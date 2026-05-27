"""
silver/loader.py
----------------
Responsabilidade unica: ler os JSON brutos da Bronze Layer (MinIO) e
inserir os registros normalizados em silver.raw_jobs no Supabase.

Cada fonte tem uma estrutura JSON diferente. O FIELD_MAPS faz o mapeamento
de campos especificos de cada fonte para o schema comum da Silver.

Por que nao transformamos mais aqui?
Porque o loader e a "boca de entrada" da Silver — ele deve apenas
trazer os dados pro banco de forma estruturada. A logica de negocio
(dedup, area, senioridade) fica em modulos separados e testados.
"""
from __future__ import annotations

import os
import json
import logging
from datetime import datetime, date

import boto3
from botocore.exceptions import ClientError

from silver.db import upsert_raw_jobs

logger = logging.getLogger(__name__)

# Configuracoes do MinIO (equivalente local do S3)
MINIO_ENDPOINT   = "http://minio:9000"
BRONZE_BUCKET    = "datatrack-bronze"

# Mapeamento de campos: cada chave e uma fonte, e o valor e um dict
# que traduz os campos originais para o schema comum.
# Campos aninhados usam "." como separador (ex: "company.display_name")
FIELD_MAPS = {
    "adzuna": {
        "source_id":   "id",
        "title":       "title",
        "company":     "company.display_name",
        "location":    "location.display_name",
        "description": "description",
        "url":         "redirect_url",
        "posted_at":   "created",
        "is_remote":   None,   # Adzuna nao tem campo direto de remoto
    },
    "jooble": {
        "source_id":   "id",
        "title":       "title",
        "company":     "company",
        "location":    "location",
        "description": "snippet",
        "url":         "link",
        "posted_at":   "updated",
        "is_remote":   None,
    },
    "remoteok": {
        "source_id":   "id",
        "title":       "position",
        "company":     "company",
        "location":    "location",
        "description": "description",
        "url":         "url",
        "posted_at":   "date",
        "is_remote":   True,   # RemoteOK e 100% remoto por definicao
    },
    "gupy": {
        "source_id":   "source_id",
        "title":       "title",
        "company":     "company",
        "location":    "location",
        "description": "raw_text",
        "url":         "url",
        "posted_at":   "posted_at",
        "is_remote":   "is_remote",
    },
}


def _get_minio_client():
    """Instancia o cliente boto3 apontando para o MinIO local."""
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=os.getenv("MINIO_ROOT_USER", "admin"),
        aws_secret_access_key=os.getenv("MINIO_ROOT_PASSWORD", "adminpassword"),
        region_name="us-east-1",
    )


def _read_bronze_file(source: str, execution_date: str) -> list:
    """
    Le o arquivo JSON da Bronze Layer para a fonte e data especificadas.
    Retorna a lista de vagas brutas, ou lista vazia se o arquivo nao existir.
    """
    s3 = _get_minio_client()
    file_key = f"{source}/{execution_date}/raw_jobs.json"

    try:
        response = s3.get_object(Bucket=BRONZE_BUCKET, Key=file_key)
        content = json.loads(response["Body"].read())
        jobs = content.get("results", [])
        logger.info("[%s] %d vagas brutas lidas de %s", source, len(jobs), file_key)
        return jobs
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            logger.warning("[%s] Arquivo nao encontrado: %s", source, file_key)
            return []
        raise


def _get_nested(obj: dict, path: str):
    """
    Acessa campos aninhados usando "." como separador.
    Ex: _get_nested(job, "company.display_name") -> job["company"]["display_name"]
    Retorna None se qualquer nivel nao existir.
    """
    keys = path.split(".")
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _normalize_date(raw_date) -> date | None:
    """
    Tenta parsear a data de varios formatos que as fontes usam.
    Retorna um objeto date() ou None se nao conseguir parsear.
    """
    if not raw_date:
        return None

    # Timestamp Unix (RemoteOK usa isso)
    if isinstance(raw_date, (int, float)):
        return datetime.fromtimestamp(raw_date).date()

    if isinstance(raw_date, str):
        # Fatiamos os primeiros 19 caracteres para obter o datetime sem timezone
        clean_date = raw_date[:19]
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(clean_date, fmt).date()
            except ValueError:
                continue

    return None


