from __future__ import annotations
import asyncio
import logging
import unicodedata
import httpx
from silver.db import get_connection

logger = logging.getLogger(__name__)

# Padrões de URLs conhecidos que agregadores usam para redirecionar vagas expiradas
EXPIRED_URL_PATTERNS = [
    "details/expired",
    "vaga-nao-disponivel",
    "expired",
    "invalid-job",
    "vaga-inativa",
    "vaga-finalizada"
]

def fetch_active_recent_jobs(conn) -> list[dict]:
    """Busca todas as vagas que constam como ativas nos últimos 14 dias."""
    sql = """
        SELECT job_id, url 
        FROM silver.jobs 
        WHERE is_active = true 
          AND posted_at >= CURRENT_DATE - 14
        ORDER BY posted_at DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        colnames = [desc[0] for desc in cur.description]
        return [dict(zip(colnames, row)) for row in cur.fetchall()]

def inactivate_expired_jobs_by_age(conn) -> int:
    """Inativa automaticamente vagas publicadas há mais de 14 dias."""
    sql = """
        UPDATE silver.jobs 
        SET is_active = false 
        WHERE is_active = true 
          AND posted_at < CURRENT_DATE - 14
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.rowcount

def inactivate_jobs_batch(conn, job_ids: list[str]) -> int:
    """Marca uma lista de IDs de vagas como inativas no banco."""
    if not job_ids:
        return 0
    sql = """
        UPDATE silver.jobs 
        SET is_active = false 
        WHERE job_id = ANY(%s::uuid[])
    """
    with conn.cursor() as cur:
        cur.execute(sql, (job_ids,))
        return cur.rowcount

async def check_single_url(client: httpx.AsyncClient, semaphore: asyncio.Semaphore, job_id: str, url: str) -> tuple[str, bool]:
    """Testa uma URL com requisição GET assíncrona, tratando timeouts e redirecionamentos."""
    async with semaphore:
        try:
            # Agregadores costumam redirecionar, então follow_redirects=True é mandatório
            # Usamos GET para poder inspecionar o corpo da resposta se necessário
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            response = await client.get(url, headers=headers, timeout=3.5, follow_redirects=True)
            
            # Status 404 ou 410 indica indisponibilidade definitiva
            if response.status_code in (404, 410):
                return job_id, False
                
            # Verifica se redirecionou para alguma URL de erro padrão de vaga encerrada
            final_url_str = str(response.url).lower()
            if any(pat in final_url_str for pat in EXPIRED_URL_PATTERNS):
                return job_id, False
                
            # Se for sucesso (200), podemos fazer uma verificação textual rápida no HTML
            # contra expressões típicas de expiração para evitar falsos positivos
            if response.status_code == 200:
                html_lower = response.text.lower()
                text_indicators = [
                    "vaga nao esta mais disponivel",
                    "vaga nao disponivel",
                    "vaga expirada",
                    "vaga encerrada",
                    "finalizada",
                    "vaga inativa",
                    "infelizmente essa vaga nao"
                ]
                # Remove acentos do HTML para comparação limpa
                normalized = unicodedata.normalize("NFD", html_lower).encode("ascii", "ignore").decode("ascii")
                if any(ind in normalized for ind in text_indicators):
                    return job_id, False
            
            return job_id, True
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 410):
                return job_id, False
            return job_id, True
        except (httpx.RequestError, asyncio.TimeoutError):
            # Erros de rede genéricos ou timeouts não devem inativar a vaga no primeiro erro
            return job_id, True

async def check_all_urls(jobs: list[dict]) -> list[str]:
    """Orquestra a verificação concorrente de todas as URLs ativas."""
    # Limita concorrência para 10 conexões simultâneas para evitar rate limits
    semaphore = asyncio.Semaphore(10)
    inactive_ids = []
    
    # verify=False desabilita validacao TLS intencionalmente:
    # estamos apenas checando se a URL responde, nao transferindo dados sensiveis.
    # Muitos sites de vagas usam certificados auto-assinados ou CDNs com certs intermediarios.
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=20)
    async with httpx.AsyncClient(limits=limits, verify=False) as client:
        tasks = []
        for job in jobs:
            job_id = str(job["job_id"])
            url = job.get("url")
            if url:
                tasks.append(check_single_url(client, semaphore, job_id, url))
                
        # Roda concorrentemente e aguarda todos finalizarem
        results = await asyncio.gather(*tasks)
        
        # Filtra os IDs das vagas que retornaram inativas (False)
        for job_id, is_active in results:
            if not is_active:
                inactive_ids.append(job_id)
                
    return inactive_ids

def run(**kwargs) -> dict:
    """Entrypoint chamado pela tarefa do Airflow."""
    conn = get_connection()
    try:
        # 1. Desativa por idade vagas com mais de 14 dias
        expired_by_age = inactivate_expired_jobs_by_age(conn)
        logger.info("Inativadas %d vagas antigas (>14 dias) por recência.", expired_by_age)
        
        # 2. Busca vagas recentes (<= 14 dias) ainda ativas para verificação HTTP
        active_jobs = fetch_active_recent_jobs(conn)
        logger.info("Testando links de %d vagas ativas recentes.", len(active_jobs))
        
        stats = {
            "expired_by_age": expired_by_age,
            "tested": len(active_jobs),
            "expired_by_link": 0
        }
        
        if not active_jobs:
            return stats
            
        # Executa loop de evento assíncrono para os testes HTTP
        inactive_ids = asyncio.run(check_all_urls(active_jobs))
        
        # 3. Atualiza o status de inativas no banco em lote
        if inactive_ids:
            expired_by_link = inactivate_jobs_batch(conn, inactive_ids)
            stats["expired_by_link"] = expired_by_link
            logger.info("Marcadas %d vagas como inativas devido a links expirados/quebrados.", expired_by_link)
            
        logger.info("Higienização concluída: %d inativadas por idade | %d testadas | %d inativadas por link",
                    stats["expired_by_age"], stats["tested"], stats["expired_by_link"])
        return stats
        
    except Exception as e:
        logger.error("Erro na verificação de links: %s", str(e))
        raise
    finally:
        conn.close()
