"""
tests/silver/test_link_checker.py
----------------------------------
Testes unitários assíncronos e síncronos para o link_checker.py.

Usa mock de httpx para testar chamadas de rede concorrentes e validação de URLs,
e mock de conexão PostgreSQL para verificar o fluxo do entrypoint run().
"""

import pytest
import asyncio
import httpx
from unittest.mock import MagicMock, AsyncMock, patch
from silver.link_checker import (
    check_single_url,
    check_all_urls,
    run,
    EXPIRED_URL_PATTERNS,
)

# =============================================================================
# Testes de check_single_url
# =============================================================================

@pytest.mark.asyncio
async def test_check_single_url_ativa_com_sucesso():
    client = AsyncMock(spec=httpx.AsyncClient)
    semaphore = asyncio.Semaphore(1)
    
    # Simula retorno status 200 com HTML normal de vaga ativa
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.url = httpx.URL("https://exemplo.com/vaga/123")
    mock_response.text = "<html><body>Vaga aberta para Engenharia de Dados! Inscreva-se.</body></html>"
    client.get.return_value = mock_response

    job_id, is_active = await check_single_url(client, semaphore, "uuid-1", "https://exemplo.com/vaga/123")
    
    assert job_id == "uuid-1"
    assert is_active is True


@pytest.mark.asyncio
async def test_check_single_url_inativa_por_404():
    client = AsyncMock(spec=httpx.AsyncClient)
    semaphore = asyncio.Semaphore(1)
    
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    client.get.return_value = mock_response

    job_id, is_active = await check_single_url(client, semaphore, "uuid-1", "https://exemplo.com/vaga/123")
    
    assert is_active is False


@pytest.mark.asyncio
async def test_check_single_url_inativa_por_url_de_redirecionamento_expirada():
    client = AsyncMock(spec=httpx.AsyncClient)
    semaphore = asyncio.Semaphore(1)
    
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    # Redirecionou para a página de expiração
    mock_response.url = httpx.URL("https://gupy.io/vaga-nao-disponivel")
    mock_response.text = "Vaga não encontrada"
    client.get.return_value = mock_response

    job_id, is_active = await check_single_url(client, semaphore, "uuid-1", "https://exemplo.com/vaga/123")
    
    assert is_active is False


@pytest.mark.asyncio
async def test_check_single_url_inativa_por_conteudo_expirado_no_html():
    client = AsyncMock(spec=httpx.AsyncClient)
    semaphore = asyncio.Semaphore(1)
    
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.url = httpx.URL("https://exemplo.com/vaga/123")
    # HTML contém expressão que sinaliza expiração (sem acento)
    mock_response.text = "<html><body>Infelizmente essa vaga nao esta mais disponivel no portal.</body></html>"
    client.get.return_value = mock_response

    job_id, is_active = await check_single_url(client, semaphore, "uuid-1", "https://exemplo.com/vaga/123")
    
    assert is_active is False


@pytest.mark.asyncio
async def test_check_single_url_erro_de_conexao_mantem_ativa():
    client = AsyncMock(spec=httpx.AsyncClient)
    semaphore = asyncio.Semaphore(1)
    
    # Erros de timeout ou rede temporários não devem inativar a vaga no primeiro erro
    client.get.side_effect = httpx.ConnectTimeout("Timeout ao conectar")

    job_id, is_active = await check_single_url(client, semaphore, "uuid-1", "https://exemplo.com/vaga/123")
    
    assert is_active is True


# =============================================================================
# Testes de check_all_urls
# =============================================================================

@pytest.mark.asyncio
@patch("silver.link_checker.check_single_url")
async def test_check_all_urls(mock_check_single):
    # Simula o resultado de 3 vagas testadas
    mock_check_single.side_effect = [
        ("uuid-1", True),   # Continua ativa
        ("uuid-2", False),  # Expira
        ("uuid-3", False),  # Expira
    ]
    
    jobs = [
        {"job_id": "uuid-1", "url": "https://url1.com"},
        {"job_id": "uuid-2", "url": "https://url2.com"},
        {"job_id": "uuid-3", "url": "https://url3.com"},
    ]
    
    inactive_ids = await check_all_urls(jobs)
    
    # Deve retornar a lista com os IDs das vagas inativas
    assert inactive_ids == ["uuid-2", "uuid-3"]
    assert mock_check_single.call_count == 3


# =============================================================================
# Testes do entrypoint run()
# =============================================================================

# Para testar a função síncrona run() que roda asyncio.run() internamente, 
# nós mockamos a chamada de check_all_urls para evitar criar loop dentro do teste.
@patch("silver.link_checker.get_connection")
@patch("silver.link_checker.inactivate_expired_jobs_by_age")
@patch("silver.link_checker.fetch_active_recent_jobs")
@patch("silver.link_checker.check_all_urls")
@patch("silver.link_checker.inactivate_jobs_batch")
def test_run_link_checker(mock_inactivate_batch, mock_check_urls, mock_fetch_active, mock_inactivate_age, mock_conn):
    # Setup de mocks
    mock_db_conn = MagicMock()
    mock_conn.return_value = mock_db_conn
    
    mock_inactivate_age.return_value = 5  # 5 inativadas por tempo
    mock_fetch_active.return_value = [
        {"job_id": "uuid-1", "url": "https://url1.com"},
        {"job_id": "uuid-2", "url": "https://url2.com"}
    ]
    
    # check_all_urls é corotina mockada retornando os IDs inativos
    mock_check_urls.return_value = ["uuid-2"]
    mock_inactivate_batch.return_value = 1  # 1 inativada por link

    # Como run() chama asyncio.run(check_all_urls(...)), precisamos que o mock
    # de check_all_urls se comporte como uma corotina ou seja esperado corretamente.
    # No Python moderno, patch de uma função async retorna um AsyncMock por padrão
    # ou podemos configurar seu return_value.
    
    stats = run()
    
    assert stats == {
        "expired_by_age": 5,
        "tested": 2,
        "expired_by_link": 1
    }
    
    mock_inactivate_age.assert_called_once_with(mock_db_conn)
    mock_fetch_active.assert_called_once_with(mock_db_conn)
    mock_inactivate_batch.assert_called_once_with(mock_db_conn, ["uuid-2"])