def _normalize_is_remote(value, source: str) -> bool:
    """
    Normaliza o campo is_remote para boolean.
    O RemoteOK e sempre True. O Gupy usa string 'remote'/'hybrid'/'on-site'.
    """
    if value is True:
        return True
    if isinstance(value, str):
        return value.lower() in ("remote", "remoto", "home office")
    return False


def _map_job(raw_job: dict, source: str) -> dict:
    """
    Transforma um registro bruto da fonte em um dict compativel com silver.raw_jobs.
    Usa o FIELD_MAPS para saber quais campos pegar e de onde.
    """
    field_map = FIELD_MAPS[source]
    normalized = {"source": source, "payload": json.dumps(raw_job, ensure_ascii=False)}

    for target_field, source_path in field_map.items():
        if target_field == "is_remote":
            raw_val = True if source_path is True else _get_nested(raw_job, source_path) if source_path else None
            normalized["is_remote"] = _normalize_is_remote(raw_val, source)
        elif target_field == "posted_at":
            normalized["posted_at"] = _normalize_date(_get_nested(raw_job, source_path))
        else:
            normalized[target_field] = _get_nested(raw_job, source_path) if source_path else None

    # Garante que source_id nunca seja None (usar str do campo ou None)
    sid = normalized.get("source_id")
    normalized["source_id"] = str(sid) if sid else None

    # Inferencia de trabalho remoto baseada em palavras-chave no titulo, localizacao ou descricao
    if not normalized.get("is_remote"):
        title_lower = (normalized.get("title") or "").lower()
        loc_lower = (normalized.get("location") or "").lower()
        desc_lower = (normalized.get("description") or "").lower()
        
        remote_keywords = ["remoto", "remote", "home office", "homeoffice", "teletrabalho", "wfh", "work from home"]
        is_inferred_remote = (
            any(kw in title_lower for kw in remote_keywords) or
            any(kw in loc_lower for kw in remote_keywords) or
            "100% remoto" in desc_lower or
            "100% remote" in desc_lower or
            "totalmente remoto" in desc_lower or
            "trabalho remoto" in desc_lower
        )
        if is_inferred_remote:
            normalized["is_remote"] = True

    return normalized


def load_source(source: str, execution_date: str) -> int:
    """
    Carrega todas as vagas de uma fonte especifica para silver.raw_jobs.
    Retorna o numero de registros inseridos.
    """
    raw_jobs = _read_bronze_file(source, execution_date)
    if not raw_jobs:
        return 0

    records = [_map_job(job, source) for job in raw_jobs]
    inserted = upsert_raw_jobs(records)
    logger.info("[%s] %d/%d registros inseridos na Silver.", source, inserted, len(records))
    return inserted


def load_all_sources(**kwargs) -> dict:
    """
    Entry point chamado pela task do Airflow.
    Carrega todas as 4 fontes para a data de execucao da DAG, auditando no pipeline_logs.
    """
    execution_date = kwargs.get("ds") or datetime.now().strftime("%Y-%m-%d")
    sources = ["adzuna", "jooble", "remoteok", "gupy"]
    results = {}

    from silver.db import upsert_pipeline_log_start, update_pipeline_log_extract, update_pipeline_log_end

    try:
        # 1. Inicia auditoria
        upsert_pipeline_log_start(execution_date)

        # 2. Carrega cada fonte
        for source in sources:
            results[source] = load_source(source, execution_date)

        total = sum(results.values())
        logger.info("Silver load concluido: %d registros no total. Detalhes: %s", total, results)

        # 3. Salva contadores parciais na auditoria
        update_pipeline_log_extract(
            execution_date=execution_date,
            adzuna=results.get("adzuna", 0),
            jooble=results.get("jooble", 0),
            remoteok=results.get("remoteok", 0),
            gupy=results.get("gupy", 0),
            raw_inserted=total
        )
        return results
    except Exception as e:
        logger.error("Erro no loader: %s", str(e))
        update_pipeline_log_end(execution_date, 0, "FAILED", error_message=str(e))
        raise

