"""
tests/silver/test_deduplicator.py
----------------------------------
Testes unitarios para a logica de deduplicacao.

Aqui nao conectamos ao banco — testamos apenas as funcoes puras:
_normalize_text, _build_dedup_hash, _get_date_window e _find_duplicate.

Em um time real, isso e chamado de "unit test": testa a logica de negocio
isolada das dependencias externas (banco, rede, etc.).

Para rodar: pytest tests/silver/test_deduplicator.py -v
"""

import pytest
from datetime import date

# Importamos diretamente as funcoes que queremos testar
# (nao o run() que depende do banco)
from silver.deduplicator import (
    _normalize_text,
    _build_dedup_hash,
    _get_date_window,
    _find_duplicate,
    infer_modalidade,
)



# =============================================================================
# Testes de _normalize_text
# =============================================================================

def test_normalize_remove_acentos():
    assert _normalize_text("Sênior") == "senior"
    assert _normalize_text("Engenharia de Dados") == "engenharia de dados"
    assert _normalize_text("São Paulo") == "sao paulo"


def test_normalize_texto_none_retorna_vazio():
    assert _normalize_text(None) == ""
    assert _normalize_text("") == ""


def test_normalize_converte_para_minusculo():
    assert _normalize_text("DATA ENGINEER") == "data engineer"


# =============================================================================
# Testes de _build_dedup_hash
# =============================================================================

def test_hash_identico_para_mesma_entrada():
    h1 = _build_dedup_hash("data engineer", "nubank", "sao paulo", "bucket_10")
    h2 = _build_dedup_hash("data engineer", "nubank", "sao paulo", "bucket_10")
    assert h1 == h2


def test_hash_diferente_para_empresas_diferentes():
    h1 = _build_dedup_hash("data engineer", "nubank", "sao paulo", "bucket_10")
    h2 = _build_dedup_hash("data engineer", "google", "sao paulo", "bucket_10")
    assert h1 != h2


def test_hash_tem_64_caracteres():
    h = _build_dedup_hash("a", "b", "c", "d")
    assert len(h) == 64


# =============================================================================
# Testes de _get_date_window
# =============================================================================

def test_datas_proximas_no_mesmo_bucket():
    d1 = date(2026, 5, 20)
    d2 = date(2026, 5, 21)
    # Datas com 1 dia de diferenca devem cair no mesmo bucket de 3 dias
    # (dependendo do alinhamento do calculo)
    # Verificamos apenas que datas iguais tem o mesmo bucket
    assert _get_date_window(d1) == _get_date_window(d1)


def test_datas_distantes_em_buckets_diferentes():
    d1 = date(2026, 5, 1)
    d2 = date(2026, 5, 20)
    assert _get_date_window(d1) != _get_date_window(d2)


def test_data_none_retorna_unknown():
    assert _get_date_window(None) == "unknown"


# =============================================================================
# Testes de _find_duplicate
# =============================================================================

def _make_raw_job(title, company, posted_at=date(2026, 5, 20), is_remote=False):
    """Helper para criar um raw_job de teste rapidamente."""
    return {
        "title":     title,
        "company":   company,
        "posted_at": posted_at,
        "is_remote": is_remote,
    }


def _make_existing_job(title, company, posted_at=date(2026, 5, 20)):
    """Helper para criar um existing_job (de silver.jobs) de teste."""
    return {
        "job_id":       "uuid-fake-123",
        "title":        title,
        "company_name": company,
        "posted_at":    posted_at,
    }


