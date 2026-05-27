import streamlit as st
import pandas as pd

def get_connection():
    """Retorna a conexão com o banco gerenciada pelo Streamlit."""
    return st.connection("postgresql", type="sql")

@st.cache_data(ttl=60) # Menor tempo de cache para logs operacionais (1 minuto)
def get_pipeline_status_atual():
    """Retorna o resumo da última execução registrada."""
    conn = get_connection()
    df = conn.query("""
        SELECT 
            execution_date,
            started_at,
            ended_at,
            status,
            adzuna_count,
            jooble_count,
            remoteok_count,
            gupy_count,
            raw_inserted,
            dedup_new,
            dedup_duplicates,
            classified_count,
            error_message
        FROM silver.pipeline_logs
        ORDER BY execution_date DESC
        LIMIT 1
    """)
    if df.empty:
        return None
    return df.iloc[0].to_dict()

@st.cache_data(ttl=300)
def get_pipeline_evolucao_diaria(dias=30):
    """Retorna o histórico diário de vagas por fonte para o gráfico de linha."""
    conn = get_connection()
    return conn.query("""
        SELECT 
            execution_date as data,
            adzuna_count as adzuna,
            jooble_count as jooble,
            remoteok_count as remoteok,
            gupy_count as gupy,
            raw_inserted as "Total Bruto Ingerido"
        FROM silver.pipeline_logs
        ORDER BY execution_date DESC
        LIMIT :dias
    """, params={"dias": dias})

@st.cache_data(ttl=60)
def get_pipeline_logs(dias=30, status_filter=None):
    """Histórico de logs para a tabela de auditoria."""
    conn = get_connection()
    query = """
        SELECT 
            execution_date as data,
            started_at as inicio,
            ended_at as fim,
            EXTRACT(EPOCH FROM (ended_at - started_at))::int as duracao_segundos,
            status,
            raw_inserted as bruto,
            dedup_new as novos,
            dedup_duplicates as duplicados,
            classified_count as classificados,
            error_message as erro
        FROM silver.pipeline_logs
        WHERE 1=1
    """
    params = {}
    if status_filter:
        query += " AND status = :status"
        params["status"] = status_filter
        
    query += " ORDER BY execution_date DESC LIMIT :dias"
    params["dias"] = dias
    
    return conn.query(query, params=params)

@st.cache_data(ttl=600)
def get_unmapped_skills_ranking(limit=50):
    """Ranking das palavras capitalizadas não mapeadas na silver para sugestão de novas skills."""
    conn = get_connection()
    return conn.query("""
        SELECT 
            word as skill_sugerida,
            COUNT(*) as ocorrencias,
            MAX(occurred_at)::date as vista_pela_ultima_vez
        FROM silver.unmapped_skills_logs
        GROUP BY word
        ORDER BY ocorrencias DESC
        LIMIT :limit
    """, params={"limit": limit})

@st.cache_data(ttl=600)
def get_recent_jobs_for_unmapped_skill(word):
    """Lista as vagas que continham a palavra não mapeada para auditoria semântica."""
    conn = get_connection()
    return conn.query("""
        SELECT 
            j.title,
            c.name as company,
            j.url
        FROM silver.unmapped_skills_logs u
        JOIN silver.jobs j ON u.job_id = j.job_id
        JOIN silver.companies c ON j.company_id = c.id
        WHERE u.word = :word
        LIMIT 10
    """, params={"word": word})
