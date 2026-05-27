"""
silver/db.py
------------
Responsabilidade unica: gerenciar a conexao com o PostgreSQL (Supabase) e
expor funcoes de escrita idempotentes para a Silver Layer.

"Idempotente" significa: rodar duas vezes produz o mesmo resultado que rodar uma vez.
Isso e essencial porque o Airflow pode retentar tasks automaticamente em caso de falha.
"""
from __future__ import annotations

import os
import logging
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


def get_connection():
    """
    Retorna uma conexao aberta com o Supabase (PostgreSQL).

    Lemos a URL completa de uma unica variavel de ambiente para simplificar
    a configuracao. O formato e o padrao do PostgreSQL:
      postgresql://usuario:senha@host:porta/banco
    """
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise EnvironmentError(
            "Variavel de ambiente SUPABASE_DB_URL nao encontrada. "
            "Verifique o .env e o docker-compose.yml."
        )
    return psycopg2.connect(db_url)


def upsert_raw_jobs(records: list[dict]) -> int:
    """
    Insere registros em silver.raw_jobs de forma idempotente.

    Usamos ON CONFLICT DO NOTHING no par (source, source_id):
    se a vaga ja existe para aquela fonte, simplesmente ignoramos.
    Isso garante que retries do Airflow nao criam duplicatas.

    Retorna o numero de registros efetivamente inseridos.
    """
    if not records:
        return 0

    sql = """
        INSERT INTO silver.raw_jobs
            (source, source_id, title, company, location, description,
             url, posted_at, is_remote, payload)
        VALUES
            (%(source)s, %(source_id)s, %(title)s, %(company)s, %(location)s,
             %(description)s, %(url)s, %(posted_at)s, %(is_remote)s, %(payload)s)
        ON CONFLICT (source, source_id)
        WHERE source_id IS NOT NULL
        DO NOTHING
    """

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # execute_many e otimizado para insercoes em lote
                psycopg2.extras.execute_batch(cur, sql, records, page_size=200)
                inserted = cur.rowcount
        logger.info("raw_jobs: %d registros inseridos.", inserted)
        return inserted
    finally:
        conn.close()


def fetch_all_companies(conn=None) -> dict[str, str]:
    """
    Retorna um dicionario {nome_da_empresa.lower(): id_uuid}.
    Util para cache em memoria durante cargas massivas.
    """
    sql = "SELECT id, name FROM silver.companies"
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return {row[1].lower(): str(row[0]) for row in cur.fetchall()}
    finally:
        if close_conn:
            conn.close()


def fetch_all_locations(conn=None) -> dict[str, str]:
    """
    Retorna um dicionario {raw_localizacao.lower(): id_uuid}.
    Util para cache em memoria durante cargas massivas.
    """
    sql = "SELECT id, raw FROM silver.locations"
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return {row[1].lower(): str(row[0]) for row in cur.fetchall()}
    finally:
        if close_conn:
            conn.close()


def upsert_job(job: dict, conn=None) -> bool:
    """
    Insere ou ignora uma vaga deduplicada em silver.jobs.

    O campo dedup_hash e UNIQUE — se ja existe, o ON CONFLICT ignora.
    Retorna True se inseriu, False se ja existia.
    """
    sql = """
        INSERT INTO silver.jobs
            (source_ids, dedup_hash, title, company_id, location_id,
             area, seniority, skills, url, posted_at, is_remote, is_hybrid)
        VALUES
            (%(source_ids)s, %(dedup_hash)s, %(title)s, %(company_id)s, %(location_id)s,
             %(area)s, %(seniority)s, %(skills)s, %(url)s, %(posted_at)s,
             %(is_remote)s, %(is_hybrid)s)
        ON CONFLICT (dedup_hash) DO NOTHING
    """

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    try:
        if close_conn:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(sql, job)
                    return cur.rowcount == 1
        else:
            with conn.cursor() as cur:
                cur.execute(sql, job)
                return cur.rowcount == 1
    finally:
        if close_conn:
            conn.close()


def get_or_create_company(name: str, conn=None) -> str:
    """
    Retorna o UUID da empresa pelo nome, criando o registro se nao existir.
    Padrao "get or create" — evita duplicatas na tabela de empresas.
    """
    sql_select = "SELECT id FROM silver.companies WHERE name = %s"
    sql_insert = "INSERT INTO silver.companies (name) VALUES (%s) RETURNING id"

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    try:
        if close_conn:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(sql_select, (name,))
                    row = cur.fetchone()
                    if row:
                        return str(row[0])
                    cur.execute(sql_insert, (name,))
                    return str(cur.fetchone()[0])
        else:
            with conn.cursor() as cur:
                cur.execute(sql_select, (name,))
                row = cur.fetchone()
                if row:
                    return str(row[0])
                cur.execute(sql_insert, (name,))
                return str(cur.fetchone()[0])
    finally:
        if close_conn:
            conn.close()


