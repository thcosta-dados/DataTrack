"""
silver/normalizer.py
---------------------
Responsabilidade unica: classificar cada vaga em silver.jobs com:
  - area:      qual sub-area de dados (data_engineering, data_science, etc.)
  - seniority: nivel de senioridade (estagio, junior, pleno, senior, lead)
  - skills:    lista de competencias tecnicas extraidas da descricao

Como funciona:
  Para area e senioridade: comparamos palavras-chave contra o titulo da vaga.
  O titulo e mais preciso que a descricao para isso — a descricao costuma
  mencionar habilidades de areas diferentes sem que a vaga seja daquela area.

  Para skills: varremos a descricao com regex case-insensitive contra um
  dicionario por area. Usamos a descricao aqui porque skills aparecem
  especificamente listadas (ex: "Conhecimento em Python, SQL e Airflow").
"""
from __future__ import annotations

import re
import logging
import unicodedata

from silver.db import (
    fetch_jobs_without_classification,
    update_job_classification,
    get_connection,
)

logger = logging.getLogger(__name__)

# Palavras capitalizadas comuns a serem ignoradas na busca de novas skills (stop words)
EXCLUDE_WORDS = {
    "A", "O", "De", "Para", "Com", "Em", "Um", "Uma", "Os", "As", "Se", "Por", "Como", 
    "Ao", "Aos", "Dos", "Das", "Nas", "Nos", "Pelo", "Pela", "Sobre", "Entre", "Através", 
    "Durante", "Requisitos", "Desejável", "Diferencial", "Perfil", "Você", "Será", 
    "Atividades", "Responsabilidades", "Experiência", "Conhecimento", "Trabalhar", 
    "Equipe", "Empresa", "Projetos", "Tecnologia", "Área", "Vagas", "Vaga", "Dados", 
    "Informação", "Sistemas", "Desenvolvimento", "Engenharia", "Ciência", "Análise", 
    "Mercado", "Negócio", "Negócios", "Cliente", "Clientes", "Suporte", "Ferramentas", 
    "Soluções", "Plataforma", "Buscamos", "Procuramos", "Profissional", "Profissionais", 
    "Pessoas", "Ambiente", "Crescimento", "Oportunidade", "Benefícios", "Salário", "Contratação", 
    "Remoto", "Híbrido", "Presencial", "São", "Paulo", "Rio", "Janeiro", "Brasil", 
    "English", "Português", "Spanish", "Mais", "Muito", "Tudo", "Temos", "Estamos", 
    "Fazer", "Participar", "Atuar", "Garantir", "Criar", "Melhores", "Práticas", 
    "Qualidade", "Definir", "Implementar", "Desejáveis", "Principais", "Conhecer",
    "Excelentes", "Habilidades"
}

def extract_potential_new_skills(description: str | None, mapped_skills: list[str]) -> list[str]:
    """
    Busca na descricao termos capitalizados que podem representar tecnologias
    mas que ainda nao constam na nossa lista mapeada.
    """
    if not description:
        return []
    
    # Conjunto de skills ja mapeadas (minusculo para comparacao limpa)
    mapped_lower = {s.lower() for s in mapped_skills}
    
    # Encontra termos capitalizados, siglas ou que contem caracteres de tecnologia (C++, C#, .NET)
    # Removemos o \b no final para permitir caracteres nao-alfanumericos como # e + no final de siglas
    words = re.findall(r"\b[A-Z][a-zA-Z0-9+#\.\-/]*", description)
    
    candidates = set()
    for w in words:
        w_clean = w.strip(".,;:?!-()\"'")
        if len(w_clean) < 2 or len(w_clean) > 20:
            continue
        
        # Ignora se for do dicionario conhecido ou lista de exclusao
        if w_clean.lower() in mapped_lower:
            continue
        if w_clean in EXCLUDE_WORDS or w_clean.lower() in {ew.lower() for ew in EXCLUDE_WORDS}:
            continue
            
        candidates.add(w_clean)
        
    return list(candidates)


