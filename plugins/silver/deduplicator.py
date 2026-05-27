"""
silver/deduplicator.py
-----------------------
Responsabilidade unica: detectar vagas duplicadas publicadas em multiplas
plataformas e consolidar cada vaga real em um unico registro em silver.jobs.

Como funciona o algoritmo:
1. Busca registros de silver.raw_jobs ainda nao processados
2. Para cada registro, tenta encontrar uma vaga existente em silver.jobs
   com titulo e empresa similares (via rapidfuzz) + mesma localizacao
   + postada na mesma janela de 3 dias
3. Se encontrou match: adiciona o source_id ao registro existente
4. Se nao encontrou: cria um novo registro em silver.jobs com dedup_hash

Por que token_sort_ratio?
"Engenheiro de Dados Senior" vs "Senior Engenheiro de Dados"
-> ratio normal: baixo (ordem das palavras importa)
-> token_sort_ratio: alto (ordena as palavras antes de comparar)
Exatamente o que precisamos para titulos de vagas bagunçados.
"""
from __future__ import annotations

import hashlib
import logging
import unicodedata
from datetime import timedelta

from rapidfuzz import fuzz

from silver.db import (
    get_or_create_company,
    get_or_create_location,
    upsert_job,
    fetch_unprocessed_raw_jobs,
    get_connection,
    fetch_all_companies,
    fetch_all_locations,
)

logger = logging.getLogger(__name__)

# Limiares de similaridade — valores calibrados para minimizar
# tanto falsos positivos (unir vagas diferentes) quanto
# falsos negativos (deixar passar duplicatas reais)
TITLE_THRESHOLD   = 85  # % de similaridade minima no titulo
COMPANY_THRESHOLD = 90  # % de similaridade minima na empresa
DATE_WINDOW_DAYS  = 3   # vagas postadas com mais de 3 dias de diferenca nao sao comparadas


def _normalize_text(text: str | None) -> str:
    """
    Normaliza um texto para comparacao:
    - Remove acentos
    - Converte para minusculo
    - Remove espacos extras

    Ex: "Sênior Engenheiro de Dados" -> "senior engenheiro de dados"
    """
    if not text:
        return ""
    # Decompoe os caracteres acentuados e remove as marcas de acento
    normalized = unicodedata.normalize("NFD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_only.lower().strip()


def _build_dedup_hash(title: str, company: str, location: str, date_window: str) -> str:
    """
    Gera o SHA256 da identidade normalizada da vaga.

    Combinamos os 4 campos que juntos identificam uma vaga de forma unica.
    O SHA256 garante que a mesma combinacao sempre gera o mesmo hash de 64 chars.

    Ex: "senior engenheiro de dados|nubank|sao paulo|2026-05-18" -> "a3f8c2d1..."
    """
    identity = f"{title}|{company}|{location}|{date_window}"
    return hashlib.sha256(identity.encode()).hexdigest()


def _get_date_window(posted_at) -> str:
    """
    Agrupa datas em janelas de DATE_WINDOW_DAYS dias.
    Vagas da mesma janela sao candidatas a ser duplicatas.

    Ex (janela de 3 dias):
      2026-05-20 e 2026-05-21 -> mesma janela -> comparamos
      2026-05-20 e 2026-05-24 -> janelas diferentes -> nao comparamos
    """
    if not posted_at:
        return "unknown"
    # Divide o timestamp pelo numero de dias da janela, truncando o resultado
    # Duas datas na mesma "caixa" de 3 dias caem no mesmo bucket
    epoch = posted_at.toordinal()
    bucket = epoch // DATE_WINDOW_DAYS
    return str(bucket)


def _fetch_candidates_for_matching(conn=None) -> list[dict]:
    """
    Busca em silver.jobs vagas candidatas a ser duplicata do registro atual.
    """
    sql = """
        SELECT
            j.job_id,
            j.source_ids,
            j.dedup_hash,
            j.title,
            j.posted_at,
            c.name AS company_name,
            l.raw  AS location_raw
        FROM silver.jobs j
        LEFT JOIN silver.companies c ON j.company_id = c.id
        LEFT JOIN silver.locations l ON j.location_id = l.id
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    try:
        import psycopg2.extras
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(row) for row in cur.fetchall()]
    finally:
        if close_conn:
            conn.close()


def _find_duplicate(raw_job: dict, existing_jobs: list[dict]) -> dict | None:
    """
    Verifica se raw_job e duplicata de algum registro em existing_jobs.
    Retorna o registro existente se for duplicata, None caso contrario.

    Os 3 criterios devem ser satisfeitos simultaneamente:
    1. Titulo similar (>= TITLE_THRESHOLD)
    2. Empresa similar (>= COMPANY_THRESHOLD)
    3. Postadas na mesma janela de datas
    """
    title_norm   = _normalize_text(raw_job.get("title"))
    company_norm = _normalize_text(raw_job.get("company"))
    window       = _get_date_window(raw_job.get("posted_at"))

    for existing in existing_jobs:
        existing_window = existing.get("_window")
        if existing_window is None:
            existing_window = _get_date_window(existing.get("posted_at"))

        if existing_window != window:
            continue

        existing_title = existing.get("_title_norm")
        if existing_title is None:
            existing_title = _normalize_text(existing.get("title"))

        existing_company = existing.get("_company_norm")
        if existing_company is None:
            existing_company = _normalize_text(existing.get("company_name"))

        title_score   = fuzz.token_sort_ratio(title_norm, existing_title)
        company_score = fuzz.token_sort_ratio(company_norm, existing_company)

        if title_score >= TITLE_THRESHOLD and company_score >= COMPANY_THRESHOLD:
            logger.debug(
                "Duplicata encontrada: '%s' (%s) ~ '%s' (%s) | score titulo=%d empresa=%d",
                title_norm, company_norm, existing_title, existing_company,
                title_score, company_score,
            )
            return existing

    return None


def _mark_as_duplicate(existing_job_id: str, new_source_id: str, conn=None) -> None:
    """
    Adiciona o source_id da nova ocorrencia ao array source_ids do registro existente.
    Dessa forma mantemos a rastreabilidade: sabemos de quais plataformas cada vaga veio.
    """
    sql = """
        UPDATE silver.jobs
        SET source_ids = array_append(source_ids, %s)
        WHERE job_id = %s
          AND NOT (%s = ANY(source_ids))
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    try:
        if close_conn:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (new_source_id, existing_job_id, new_source_id))
        else:
            with conn.cursor() as cur:
                cur.execute(sql, (new_source_id, existing_job_id, new_source_id))
    finally:
        if close_conn:
            conn.close()