def get_or_create_location(raw: str, is_remote: bool = False, conn=None) -> str:
    """
    Retorna o UUID da localizacao pelo texto bruto, criando se nao existir.
    A normalizacao de cidade/estado fica para a Fase 4 (Gold layer com dbt).
    """
    sql_select = "SELECT id FROM silver.locations WHERE raw = %s"
    sql_insert = "INSERT INTO silver.locations (raw, is_remote) VALUES (%s, %s) RETURNING id"

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    try:
        if close_conn:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(sql_select, (raw,))
                    row = cur.fetchone()
                    if row:
                        return str(row[0])
                    cur.execute(sql_insert, (raw, is_remote))
                    return str(cur.fetchone()[0])
        else:
            with conn.cursor() as cur:
                cur.execute(sql_select, (raw,))
                row = cur.fetchone()
                if row:
                    return str(row[0])
                cur.execute(sql_insert, (raw, is_remote))
                return str(cur.fetchone()[0])
    finally:
        if close_conn:
            conn.close()


def fetch_unprocessed_raw_jobs(limit: int = 5000) -> list[dict]:
    """
    Busca registros de silver.raw_jobs que ainda nao foram processados
    pelo deduplicador (ou seja, que nao existem em silver.jobs via source_id).

    Retorna uma lista de dicts prontos para o deduplicador consumir.
    """
    sql = """
        SELECT
            r.id,
            r.source,
            r.source_id,
            r.title,
            r.company,
            r.location,
            r.description,
            r.url,
            r.posted_at,
            r.is_remote
        FROM silver.raw_jobs r
        WHERE NOT EXISTS (
            SELECT 1 FROM silver.jobs j
            WHERE r.source_id = ANY(j.source_ids)
        )
        ORDER BY r.ingested_at DESC
        LIMIT %s
    """

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (limit,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def fetch_jobs_without_classification(limit: int = 5000) -> list[dict]:
    """
    Busca vagas em silver.jobs onde area e NULL (ainda nao normalizadas).
    O normalizer processara apenas esses registros — evita reprocessamento.
    A descricao e buscada na raw_jobs associada.
    """
    sql = """
        SELECT 
            j.job_id, 
            j.title, 
            (SELECT description FROM silver.raw_jobs r WHERE r.source_id = j.source_ids[1] LIMIT 1) as description
        FROM silver.jobs j
        WHERE j.area IS NULL
        LIMIT %s
    """

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (limit,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def update_job_classification(job_id: str, area: str, seniority: str, skills: list[str], conn=None) -> None:
    """
    Atualiza area, senioridade e skills de uma vaga especifica em silver.jobs.
    Chamado pelo normalizer apos a classificacao.
    """
    sql = """
        UPDATE silver.jobs
        SET area = %s, seniority = %s, skills = %s
        WHERE job_id = %s
    """

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    try:
        if close_conn:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (area, seniority, skills, job_id))
        else:
            with conn.cursor() as cur:
                cur.execute(sql, (area, seniority, skills, job_id))
    finally:
        if close_conn:
            conn.close()


def upsert_pipeline_log_start(execution_date: str, conn=None) -> None:
    """Insere ou reseta o registro de auditoria do dia atual."""
    sql = """
        INSERT INTO silver.pipeline_logs (execution_date, started_at, status, error_message)
        VALUES (%s, NOW(), 'RUNNING', NULL)
        ON CONFLICT (execution_date) DO UPDATE
        SET started_at = NOW(), status = 'RUNNING', error_message = NULL, ended_at = NULL
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (execution_date,))
        if close_conn:
            conn.commit()
    finally:
        if close_conn:
            conn.close()


def update_pipeline_log_extract(execution_date: str, adzuna: int, jooble: int, remoteok: int, gupy: int, raw_inserted: int, conn=None) -> None:
    """Atualiza contadores de ingestao bruta."""
    sql = """
        UPDATE silver.pipeline_logs
        SET adzuna_count = %s, jooble_count = %s, remoteok_count = %s, gupy_count = %s, raw_inserted = %s
        WHERE execution_date = %s
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (adzuna, jooble, remoteok, gupy, raw_inserted, execution_date))
        if close_conn:
            conn.commit()
    finally:
        if close_conn:
            conn.close()


def update_pipeline_log_dedup(execution_date: str, dedup_new: int, dedup_duplicates: int, conn=None) -> None:
    """Atualiza contadores do processo de deduplicacao."""
    sql = """
        UPDATE silver.pipeline_logs
        SET dedup_new = %s, dedup_duplicates = %s
        WHERE execution_date = %s
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (dedup_new, dedup_duplicates, execution_date))
        if close_conn:
            conn.commit()
    finally:
        if close_conn:
            conn.close()


def update_pipeline_log_end(execution_date: str, classified_count: int, status: str, error_message: str = None, conn=None) -> None:
    """Finaliza o log definindo o termino da pipeline."""
    sql = """
        UPDATE silver.pipeline_logs
        SET ended_at = NOW(), status = %s, classified_count = %s, error_message = %s
        WHERE execution_date = %s
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (status, classified_count, error_message, execution_date))
        if close_conn:
            conn.commit()
    finally:
        if close_conn:
            conn.close()


def insert_unmapped_skills_batch(records: list[dict], conn=None) -> None:
    """Insere em lote termos identificados que nao constam no dicionario de skills."""
    if not records:
        return
    sql = """
        INSERT INTO silver.unmapped_skills_logs (job_id, word)
        VALUES (%(job_id)s, %(word)s)
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True
    try:
        import psycopg2.extras
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, records, page_size=500)
        if close_conn:
            conn.commit()
    finally:
        if close_conn:
            conn.close()

