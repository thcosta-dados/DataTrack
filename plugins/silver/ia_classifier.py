import os
import json
import logging
import google.generativeai as genai
from silver.db import get_connection, update_job_classification

logger = logging.getLogger(__name__)

# Categorias válidas permitidas para evitar classificações inválidas da IA
VALID_AREAS = {'data_engineering', 'data_science', 'data_analytics', 'ml_mlops', 'bi', 'unknown'}
VALID_SENIORITIES = {'estagio', 'junior', 'pleno', 'senior', 'lead', 'unknown'}

def fetch_unknown_active_jobs(conn) -> list[dict]:
    """Busca vagas recentes e ativas que ainda estão sem classificação, buscando a descrição da raw_jobs."""
    sql = """
        SELECT 
            j.job_id, 
            j.title, 
            j.skills,
            (
                SELECT r.description 
                FROM silver.raw_jobs r 
                WHERE r.source_id = j.source_ids[1] 
                LIMIT 1
            ) as description
        FROM silver.jobs j
        WHERE j.is_active = true
          AND j.posted_at >= CURRENT_DATE - 14
          AND j.classification_source = 'unknown'
          AND (j.area = 'unknown' OR j.seniority = 'unknown')
        ORDER BY j.posted_at DESC
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        colnames = [desc[0] for desc in cur.description]
        return [dict(zip(colnames, row)) for row in cur.fetchall()]

def classify_description_with_gemini(model, title: str, description: str) -> dict | None:
    """Usa a API do Gemini para ler a JD e inferir área e senioridade em JSON."""
    prompt = f"""
Você é um especialista em Engenharia de Dados e Recrutamento Técnico (Tech Recruiter).
Analise o título e a descrição (Job Description) da vaga abaixo para classificar a área de dados e o nível de senioridade de forma precisa.

Título da vaga: {title}
Descrição da vaga: {description}

Instruções de Classificação:
1. Escolha a "area" da vaga entre as opções:
   - 'data_engineering' (se for Engenharia de Dados, Pipelines, ETL, Spark, Airflow, dbt, Cloud Data Solutions)
   - 'data_science' (se for Ciência de Dados, Modelos Estatísticos, ML, Deep Learning, P&D)
   - 'data_analytics' (se for Análise de Dados, Product Analytics, Analytics Engineering, BI avançado)
   - 'ml_mlops' (se for Machine Learning Engineer, MLOps, Deploy de Modelos, ML Platform)
   - 'bi' (se for Business Intelligence puro, dashboards Power BI/Tableau, relatórios comerciais)
   - 'unknown' (se não for possível determinar)

2. Escolha a "seniority" (senioridade) da vaga entre as opções:
   - 'estagio' (estágio, intern, trainee)
   - 'junior' (júnior, jr, 1-2 anos de experiência)
   - 'pleno' (pleno, pl, mid-level, 3-4 anos de experiência)
   - 'senior' (sênior, sr, especialista, 5+ anos de experiência)
   - 'lead' (lead, líder técnico, coordenador, gerente, staff, principal)
   - 'unknown' (se não houver nenhuma pista na descrição)

Para determinar a senioridade, leia atentamente a descrição (JD). Muitas vezes o título não diz a senioridade, mas a descrição pede "experiência sólida de 5 anos", "liderança de projetos" (Sênior/Lead) ou "estudantes universitários", "primeira oportunidade" (Estágio/Júnior).

Retorne a resposta estritamente no seguinte formato JSON:
{{
  "area": "area_escolhida",
  "seniority": "seniority_escolhida"
}}
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text.strip())
        
        # Garante que a IA retornou chaves válidas
        area = data.get("area")
        seniority = data.get("seniority")
        
        if area not in VALID_AREAS:
            area = "unknown"
        if seniority not in VALID_SENIORITIES:
            seniority = "unknown"
            
        return {"area": area, "seniority": seniority}
    except Exception as e:
        err_msg = str(e).lower()
        logger.warning("Falha ao classificar com Gemini: %s", str(e))
        if "429" in err_msg or "quota" in err_msg:
            return "RATE_LIMIT"
        return None

def run(**kwargs) -> dict:
    """Entrypoint chamado pela tarefa do Airflow."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("Variável GEMINI_API_KEY não configurada. A classificação por IA foi pulada.")
        return {"processed": 0, "status": "skipped"}
        
    # Inicializa API do Gemini
    genai.configure(api_key=api_key)
    # gemini-2.5-flash é excelente, rápido e gratuito na cota
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    conn = get_connection()
    try:
        jobs = fetch_unknown_active_jobs(conn)
        logger.info("Encontradas %d vagas unknown para classificar via IA.", len(jobs))
        
        stats = {"processed": 0, "success": 0, "failed": 0}
        if not jobs:
            return stats
            
        with conn:
            for i, job in enumerate(jobs):
                # Adiciona sleep de 12 segundos antes de cada chamada (exceto na primeira)
                # para respeitar o limite gratuito de 5 RPM (60s / 5 = 12s)
                if i > 0:
                    import time
                    time.sleep(12)

                job_id = str(job["job_id"])
                title = job.get("title", "")
                description = job.get("description", "")
                
                result = classify_description_with_gemini(model, title, description)
                
                if result == "RATE_LIMIT":
                    logger.warning("Limite de quota da API atingido. Interrompendo graciosamente a execução para reprocessamento diário futuro.")
                    break
                    
                stats["processed"] += 1
                
                if result and isinstance(result, dict) and (result["area"] != "unknown" or result["seniority"] != "unknown"):
                    # Salva classificação enriquecida marcando classification_source = 'ia'
                    # Mantém as skills originais já extraídas sintaticamente
                    cur_skills = job.get("skills", [])
                    
                    update_job_classification(
                        job_id=job_id,
                        area=result["area"],
                        seniority=result["seniority"],
                        skills=cur_skills, # Mantém as skills do banco
                        classification_source="ia",
                        conn=conn
                    )
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
                    
        logger.info("Processamento de IA concluído: %d tentadas | %d refinadas | %d falhas/sem pista", 
                    stats["processed"], stats["success"], stats["failed"])
        return stats
        
    except Exception as e:
        logger.error("Erro no processamento da IA: %s", str(e))
        raise
    finally:
        conn.close()
