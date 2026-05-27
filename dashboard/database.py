import streamlit as st
import pandas as pd

def get_connection():
    """Retorna a conexão com o banco gerenciada pelo Streamlit."""
    return st.connection("postgresql", type="sql")

@st.cache_data(ttl=3600)
def get_filter_options():
    """Busca as opções disponíveis para os filtros do sidebar dinamicamente."""
    conn = get_connection()
    
    # Busca áreas
    areas = conn.query("SELECT area_code, area_label FROM gold.dim_area ORDER BY area_label")
    
    # Busca senioridades
    seniorities = conn.query("SELECT seniority_code, order_rank FROM gold.dim_seniority ORDER BY order_rank")
    
    # Busca localizações distintas (cidades/estados)
    locations = conn.query("""
        SELECT DISTINCT l.location_name 
        FROM gold.dim_location l
        JOIN gold.fact_job_posting f ON f.location_id = l.location_id
        WHERE l.location_name IS NOT NULL AND l.location_name != 'desconhecido'
        ORDER BY l.location_name
    """)
    
    # Busca todas as skills distintas catalogadas
    skills = conn.query("SELECT DISTINCT skill_name FROM gold.dim_skill ORDER BY skill_name")
    
    return {
        "areas": areas.to_dict(orient="records"),
        "seniorities": seniorities.to_dict(orient="records"),
        "locations": locations["location_name"].tolist(),
        "skills": skills["skill_name"].tolist()
    }

@st.cache_data(ttl=3600)
def get_vagas_filtradas(areas=None, seniorities=None, locations=None, selected_modalities=None, selected_skills=None, dias=None, search_term=""):
    """
    Busca vagas com filtros avançados aplicados dinamicamente.
    Retorna as skills de cada vaga desaninhadas no formato amigável.
    """
    conn = get_connection()
    
    query = """
        SELECT 
            f.job_id,
            f.job_title as title,
            c.company_name as company,
            l.location_name as location,
            a.area_label as area,
            s_dim.order_rank as seniority_rank,
            -- Resolve o nome amigável da senioridade
            CASE 
                WHEN f.seniority_code = 'estagio' THEN 'Estágio'
                WHEN f.seniority_code = 'junior' THEN 'Júnior'
                WHEN f.seniority_code = 'pleno' THEN 'Pleno'
                WHEN f.seniority_code = 'senior' THEN 'Sênior'
                WHEN f.seniority_code = 'especialista' THEN 'Especialista'
                WHEN f.seniority_code = 'lead' THEN 'Lead'
                ELSE 'Não Informado'
            END as seniority,
            -- Busca array de skills da silver
            s_db.skills as skills,
            f.job_url as url,
            f.posted_date as posted_at,
            f.is_remote,
            f.is_hybrid
        FROM gold.fact_job_posting f
        JOIN gold.dim_company c ON f.company_id = c.company_id
        JOIN gold.dim_location l ON f.location_id = l.location_id
        JOIN gold.dim_area a ON f.area_code = a.area_code
        JOIN gold.dim_seniority s_dim ON f.seniority_code = s_dim.seniority_code
        LEFT JOIN silver.jobs s_db ON f.job_id = s_db.job_id
        WHERE 1=1
    """
    
    params = {}
    
    if areas:
        query += " AND f.area_code = ANY(:areas)"
        params["areas"] = list(areas)
        
    if seniorities:
        query += " AND f.seniority_code = ANY(:seniorities)"
        params["seniorities"] = list(seniorities)
        
    if locations:
        query += " AND l.location_name = ANY(:locations)"
        params["locations"] = list(locations)
        
    if selected_modalities:
        modal_conds = []
        if "🌐 Remoto" in selected_modalities:
            modal_conds.append("f.is_remote = true")
        if "🏢 Híbrido" in selected_modalities:
            modal_conds.append("f.is_hybrid = true")
        if "🏢 Presencial" in selected_modalities:
            modal_conds.append("(f.is_remote = false AND f.is_hybrid = false)")
        if modal_conds:
            query += f" AND ({' OR '.join(modal_conds)})"
        
    if dias:
        query += " AND f.posted_date >= CURRENT_DATE - CAST(:dias AS INT) * INTERVAL '1 day'"
        params["dias"] = dias
        
    if search_term:
        query += " AND (LOWER(f.job_title) LIKE :search OR LOWER(c.company_name) LIKE :search)"
        params["search"] = f"%{search_term.lower()}%"
        
    # Filtro de skills (todas as selecionadas devem estar presentes na vaga)
    if selected_skills:
        query += " AND s_db.skills @> :selected_skills"
        params["selected_skills"] = selected_skills # Lista/array python mapeia pro postgres array
        
    query += " ORDER BY f.posted_date DESC, f.job_id LIMIT 201"
    
    return conn.query(query, params=params)

