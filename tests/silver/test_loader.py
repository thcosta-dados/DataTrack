"""
tests/silver/test_loader.py
----------------------------
Testes unitários para a lógica de normalização, mapeamento e parsing de dados
no módulo silver/loader.py.

Estes testes não realizam chamadas externas (MinIO, banco de dados, etc.) e validam
as transformações de dados de forma determinística.
"""

import pytest
from datetime import date
from silver.loader import (
    _normalize_date,
    _normalize_is_remote,
    _get_nested,
    _map_job,
)


# =============================================================================
# Testes de _get_nested
# =============================================================================

def test_get_nested_valido():
    data = {
        "company": {
            "display_name": "Nubank",
            "details": {"size": "Large"}
        }
    }
    assert _get_nested(data, "company.display_name") == "Nubank"
    assert _get_nested(data, "company.details.size") == "Large"


def test_get_nested_caminho_inexistente():
    data = {"company": {"name": "Nubank"}}
    assert _get_nested(data, "company.address") is None
    assert _get_nested(data, "location.city") is None


def test_get_nested_tipo_invalido_no_caminho():
    data = {"company": "Nubank"}  # String em vez de dict no nó intermediário
    assert _get_nested(data, "company.display_name") is None


# =============================================================================
# Testes de _normalize_date
# =============================================================================

def test_normalize_date_unix_timestamp():
    # Evita problemas de timezone na maquina local
    from datetime import datetime
    expected = datetime.fromtimestamp(1779926400).date()
    assert _normalize_date(1779926400) == expected
    assert _normalize_date(1779926400.0) == expected


def test_normalize_date_iso_string():
    assert _normalize_date("2026-06-03T15:30:00.123Z") == date(2026, 6, 3)
    assert _normalize_date("2026-06-03T15:30:00") == date(2026, 6, 3)


def test_normalize_date_formato_yyyy_mm_dd():
    assert _normalize_date("2026-05-20") == date(2026, 5, 20)


def test_normalize_date_formato_dd_mm_yyyy():
    assert _normalize_date("20/05/2026") == date(2026, 5, 20)


def test_normalize_date_invalidos_ou_nulos():
    assert _normalize_date(None) is None
    assert _normalize_date("") is None
    assert _normalize_date("data-invalida") is None
    assert _normalize_date([]) is None


# =============================================================================
# Testes de _normalize_is_remote
# =============================================================================

def test_normalize_is_remote_boolean():
    assert _normalize_is_remote(True, "remoteok") is True
    assert _normalize_is_remote(False, "remoteok") is False


def test_normalize_is_remote_string():
    assert _normalize_is_remote("remote", "gupy") is True
    assert _normalize_is_remote("remoto", "gupy") is True
    assert _normalize_is_remote("Home Office", "gupy") is True
    assert _normalize_is_remote("hybrid", "gupy") is False
    assert _normalize_is_remote("on-site", "gupy") is False
    assert _normalize_is_remote("presencial", "gupy") is False


# =============================================================================
# Testes de _map_job
# =============================================================================

def test_map_job_adzuna():
    raw_job = {
        "id": "adz-123",
        "title": "Engenheiro de Dados Pleno",
        "company": {"display_name": "Stark Industries"},
        "location": {"display_name": "São Paulo, SP"},
        "description": "Trabalhar com pipelines de dados e ETL.",
        "redirect_url": "https://adzuna.com/job/123",
        "created": "2026-06-01T12:00:00Z"
    }
    mapped = _map_job(raw_job, "adzuna")
    assert mapped["source"] == "adzuna"
    assert mapped["source_id"] == "adz-123"
    assert mapped["title"] == "Engenheiro de Dados Pleno"
    assert mapped["company"] == "Stark Industries"
    assert mapped["location"] == "São Paulo, SP"
    assert mapped["url"] == "https://adzuna.com/job/123"
    assert mapped["posted_at"] == date(2026, 6, 1)
    assert mapped["is_remote"] is False


def test_map_job_remoteok():
    raw_job = {
        "id": "ro-555",
        "position": "Data Engineer",
        "company": "GitLab",
        "location": "Worldwide",
        "description": "GitLab is a remote-only company.",
        "url": "https://remoteok.com/job/555",
        "date": 1779926400  # 2026-05-29
    }
    from datetime import datetime
    expected = datetime.fromtimestamp(1779926400).date()
    mapped = _map_job(raw_job, "remoteok")
    assert mapped["source"] == "remoteok"
    assert mapped["source_id"] == "ro-555"
    assert mapped["title"] == "Data Engineer"
    assert mapped["company"] == "GitLab"
    assert mapped["url"] == "https://remoteok.com/job/555"
    assert mapped["posted_at"] == expected
    assert mapped["is_remote"] is True  # RemoteOK é sempre remoto por padrão


def test_map_job_inferencia_remoto_por_texto():
    # Caso onde o campo remoto é nulo/falso no JSON original, mas o título ou
    # a localização indicam que é trabalho remoto
    raw_job = {
        "id": "adz-999",
        "title": "Analista de Dados (Home Office)",
        "company": {"display_name": "ACME Corp"},
        "location": {"display_name": "São Paulo, SP"},
        "description": "Buscamos analistas para trabalhar em regime home office.",
        "redirect_url": "https://adzuna.com/job/999",
        "created": "2026-06-01T12:00:00Z"
    }
    mapped = _map_job(raw_job, "adzuna")
    assert mapped["is_remote"] is True