# =============================================================================
# Taxonomia de areas — ordem importa: avaliamos do mais especifico para o mais geral
# Isso evita que "Data Science" capture vagas de "MLOps" antes do mlops ter chance
# =============================================================================
AREA_KEYWORDS: dict[str, list[str]] = {
    "ml_mlops": [
        "mlops", "ml engineer", "machine learning engineer",
        "model deployment", "model serving", "ml platform",
        "mlflow", "kubeflow", "sagemaker", "feature store",
    ],
    "data_engineering": [
        "engenheiro de dados", "engenheiros de dados", "data engineer", "data engineers",
        "engenharia de dados", "engenharia dos dados", "pipeline de dados", "data pipeline",
        "etl", "elt", "arquiteto de dados", "data architect",
    ],
    "data_science": [
        "cientista de dados", "cientistas de dados", "data scientist", "data scientists",
        "ciencia de dados", "ciencia dos dados", "ciencias de dados", "ciencias dos dados",
        "pesquisador de dados", "research scientist",
    ],
    "data_analytics": [
        "analista de dados", "analistas de dados", "data analyst", "data analysts",
        "analytics engineer", "analytics engineers", "data analytics", "analista de analytics",
        "analise de dados", "analise dos dados", "analises de dados", "analytics",
    ],
    "bi": [
        "business intelligence", "bi developer", "bi analyst",
        "analista de bi", "analistas de bi", "desenvolvedor de bi",
        "power bi", "tableau developer", "looker developer", "inteligencia de negocios",
    ],
}

# =============================================================================
# Taxonomia de senioridade — ordem: do mais especifico para o mais geral
# "lead" antes de "senior" evita que "tech lead" seja classificado como senior
# Usamos regex com word boundaries (\b) para evitar correspondencias parciais e falsos positivos.
# =============================================================================
SENIORITY_PATTERNS: dict[str, list[str]] = {
    "lead": [
        r"tech\s+lead", r"lead\s+engineer", r"staff\s+engineer",
        r"principal\s+engineer", r"head\s+of\s+data", r"head\s+of\s+analytics",
        r"lead", r"lider", r"lideranca", r"coordenador", r"coordenadora",
        r"supervisor", r"supervisora", r"gerente", r"manager"
    ],
    "estagio": [
        r"estagio", r"estagiario", r"estagiaria", r"estag",
        r"intern", r"internship", r"trainee", r"aprendiz", r"apprentice"
    ],
    "junior": [
        r"junior", r"jr", r"entry\s+level", r"entry-level",
        r"nivel\s+i", r"level\s+i", r"i"
    ],
    "pleno": [
        r"pleno", r"pl", r"mid-level", r"mid\s+level",
        r"nivel\s+ii", r"level\s+ii", r"ii", r"intermediario"
    ],
    "senior": [
        r"senior", r"sr", r"especialista", r"expert",
        r"nivel\s+iii", r"level\s+iii", r"iii"
    ]
}


# =============================================================================
# Dicionario de skills por area — extraidas via regex na descricao da vaga
# Usamos word boundaries (\b) para nao capturar "python" dentro de "cpython"
# =============================================================================
SKILLS_BY_AREA: dict[str, list[str]] = {
    "data_engineering": [
        "Python", "SQL", "Spark", "PySpark", "Airflow", "dbt",
        "Kafka", "AWS", "GCP", "Azure", "Docker", "Kubernetes",
        "PostgreSQL", "Redshift", "BigQuery", "Snowflake", "Databricks",
        "Prefect", "S3", "Glue", "Lambda", "Terraform", "Flink",
    ],
    "data_science": [
        "Python", "R", "TensorFlow", "PyTorch", "scikit-learn", "pandas",
        "NumPy", "MLflow", "Prophet", "statsmodels", "Jupyter",
        "SHAP", "XGBoost", "LightGBM", "SQL", "Spark",
    ],
    "data_analytics": [
        "SQL", "Python", "Power BI", "Tableau", "Looker", "Metabase",
        "Google Analytics", "DAX", "Excel", "Superset", "dbt",
        "BigQuery", "Redshift",
    ],
    "ml_mlops": [
        "MLflow", "Kubeflow", "SageMaker", "BentoML", "Docker",
        "Kubernetes", "TensorFlow", "Ray", "Seldon", "FastAPI",
        "Python", "AWS", "GCP", "Azure", "Terraform",
    ],
    "bi": [
        "Power BI", "Tableau", "Looker", "Qlik", "MicroStrategy",
        "DAX", "SQL", "MQL", "Metabase", "Superset", "Excel",
    ],
}

