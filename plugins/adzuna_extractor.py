import os
import json
import requests
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# Configuracoes de extracao
MAX_DAYS_OLD = 7          # Somente vagas dos ultimos 7 dias (janela semanal)
RESULTS_PER_PAGE = 50     # Maximo permitido pela API
MAX_PAGES_PER_TERM = 5    # Teto de seguranca para nao estourar cota do free tier


def extract_adzuna_jobs():
    app_id = os.getenv('ADZUNA_APP_ID')
    app_key = os.getenv('ADZUNA_APP_KEY')

    if not app_id or not app_key:
        raise ValueError("Credenciais do Adzuna nao encontradas nas variaveis de ambiente.")

    # Cada termo vira uma requisicao separada porque a API da Adzuna
    # nao lida bem com queries booleanas longas
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

    # Monta o JSON final com metadados de rastreabilidade
    final_data = {
        "source": "adzuna",
        "extracted_at": datetime.now().isoformat(),
        "max_days_old": MAX_DAYS_OLD,
        "total_results": len(all_jobs),
        "results": all_jobs
    }

    # Salva no MinIO (Data Lake Bronze)
    file_key = _upload_to_minio(final_data)

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

        # Se ja coletamos tudo que existe, nao precisa pedir mais paginas
        if len(collected) >= total_available:
            break

        page += 1

    print(f"    -> Subtotal para '{term}': {len(collected)} vagas coletadas")
    return collected


def _upload_to_minio(data):
    """
    Conecta ao MinIO e salva o JSON na camada Bronze,
    particionado por data (adzuna/YYYY-MM-DD/raw_jobs.json).
    """
    minio_user = os.getenv('MINIO_ROOT_USER', 'admin')
    minio_password = os.getenv('MINIO_ROOT_PASSWORD', 'adminpassword')

    s3_client = boto3.client(
        's3',
        endpoint_url='http://minio:9000',
        aws_access_key_id=minio_user,
        aws_secret_access_key=minio_password,
        region_name='us-east-1'
    )

    bucket_name = 'datatrack-bronze'

    # Cria o bucket se nao existir (idempotente)
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError:
        s3_client.create_bucket(Bucket=bucket_name)

    # Particionamento por data para facilitar consultas futuras
    date_str = datetime.now().strftime('%Y-%m-%d')
    file_key = f"adzuna/{date_str}/raw_jobs.json"

    s3_client.put_object(
        Bucket=bucket_name,
        Key=file_key,
        Body=json.dumps(data, ensure_ascii=False, indent=2),
        ContentType='application/json'
    )

    return file_key


if __name__ == "__main__":
    extract_adzuna_jobs()