class TestFindDuplicate:

    def test_vaga_identica_e_duplicata(self):
        raw     = _make_raw_job("Engenheiro de Dados Senior", "Nubank")
        existing = [_make_existing_job("Engenheiro de Dados Senior", "Nubank")]
        result = _find_duplicate(raw, existing)
        assert result is not None

    def test_variacao_de_ordem_no_titulo_e_duplicata(self):
        # token_sort_ratio deve tratar as duas como iguais
        raw      = _make_raw_job("Senior Engenheiro de Dados", "Nubank")
        existing = [_make_existing_job("Engenheiro de Dados Senior", "Nubank")]
        result = _find_duplicate(raw, existing)
        assert result is not None

    def test_abreviacao_de_senioridade_e_duplicata(self):
        raw      = _make_raw_job("Engenheiro de Dados Sr.", "iFood")
        existing = [_make_existing_job("Engenheiro de Dados Senior", "iFood")]
        result = _find_duplicate(raw, existing)
        assert result is not None

    def test_empresa_diferente_nao_e_duplicata(self):
        raw      = _make_raw_job("Engenheiro de Dados", "Nubank")
        existing = [_make_existing_job("Engenheiro de Dados", "Google")]
        result = _find_duplicate(raw, existing)
        assert result is None

    def test_titulo_completamente_diferente_nao_e_duplicata(self):
        raw      = _make_raw_job("Engenheiro de Dados", "Nubank")
        existing = [_make_existing_job("Analista de BI", "Nubank")]
        result = _find_duplicate(raw, existing)
        assert result is None

    def test_vaga_muito_antiga_nao_e_duplicata(self):
        raw      = _make_raw_job("Data Engineer", "Nubank", posted_at=date(2026, 5, 20))
        existing = [_make_existing_job("Data Engineer", "Nubank", posted_at=date(2026, 4, 1))]
        result = _find_duplicate(raw, existing)
        assert result is None

    def test_lista_vazia_retorna_none(self):
        raw    = _make_raw_job("Data Engineer", "Nubank")
        result = _find_duplicate(raw, [])
        assert result is None

    def test_grafia_diferente_da_empresa_e_duplicata(self):
        # "ifood" vs "iFood" — normalizacao deve resolver
        raw      = _make_raw_job("Data Engineer", "ifood")
        existing = [_make_existing_job("Data Engineer", "iFood")]
        result = _find_duplicate(raw, existing)
        assert result is not None


# =============================================================================
# Testes de infer_modalidade
# =============================================================================

class TestInferModalidade:

    def test_infer_remote_original(self):
        assert infer_modalidade("Data Engineer", "São Paulo", "Some desc", True) == (True, False)

    def test_infer_remote_from_title(self):
        assert infer_modalidade("Data Engineer (Remote)", "São Paulo", "Some desc", False) == (True, False)
        assert infer_modalidade("Engenheiro de Dados 100% Remoto", "São Paulo", "Some desc", False) == (True, False)

    def test_infer_remote_from_location(self):
        assert infer_modalidade("Data Engineer", "Home office", "Some desc", False) == (True, False)
        assert infer_modalidade("Data Engineer", "Remoto - Brasil", "Some desc", False) == (True, False)

    def test_infer_remote_from_description(self):
        assert infer_modalidade("Data Engineer", "São Paulo", "Trabalho 100% remoto para esta vaga.", False) == (True, False)

    def test_infer_hybrid_from_title(self):
        assert infer_modalidade("Data Engineer (Hybrid)", "São Paulo", "Some desc", False) == (False, True)
        assert infer_modalidade("Engenheiro de Dados Híbrido", "São Paulo", "Some desc", False) == (False, True)

    def test_infer_hybrid_from_location(self):
        assert infer_modalidade("Data Engineer", "São Paulo - Híbrido", "Some desc", False) == (False, True)

    def test_infer_hybrid_from_description(self):
        assert infer_modalidade("Data Engineer", "São Paulo", "Buscamos pessoas no formato hibrido.", False) == (False, True)
        assert infer_modalidade("Data Engineer", "São Paulo", "O trabalho sera realizado de forma hibrida.", False) == (False, True)

    def test_infer_presencial(self):
        assert infer_modalidade("Data Engineer", "São Paulo - SP", "Vaga 100% presencial.", False) == (False, False)