@st.cache_data(ttl=3600)
def get_kpis_mercado():
    """Metricas gerais do painel de visão geral."""
    conn = get_connection()
    
    total_vagas = conn.query("SELECT COUNT(*) as total FROM gold.fact_job_posting")
    
    remoto_percent = conn.query("""
        SELECT 
            ROUND((COUNT(CASE WHEN is_remote = true THEN 1 END) * 100.0) / COUNT(*), 1) as percent
        FROM gold.fact_job_posting
    """)
    
    hibrido_percent = conn.query("""
        SELECT 
            ROUND((COUNT(CASE WHEN is_hybrid = true THEN 1 END) * 100.0) / COUNT(*), 1) as percent
        FROM gold.fact_job_posting
    """)
    
    vagas_hoje = conn.query("""
        SELECT COUNT(*) as total 
        FROM gold.fact_job_posting 
        WHERE posted_date >= CURRENT_DATE - INTERVAL '1 day'
    """)
    
    return {
        "total_vagas": int(total_vagas["total"].iloc[0]),
        "remoto_percent": float(remoto_percent["percent"].iloc[0]) if not remoto_percent["percent"].isna().iloc[0] else 0.0,
        "hibrido_percent": float(hibrido_percent["percent"].iloc[0]) if not hibrido_percent["percent"].isna().iloc[0] else 0.0,
        "vagas_hoje": int(vagas_hoje["total"].iloc[0])
    }

@st.cache_data(ttl=3600)
def get_distribuicao_area():
    """Retorna contagem de vagas por área legível."""
    conn = get_connection()
    return conn.query("""
        SELECT a.area_label as area, COUNT(f.job_id) as vagas
        FROM gold.fact_job_posting f
        JOIN gold.dim_area a ON f.area_code = a.area_code
        GROUP BY a.area_label
        ORDER BY vagas DESC
    """)

@st.cache_data(ttl=3600)
def get_distribuicao_senioridade():
    """Retorna contagem de vagas por senioridade formatada."""
    conn = get_connection()
    return conn.query("""
        SELECT 
            CASE 
                WHEN f.seniority_code = 'estagio' THEN 'Estágio'
                WHEN f.seniority_code = 'junior' THEN 'Júnior'
                WHEN f.seniority_code = 'pleno' THEN 'Pleno'
                WHEN f.seniority_code = 'senior' THEN 'Sênior'
                WHEN f.seniority_code = 'especialista' THEN 'Especialista'
                WHEN f.seniority_code = 'lead' THEN 'Lead'
                ELSE 'Não Informado'
            END as senioridade,
            s.order_rank,
            COUNT(f.job_id) as vagas
        FROM gold.fact_job_posting f
        JOIN gold.dim_seniority s ON f.seniority_code = s.seniority_code
        GROUP BY f.seniority_code, s.order_rank
        ORDER BY s.order_rank
    """)

@st.cache_data(ttl=3600)
def get_modalidade_por_area():
    """Proporção de vagas remotas, híbridas e presenciais por área."""
    conn = get_connection()
    return conn.query("""
        SELECT 
            a.area_label as area,
            COUNT(CASE WHEN f.is_remote = true THEN 1 END) as remoto,
            COUNT(CASE WHEN f.is_hybrid = true THEN 1 END) as hybrido,
            COUNT(CASE WHEN f.is_remote = false AND f.is_hybrid = false THEN 1 END) as presencial
        FROM gold.fact_job_posting f
        JOIN gold.dim_area a ON f.area_code = a.area_code
        GROUP BY a.area_label
    """)

@st.cache_data(ttl=3600)
def get_top_skills(area_code=None, limit=15):
    """Retorna as skills mais frequentes do mercado."""
    conn = get_connection()
    query = """
        SELECT skill, SUM(job_count) as frequencia
        FROM gold.agg_skills_frequency
        WHERE 1=1
    """
    params = {}
    if area_code:
        query += " AND job_area = :area"
        params["area"] = area_code
        
    query += " GROUP BY skill ORDER BY frequencia DESC LIMIT :limit"
    params["limit"] = limit
    
    return conn.query(query, params=params)

@st.cache_data(ttl=3600)
def get_skills_heatmap_data():
    """Frequência cruzada de Top Skills vs Áreas para gráfico de Heatmap."""
    conn = get_connection()
    
    # 1. Busca as top 10 skills do mercado geral primeiro
    top_skills_df = conn.query("""
        SELECT skill, SUM(job_count) as total
        FROM gold.agg_skills_frequency
        GROUP BY skill
        ORDER BY total DESC
        LIMIT 10
    """)
    top_skills = top_skills_df["skill"].tolist()
    
    if not top_skills:
        return pd.DataFrame()
        
    # 2. Busca a contagem para essas top skills cruzadas com cada área
    return conn.query("""
        SELECT 
            skill,
            a.area_label as area,
            SUM(job_count) as frequencia
        FROM gold.agg_skills_frequency s
        JOIN gold.dim_area a ON s.job_area = a.area_code
        WHERE skill = ANY(:top_skills)
        GROUP BY skill, a.area_label
    """, params={"top_skills": list(top_skills)})

