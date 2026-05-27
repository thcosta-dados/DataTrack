"""
tests/silver/test_normalizer.py
---------------------------------
Testes unitarios para a logica de classificacao e extracao de skills.

Testamos classify_area, classify_seniority e extract_skills de forma isolada,
com titulos e descricoes que representam casos reais do mercado brasileiro.

Para rodar: pytest tests/silver/test_normalizer.py -v
"""

import pytest

from silver.normalizer import (
    classify_area,
    classify_seniority,
    extract_skills,
    extract_potential_new_skills,
)


# =============================================================================
# Testes de classify_area
# =============================================================================

class TestClassifyArea:

    def test_data_engineering_titulo_portugues(self):
        assert classify_area("Engenheiro de Dados Senior") == "data_engineering"

    def test_data_engineering_titulo_ingles(self):
        assert classify_area("Senior Data Engineer") == "data_engineering"

    def test_data_science(self):
        assert classify_area("Cientista de Dados Pleno") == "data_science"

    def test_data_analytics(self):
        assert classify_area("Analista de Dados Junior") == "data_analytics"

    def test_analytics_engineer(self):
        assert classify_area("Analytics Engineer") == "data_analytics"

    def test_ml_mlops_nao_classificado_como_data_science(self):
        # MLOps deve ter prioridade sobre Data Science
        assert classify_area("MLOps Engineer Senior") == "ml_mlops"

    def test_bi_developer(self):
        assert classify_area("Analista de BI Pleno") == "bi"

    def test_titulo_sem_area_retorna_non_data(self):
        assert classify_area("Estagiário de TI") == "non_data"

    def test_titulo_vazio_retorna_non_tech(self):
        assert classify_area("") == "non_tech"

    def test_titulo_none_retorna_non_tech(self):
        assert classify_area(None) == "non_tech"

    def test_acentos_nao_impedem_classificacao(self):
        # O normalizer deve lidar com acentos no titulo
        assert classify_area("Engenharia de Dados") == "data_engineering"

    def test_ciencias_de_dados_plural(self):
        assert classify_area("Estágio em Ciências de Dados") == "data_science"

    def test_data_analytics_english(self):
        assert classify_area("Internship in Data Analytics") == "data_analytics"

    def test_vaga_generica_com_skills_dados(self):
        # Titulo generico de TI com descricao contendo SQL e Python -> Vaga de Dados (unknown area)
        assert classify_area("Estagiário de TI", "Conhecimentos avançados em Python e banco de dados SQL.") is None

    def test_vaga_compras_non_tech(self):
        assert classify_area("Comprador de Insumos", "Responsável pelas cotações de insumos da empresa.") == "non_tech"


# =============================================================================
# Testes de classify_seniority
# =============================================================================

class TestClassifySeniority:

    def test_senior_portugues(self):
        assert classify_seniority("Engenheiro de Dados Sênior") == "senior"

    def test_senior_ingles(self):
        assert classify_seniority("Senior Data Engineer") == "senior"

    def test_senior_abreviado(self):
        assert classify_seniority("Data Engineer Sr.") == "senior"

    def test_senior_abreviacoes_variadas(self):
        assert classify_seniority("Engenheiro de Dados SR") == "senior"
        assert classify_seniority("Engenheiro de Dados Sr") == "senior"
        assert classify_seniority("Engenheiro de Dados sr") == "senior"
        assert classify_seniority("SR Engenheiro de Dados") == "senior"
        assert classify_seniority("Engenheiro de Dados SR.") == "senior"

    def test_junior(self):
        assert classify_seniority("Analista de Dados Junior") == "junior"

    def test_junior_abreviado(self):
        assert classify_seniority("Data Engineer Jr.") == "junior"

    def test_junior_abreviacoes_variadas(self):
        assert classify_seniority("Engenheiro de Dados JR") == "junior"
        assert classify_seniority("Engenheiro de Dados Jr") == "junior"
        assert classify_seniority("Engenheiro de Dados jr") == "junior"
        assert classify_seniority("JR Engenheiro de Dados") == "junior"
        assert classify_seniority("Engenheiro de Dados JR.") == "junior"

    def test_pleno(self):
        assert classify_seniority("Cientista de Dados Pleno") == "pleno"

    def test_pleno_abreviacoes_variadas(self):
        assert classify_seniority("Engenheiro de Dados PL") == "pleno"
        assert classify_seniority("Engenheiro de Dados Pl") == "pleno"
        assert classify_seniority("Engenheiro de Dados pl") == "pleno"
        assert classify_seniority("PL Engenheiro de Dados") == "pleno"
        assert classify_seniority("Engenheiro de Dados PL.") == "pleno"

    def test_estagio(self):
        assert classify_seniority("Estagiário de BI") == "estagio"

    def test_trainee(self):
        assert classify_seniority("Data Trainee") == "estagio"

    def test_lead_tem_prioridade_sobre_senior(self):
        assert classify_seniority("Tech Lead de Dados") == "lead"

    def test_titulo_sem_senioridade_retorna_none(self):
        assert classify_seniority("Data Engineer") is None

    def test_titulo_vazio_retorna_none(self):
        assert classify_seniority("") is None