def infer_modalidade(title: str | None, location: str | None, description: str | None, is_remote_raw: bool) -> tuple[bool, bool]:
    """
    Infere se a vaga e remota ou hibrida com base no titulo, localizacao e descricao.
    Retorna uma tupla (is_remote, is_hybrid).
    """
    title_norm = _normalize_text(title)
    loc_norm = _normalize_text(location)
    desc_norm = _normalize_text(description)

    is_remote = bool(is_remote_raw)
    is_hybrid = False

    # 1. Palavras-chave para remoto
    remote_keywords = ["remoto", "remote", "home office", "homeoffice", "teletrabalho", "wfh", "work from home"]
    if not is_remote:
        is_remote = (
            any(kw in title_norm for kw in remote_keywords) or
            any(kw in loc_norm for kw in remote_keywords) or
            "100% remoto" in desc_norm or
            "100% remote" in desc_norm or
            "totalmente remoto" in desc_norm or
            "trabalho remoto" in desc_norm
        )

    # 2. Palavras-chave para hibrido
    # Avaliamos hibrido apenas se nao for classificado como remoto total
    is_hybrid = (
        any(kw in title_norm for kw in ["hibrido", "hibrida", "hybrid"]) or
        any(kw in loc_norm for kw in ["hibrido", "hibrida", "hybrid"]) or
        any(kw in desc_norm for kw in [
            "modelo hibrido", "trabalho hibrido", "formato hibrido", "regime hibrido", 
            "vaga hibrida", "posicao hibrida", "hybrid model", "hybrid work", 
            "hybrid format", "hybrid regime", "hybrid position", "hybrid vacancy"
        ]) or
        (
            any(w in desc_norm for w in ["hibrido", "hibrida", "hybrid"]) and
            not ("100% remoto" in desc_norm or "100% remote" in desc_norm)
        )
    )

    # Regra de exclusao mutua: se for hibrido, is_remote deve ser False
    if is_hybrid:
        is_remote = False

    return is_remote, is_hybrid


