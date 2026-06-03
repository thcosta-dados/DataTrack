"""
tests/silver/test_ia_classifier.py
-----------------------------------
Testes unitários para a classificação de vagas com IA no módulo silver/ia_classifier.py.

Utiliza mocks para simular a API do Gemini e as operações de banco de dados,
garantindo que o classificador funcione corretamente sob diferentes cenários de resposta
e erros da API (incluindo rate limit).
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from silver.ia_classifier import (
    classify_description_with_gemini,
    run,
    VALID_AREAS,
    VALID_SENIORITIES,
)


# =============================================================================
# Testes de classify_description_with_gemini
# =============================================================================

def test_classify_description_sucesso():
    # Cria mock do modelo do Gemini
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"area": "data_engineering", "seniority": "senior"}'
    mock_model.generate_content.return_value = mock_response

    result = classify_description_with_gemini(mock_model, "Data Engineer Sr", "Requisitos: Spark, Airflow, 5 anos de experiência")
    
    assert result == {"area": "data_engineering", "seniority": "senior"}
    mock_model.generate_content.assert_called_once()


def test_classify_description_valores_invalidos_substituidos_por_unknown():
    mock_model = MagicMock()
    mock_response = MagicMock()
    # Retorna valores que não estão no set de válidos
    mock_response.text = '{"area": "desenvolvedor_web", "seniority": "pleno"}'
    mock_model.generate_content.return_value = mock_response

    result = classify_description_with_gemini(mock_model, "Vaga Genérica", "Descrição genérica")
    
    # 'desenvolvedor_web' não é área válida -> deve ir para 'unknown'
    # 'pleno' é senioridade válida -> deve se manter 'pleno'
    assert result == {"area": "unknown", "seniority": "pleno"}


def test_classify_description_retorno_incompleto_substituido_por_unknown():
    mock_model = MagicMock()
    mock_response = MagicMock()
    # JSON sem chave 'seniority'
    mock_response.text = '{"area": "data_science"}'
    mock_model.generate_content.return_value = mock_response

    result = classify_description_with_gemini(mock_model, "Cientista de Dados", "Descrição")
    assert result == {"area": "data_science", "seniority": "unknown"}


def test_classify_description_error_de_quota_ou_rate_limit():
    mock_model = MagicMock()
    # Simula erro de cota / rate limit da API
    mock_model.generate_content.side_effect = Exception("Resource has been exhausted (e.g. check quota).")

    result = classify_description_with_gemini(mock_model, "Qualquer", "Qualquer")
    assert result == "RATE_LIMIT"


def test_classify_description_erro_generico_retorna_none():
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("Algum erro desconhecido na API")

    result = classify_description_with_gemini(mock_model, "Qualquer", "Qualquer")
    assert result is None


# =============================================================================
# Testes do entrypoint run()
# =============================================================================

@patch("silver.ia_classifier.os.environ.get")
def test_run_sem_api_key_pula_execucao(mock_env_get):
    mock_env_get.return_value = None  # Sem GEMINI_API_KEY
    
    stats = run()
    assert stats == {"processed": 0, "status": "skipped"}


@patch("silver.ia_classifier.time.sleep")  # Evita o delay de 12 segundos nos testes
@patch("silver.ia_classifier.get_connection")
@patch("silver.ia_classifier.fetch_unknown_active_jobs")
@patch("silver.ia_classifier.update_job_classification")
@patch("silver.ia_classifier.genai.GenerativeModel")
@patch("silver.ia_classifier.os.environ.get")
def test_run_sucesso(mock_env_get, mock_gen_model, mock_update, mock_fetch, mock_conn, mock_sleep):
    # Setup de mocks
    mock_env_get.return_value = "fake_key_123"
    
    mock_db_conn = MagicMock()
    mock_conn.return_value = mock_db_conn
    
    # Retorna 2 vagas de teste
    mock_fetch.return_value = [
        {"job_id": "uuid-1", "title": "Engenheiro de Dados", "skills": ["Python", "SQL"]},
        {"job_id": "uuid-2", "title": "Analista de BI", "skills": ["Power BI"]}
    ]
    
    # Mock do Gemini model retornar JSONs válidos
    mock_model_instance = MagicMock()
    mock_gen_model.return_value = mock_model_instance
    
    mock_response = MagicMock()
    mock_response.text = '{"area": "data_engineering", "seniority": "junior"}'
    mock_model_instance.generate_content.return_value = mock_response

    stats = run()

    assert stats["processed"] == 2
    assert stats["success"] == 2
    assert stats["failed"] == 0
    
    # Verifica se chamou update_job_classification para cada vaga
    assert mock_update.call_count == 2
    # Verifica se respeitou o sleep a partir da segunda vaga (chamado 1 vez para a vaga 2)
    mock_sleep.assert_called_once_with(12)


@patch("silver.ia_classifier.time.sleep")
@patch("silver.ia_classifier.get_connection")
@patch("silver.ia_classifier.fetch_unknown_active_jobs")
@patch("silver.ia_classifier.classify_description_with_gemini")
@patch("silver.ia_classifier.os.environ.get")
def test_run_interrompe_no_rate_limit(mock_env_get, mock_classify, mock_fetch, mock_conn, mock_sleep):
    mock_env_get.return_value = "fake_key_123"
    
    # 2 vagas para classificar
    mock_fetch.return_value = [
        {"job_id": "uuid-1", "title": "Job 1", "skills": []},
        {"job_id": "uuid-2", "title": "Job 2", "skills": []}
    ]
    
    # A primeira vaga atinge o rate limit
    mock_classify.return_value = "RATE_LIMIT"

    stats = run()

    # O loop deve dar break imediatamente e processar apenas 1 (que falhou devido ao rate limit)
    assert stats["processed"] == 0
    assert stats["success"] == 0
    assert stats["failed"] == 0