# =============================================================================
# Testes de extract_skills
# =============================================================================

class TestExtractSkills:

    def test_skills_de_data_engineering(self):
        descricao = "Experiencia com Python, SQL, Airflow e dbt para construcao de pipelines."
        skills = extract_skills(descricao, "data_engineering")
        assert "Python" in skills
        assert "SQL" in skills
        assert "Airflow" in skills
        assert "dbt" in skills

    def test_skills_case_insensitive(self):
        descricao = "Conhecimento em python e sql obrigatorio."
        skills = extract_skills(descricao, "data_engineering")
        assert "Python" in skills
        assert "SQL" in skills

    def test_skills_de_bi(self):
        descricao = "Dominio de Power BI e DAX avancado. SQL para consultas."
        skills = extract_skills(descricao, "bi")
        assert "Power BI" in skills
        assert "DAX" in skills
        assert "SQL" in skills

    def test_descricao_sem_skills_retorna_lista_vazia(self):
        descricao = "Vaga para profissional com experiencia em comunicacao e lideranca."
        skills = extract_skills(descricao, "data_engineering")
        assert skills == []

    def test_descricao_none_retorna_lista_vazia(self):
        skills = extract_skills(None, "data_engineering")
        assert skills == []

    def test_area_none_ainda_extrai_skills_universais(self):
        # Mesmo sem area definida, Python e SQL sao universais e devem ser extraidas
        descricao = "Profissional deve ter dominio em Python e SQL."
        skills = extract_skills(descricao, None)
        assert "Python" in skills
        assert "SQL" in skills

    def test_sem_duplicatas_no_resultado(self):
        # Python aparece tanto em data_engineering quanto em universal_skills
        descricao = "Python, Python e mais Python."
        skills = extract_skills(descricao, "data_engineering")
        assert skills.count("Python") == 1

    def test_skill_com_caractere_especial(self):
        # scikit-learn tem hifen — o regex.escape deve tratar isso
        descricao = "Experiencia com scikit-learn e XGBoost."
        skills = extract_skills(descricao, "data_science")
        assert "scikit-learn" in skills
        assert "XGBoost" in skills


# =============================================================================
# Testes de extract_potential_new_skills (Melhoria A)
# =============================================================================

class TestExtractPotentialNewSkills:

    def test_extrai_siglas_e_termos_capitalizados_desconhecidos(self):
        descricao = "Desejavel experiencia com Rust, Go e COBOL, alem de Kubernetes."
        mapped_skills = ["Kubernetes", "Python", "SQL"]
        potentials = extract_potential_new_skills(descricao, mapped_skills)
        assert "Rust" in potentials
        assert "Go" in potentials
        assert "COBOL" in potentials
        assert "Kubernetes" not in potentials  # Ja estava mapeada

    def test_ignora_stop_words_capitalizadas(self):
        descricao = "A empresa busca Profissionais de Engenharia com Excelentes habilidades."
        mapped_skills = ["Python", "SQL"]
        potentials = extract_potential_new_skills(descricao, mapped_skills)
        # Palavras em EXCLUDE_WORDS nao devem ser extraidas
        assert "Empresa" not in potentials
        assert "Profissionais" not in potentials
        assert "Engenharia" not in potentials
        assert "Excelentes" not in potentials

    def test_extrai_termos_com_caracteres_especiais(self):
        descricao = "Conhecimento em C# e C++."
        mapped_skills = ["Python", "SQL"]
        potentials = extract_potential_new_skills(descricao, mapped_skills)
        assert "C#" in potentials
        assert "C++" in potentials