def run(**kwargs) -> dict:
    """
    Entry point chamado pela task do Airflow.
    Deduplica e registra dados de log na auditoria.
    """
    from datetime import datetime
    execution_date = kwargs.get("ds") or datetime.now().strftime("%Y-%m-%d")

    from silver.db import update_pipeline_log_dedup, update_pipeline_log_end

    raw_jobs = fetch_unprocessed_raw_jobs()
    logger.info("%d registros a processar.", len(raw_jobs))

    stats = {"new": 0, "duplicate": 0, "skipped": 0}

    shared_conn = get_connection()
    try:
        # Carregamos todos os jobs existentes uma unica vez para evitar
        # N queries ao banco — passamos a conexao compartilhada
        existing_jobs = _fetch_candidates_for_matching(shared_conn)

        # Pre-normalizamos os dados das vagas existentes para otimizar o loop de comparacao
        for job in existing_jobs:
            job["_title_norm"]   = _normalize_text(job.get("title"))
            job["_company_norm"] = _normalize_text(job.get("company_name"))
            job["_window"]       = _get_date_window(job.get("posted_at"))

        # Carrega o cache das empresas e localizacoes ja cadastradas
        companies_cache = fetch_all_companies(shared_conn)
        locations_cache = fetch_all_locations(shared_conn)

        # Usamos uma transacao unica para acelerar os inserts/updates em lote
        with shared_conn:
            for raw in raw_jobs:
                title_norm   = _normalize_text(raw.get("title"))
                company_norm = _normalize_text(raw.get("company"))
                location_raw = raw.get("location") or "desconhecido"
                window       = _get_date_window(raw.get("posted_at"))

                if not title_norm or not company_norm:
                    stats["skipped"] += 1
                    continue

                duplicate = _find_duplicate(raw, existing_jobs)

                if duplicate:
                    source_id = raw.get("source_id") or raw.get("id")
                    if source_id:
                        _mark_as_duplicate(duplicate["job_id"], str(source_id), conn=shared_conn)
                    stats["duplicate"] += 1
                else:
                    # Vaga nova: cria registro em silver.jobs
                    is_remote, is_hybrid = infer_modalidade(
                        title=raw.get("title"),
                        location=raw.get("location"),
                        description=raw.get("description"),
                        is_remote_raw=bool(raw.get("is_remote"))
                    )
                    dedup_hash  = _build_dedup_hash(title_norm, company_norm, location_raw, window)

                    # Lookup no cache em memoria
                    company_name_raw = raw.get("company") or "Desconhecida"
                    company_key = company_name_raw.lower().strip()
                    company_id = companies_cache.get(company_key)
                    if not company_id:
                        company_id = get_or_create_company(company_name_raw, conn=shared_conn)
                        companies_cache[company_key] = company_id

                    location_key = location_raw.lower().strip()
                    location_id = locations_cache.get(location_key)
                    if not location_id:
                        location_id = get_or_create_location(location_raw, is_remote, conn=shared_conn)
                        locations_cache[location_key] = location_id

                    job = {
                        "source_ids":  [str(raw.get("source_id"))] if raw.get("source_id") else [],
                        "dedup_hash":  dedup_hash,
                        "title":       raw.get("title"),
                        "company_id":  company_id,
                        "location_id": location_id,
                        "area":        None,   # sera preenchido pelo normalizer
                        "seniority":   None,
                        "skills":      [],
                        "url":         raw.get("url"),
                        "posted_at":   raw.get("posted_at"),
                        "is_remote":   is_remote,
                        "is_hybrid":   is_hybrid,
                    }

                    if upsert_job(job, conn=shared_conn):
                        stats["new"] += 1
                        # Adiciona ao cache local para que proximos registros
                        # possam ser comparados com este sem ir ao banco
                        existing_jobs.append({
                            "job_id":       None,   # nao precisamos do ID para comparacao
                            "title":        raw.get("title"),
                            "company_name": raw.get("company"),
                            "posted_at":    raw.get("posted_at"),
                            "_title_norm":  title_norm,
                            "_company_norm": company_norm,
                            "_window":      window,
                        })
                    else:
                        stats["skipped"] += 1

        # Grava na auditoria
        update_pipeline_log_dedup(execution_date, stats["new"], stats["duplicate"], conn=shared_conn)
        logger.info(
            "Deduplicacao concluida: %d novos | %d duplicatas | %d ignorados",
            stats["new"], stats["duplicate"], stats["skipped"]
        )
        return stats
    except Exception as e:
        logger.error("Erro no deduplicador: %s", str(e))
        update_pipeline_log_end(execution_date, 0, "FAILED", error_message=str(e))
        raise
    finally:
        shared_conn.close()