# Skills universais que extraimos independente da area
UNIVERSAL_SKILLS = ["Python", "SQL", "Git", "Linux", "Docker", "AWS", "GCP", "Azure"]


def _normalize_text(text: str | None) -> str:
    """Remove acentos e converte para minusculo para comparacao case-insensitive."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_only.lower()


# Mapeamentos pré-normalizados em tempo de importação para evitar repetição no loop
AREA_KEYWORDS_NORM = {
    area: [_normalize_text(kw) for kw in keywords]
    for area, keywords in AREA_KEYWORDS.items()
}

SENIORITY_REGEXES = {
    seniority: re.compile(
        r"\b(" + "|".join(patterns) + r")\b",
        re.IGNORECASE
    )
    for seniority, patterns in SENIORITY_PATTERNS.items()
}



def classify_area(title: str, description: str = "") -> str | None:
    """
    Classifica a area da vaga com base no titulo e na descricao em duas etapas.
    
    1. Etapa de Tecnologia (Tech Check):
       Verifica se a vaga pertence a area de tecnologia.
    2. Etapa de Dados (Data Check):
       Verifica se a vaga e de dados.
    3. Etapa de Area Especifica:
       Mapeia para a area correspondente (data_engineering, data_science, etc.).
       Se for de dados mas sem area especifica no titulo, retorna None (unknown).
    """
    title_norm = _normalize_text(title)
    desc_norm = _normalize_text(description)
    
    # 1. TECH CHECK: verifica se a vaga e de tecnologia
    tech_keywords = [
        "python", "sql", "pyspark", "java", "javascript", "typescript", "c#", "c++",
        "php", "ruby", "go", "rust", "scala", "kotlin", "html", "css", "react", "angular",
        "vue", "node", "docker", "kubernetes", "aws", "gcp", "azure", "git", "linux",
        "devops", "ci/cd", "dbt", "airflow", "spark", "hadoop", "hive", "databricks",
        "bigquery", "redshift", "snowflake", "power bi", "powerbi", "tableau", "looker",
        "metabase", "superset", "excel", "desenvolvedor", "developer", "programador",
        "programmer", "tecnologia", "technology", "ti", "it", "sistemas", "software",
        "computacao", "computação", "infraestrutura", "infra", "analytics", "dados", "data",
        "machine learning", "ia", "ai", "dashboard", "banco de dados", "database",
        "analista", "analyst", "engenheiro", "engineer", "cientista", "scientist",
        "bi", "business intelligence", "mlops", "ml", "tech"
    ]
    
    is_tech = (
        any(kw in title_norm for kw in tech_keywords) or
        any(kw in desc_norm for kw in ["python", "sql", "pyspark", "aws", "gcp", "azure", "dbt", "airflow", "spark", "docker", "kubernetes"])
    )
    if not is_tech:
        return "non_tech"
        
    # 2. DATA CHECK: verifica se a vaga e do ramo de dados
    data_title_keywords = [
        "dado", "data", "analytics", "bi", "business intelligence", "scientist",
        "cientista", "pyspark", "dbt", "looker", "powerbi", "tableau", "machine learning",
        "mlops", "ml", "estatistica", "statistic", "modelagem", "modeling",
        "inteligencia de dados", "inteligencia artificial", "artificial intelligence"
    ]
    
    # Contamos ferramentas de dados especificas para evitar falsos positivos
    data_tools = ["sql", "python", "power bi", "powerbi", "tableau", "looker", "dbt", "airflow", "spark", "bigquery", "redshift", "snowflake", "databricks"]
    tool_hits = sum(1 for tool in data_tools if tool in desc_norm)
    
    is_data = (
        any(kw in title_norm for kw in data_title_keywords) or
        (tool_hits >= 2 and any(kw in desc_norm for kw in ["dados", "data", "analytics", "bi"]))
    )
    if not is_data:
        return "non_data"
        
    # 3. AREA CLASSIFICATION (por titulo)
    for area, keywords in AREA_KEYWORDS_NORM.items():
        for keyword in keywords:
            if keyword in title_norm:
                return area

    return None


def classify_seniority(title: str) -> str | None:
    """
    Classifica a senioridade baseado no titulo da vaga.
    Retorna None se nao identificado (ex: vagas sem indicacao de nivel).
    """
    if not title:
        return None
    title_norm = _normalize_text(title)

    for seniority, regex in SENIORITY_REGEXES.items():
        if regex.search(title_norm):
            return seniority

    return None



def extract_skills(description: str | None, area: str | None) -> list[str]:
    """
    Extrai skills tecnicas da descricao usando regex com word boundaries.

    Combina o dicionario especifico da area com as skills universais
    para uma cobertura abrangente sem explodir o dicionario.

    Retorna lista sem duplicatas, em ordem de aparicao no dicionario
    (ou seja, as mais relevantes para a area aparecem primeiro).
    """
    if not description:
        return []

    # Combina skills da area com skills universais
    area_skills = SKILLS_BY_AREA.get(area, []) if area else []
    all_skills = list(dict.fromkeys(area_skills + UNIVERSAL_SKILLS))  # remove duplicatas mantendo ordem

    found = []
    for skill in all_skills:
        # re.escape garante que "C++" ou "scikit-learn" nao quebrem o regex
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, description, re.IGNORECASE):
            found.append(skill)

    return found


def run(**kwargs) -> dict:
    """
    Entry point chamado pela task do Airflow.
    Normaliza vagas, registra skills nao mapeadas e audita o status final no banco.
    """
    from datetime import datetime
    execution_date = kwargs.get("ds") or datetime.now().strftime("%Y-%m-%d")

    from silver.db import update_pipeline_log_end, insert_unmapped_skills_batch

    jobs = fetch_jobs_without_classification()
    logger.info("%d vagas para classificar.", len(jobs))

    stats = {"classified": 0, "area_unknown": 0, "seniority_unknown": 0}
    unmapped_records = []

    # Reune todas as skills catalogadas conhecidas para comparacao
    all_known_skills = []
    for s_list in SKILLS_BY_AREA.values():
        all_known_skills.extend(s_list)
    all_known_skills = list(set(all_known_skills + UNIVERSAL_SKILLS))

    shared_conn = get_connection()
    try:
        with shared_conn:
            for job in jobs:
                job_id      = str(job["job_id"])
                title       = job.get("title", "")
                description = job.get("description", "")

                area      = classify_area(title, description)
                seniority = classify_seniority(title)
                skills    = extract_skills(description, area)

                # Se a classificação sintática resolveu área ou senioridade, marca como 'syntax'
                # Caso contrário, mantém como 'unknown' para ser elegível para o robô de IA
                source = "syntax" if (area or seniority) else "unknown"

                update_job_classification(
                    job_id=job_id,
                    area=area or "unknown",
                    seniority=seniority or "unknown",
                    skills=skills,
                    classification_source=source,
                    conn=shared_conn,
                )

                # Busca skills potenciais nao mapeadas nas descricoes
                potentials = extract_potential_new_skills(description, all_known_skills)
                for p in potentials:
                    unmapped_records.append({"job_id": job_id, "word": p})

                stats["classified"] += 1
                if not area:
                    stats["area_unknown"] += 1
                if not seniority:
                    stats["seniority_unknown"] += 1

            # Insere em lote as novas skills logs
            if unmapped_records:
                insert_unmapped_skills_batch(unmapped_records, conn=shared_conn)

        # Grava auditoria finalizada com SUCESSO
        update_pipeline_log_end(execution_date, stats["classified"], "SUCCESS", conn=shared_conn)
        logger.info(
            "Normalizacao concluida: %d classificadas | %d sem area | %d sem senioridade",
            stats["classified"], stats["area_unknown"], stats["seniority_unknown"]
        )
        return stats
    except Exception as e:
        logger.error("Erro no normalizer: %s", str(e))
        update_pipeline_log_end(execution_date, 0, "FAILED", error_message=str(e))
        raise
    finally:
        shared_conn.close()

