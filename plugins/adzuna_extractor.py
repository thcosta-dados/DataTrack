import os
import json
import requests
from datetime import datetime
from bronze_storage import upload_to_bronze

# Configuracoes de extracao
MAX_DAYS_OLD = 7          # Somente vagas dos ultimos 7 dias (janela semanal)
RESULTS_PER_PAGE = 50     # Maximo permitido pela API
MAX_PAGES_PER_TERM = 5    # Teto de seguranca para nao estourar cota do free tier


def extract_adzuna_jobs():
    app_id = os.getenv('ADZUNA_APP_ID')
    app_key = os.getenv('ADZUNA_APP_KEY')

    if not app_id or not app_key:
        raise ValueError("Credenciais do Adzuna nao encontradas nas variaveis de ambiente.")

    search_terms = [
        "data engineering", "engenharia de dados",
        "data analytics", "analise de dados",
        "data science", "ciencia de dados",
        "business intelligence", "machine learning"
    ]

    country = 'br'
    all_jobs = []

    print(f"Iniciando extracao do Adzuna (vagas dos ultimos {MAX_DAYS_OLD} dias)...")

    for term in search_terms:
        term_jobs = _fetch_all_pages(app_id, app_key, country, term)
        all_jobs.extend(term_jobs)

    print(f"\nTotal bruto extraido: {len(all_jobs)} vagas.")
    print("(Duplicatas serao tratadas na Camada Silver pela deduplicacao por ID)")

    final_data = {
        "source": "adzuna",
        "extracted_at": datetime.now().isoformat(),
        "max_days_old": MAX_DAYS_OLD,
        "total_results": len(all_jobs),
        "results": all_jobs
    }

    file_key = upload_to_bronze(final_data, "adzuna")
    print(f"Sucesso! Dados salvos no MinIO: s3://datatrack-bronze/{file_key}")
    return file_key


def _fetch_all_pages(app_id, app_key, country, term):
    """
    Busca TODAS as paginas de resultados para um termo de busca.
    A API retorna no max 50 por pagina, entao iteramos ate:
    - Os resultados acabarem, OU
    - Atingir MAX_PAGES_PER_TERM (teto de seguranca)
    """
    collected = []
    page = 1

    print(f"  Buscando vagas para: '{term}'...")

    while page <= MAX_PAGES_PER_TERM:
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
        params = {
            'app_id': app_id,
            'app_key': app_key,
            'results_per_page': RESULTS_PER_PAGE,
            'what': term,
            'max_days_old': MAX_DAYS_OLD,
            'content-type': 'application/json'
        }

        response = requests.get(url, params=params, timeout=30)

        if response.status_code != 200:
            print(f"    -> Erro HTTP {response.status_code} na pagina {page}. Parando paginacao.")
            break

        data = response.json()
        jobs = data.get('results', [])
        total_available = data.get('count', 0)

        if not jobs:
            break

        collected.extend(jobs)
        print(f"    -> Pagina {page}: {len(jobs)} vagas (total disponivel: {total_available})")

        if len(collected) >= total_available:
            break

        page += 1

    print(f"    -> Subtotal para '{term}': {len(collected)} vagas coletadas")
    return collected


if __name__ == "__main__":
    extract_adzuna_jobs()
