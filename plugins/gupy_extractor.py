import os
import json
import time
import base64
import urllib.parse
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from playwright.sync_api import sync_playwright

# Configuracoes de extracao
MAX_JOBS_PER_TERM = 50  # Limite para nao sobrecarregar o scraper
SEARCH_TERMS = [
    "data engineering", "engenharia de dados",
    "data analytics", "analise de dados",
    "data science", "ciencia de dados",
    "business intelligence", "machine learning"
]

def extract_gupy_jobs():
    print("Iniciando extracao do Gupy via Playwright...")
    all_jobs = []

    with sync_playwright() as p:
        # Iniciamos o Chromium no modo headless (sem interface grafica visivel)
        browser = p.chromium.launch(headless=True)
        # Contexto com configuracoes que imitam um usuario real para evitar bloqueios
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for term in SEARCH_TERMS:
            print(f"\nBuscando vagas para: '{term}'...")
            try:
                term_jobs = _scrape_gupy_term(page, term)
                all_jobs.extend(term_jobs)
            except Exception as e:
                print(f"  -> Erro ao raspar termo '{term}': {e}")
        
        browser.close()

    print(f"\nTotal bruto extraido da Gupy: {len(all_jobs)} vagas.")
    
    # Monta o JSON final
    final_data = {
        "source": "gupy",
        "extracted_at": datetime.now().isoformat(),
        "total_results": len(all_jobs),
        "results": all_jobs
    }

    # Salva no MinIO (Bronze Layer)
    file_key = _upload_to_minio(final_data)

    print(f"Sucesso! Dados da Gupy salvos no MinIO: s3://datatrack-bronze/{file_key}")
    return file_key


def _scrape_gupy_term(page, term):
    # Formata o termo de busca para a URL
    search_url = f"https://portal.gupy.io/job-search/term={term.replace(' ', '%20')}"
    page.goto(search_url, wait_until="networkidle", timeout=60000)

    # Esperamos um pouco a mais para garantir a renderizacao dos cards via React
    page.wait_for_timeout(3000)

    # Scrola a pagina para carregar mais resultados (lazy loading)
    # Faremos um scroll para tentar capturar os 50 primeiros resultados
    for _ in range(3):
        page.keyboard.press("End")
        page.wait_for_timeout(1000)

    # Buscamos todos os links de vagas (geralmente sao tags 'a' que levam para o subdominio da empresa)
    # A estrutura atual da Gupy costuma usar ul/li para a lista, onde o a tag contem os dados
    job_cards = page.query_selector_all("a[href*='.gupy.io/job/']")
    
    collected = []
    
    for card in job_cards[:MAX_JOBS_PER_TERM]:
        try:
            # Extraimos os textos de dentro do card
            # A Gupy muda muito as classes css, entao usamos logica defensiva
            full_text = card.inner_text()
            url = card.get_attribute("href")
            
            # Se a url for relativa, montamos a url completa
            if url and url.startswith("/"):
                url = f"https://portal.gupy.io{url}"
            
            # Quebramos o texto do card (que normalmente tem Nome da vaga, Empresa, Local)
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            # Definimos um dicionario basico. A quebra exata dependera do layout atual.
            # Capturamos o payload cru para depois processarmos (Bronze layer armazena bruto)
            job_data = {
                "url": url,
                "raw_text": full_text,
                "lines": lines
            }
            
            # Tentativa de parsing basico se tivermos pelo menos 3 linhas
            if len(lines) >= 3:
                job_data["company"] = lines[0]
                job_data["title"] = lines[1]
                job_data["location"] = lines[2]
            
            # Extraímos o source_id decodificando o token da URL da Gupy
            source_id = None
            if url:
                parsed_url = urllib.parse.urlparse(url)
                path_parts = parsed_url.path.strip("/").split("/")
                if "job" in path_parts:
                    idx = path_parts.index("job")
                    if idx + 1 < len(path_parts):
                        token = path_parts[idx + 1]
                        try:
                            # Adiciona padding se necessário para decodificar base64
                            padded_token = token + "=" * ((4 - len(token) % 4) % 4)
                            decoded_bytes = base64.b64decode(padded_token)
                            decoded_dict = json.loads(decoded_bytes.decode("utf-8"))
                            job_id = decoded_dict.get("jobId")
                            if job_id:
                                source_id = str(job_id)
                        except Exception:
                            source_id = token
            
            # Determinamos se a vaga é remota baseado na localização
            location = job_data.get("location", "")
            is_remote = False
            if location:
                is_remote = any(x in location.lower() for x in ["remoto", "home office", "remote"])
            
            job_data["source_id"] = source_id
            job_data["is_remote"] = is_remote
            job_data["posted_at"] = datetime.now().isoformat()
            
            collected.append(job_data)
        except Exception as e:
            # Logamos mas continuamos se um card falhar
            print(f"    -> Aviso: Falha ao fazer parse de um card: {e}")

    print(f"  -> Coletadas {len(collected)} vagas na pagina atual.")
    return collected


def _upload_to_minio(data):
    """
    Conecta ao MinIO e salva o JSON na camada Bronze,
    particionado por data (gupy/YYYY-MM-DD/raw_jobs.json).
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

    # Particionamento por data para a Gupy
    date_str = datetime.now().strftime('%Y-%m-%d')
    file_key = f"gupy/{date_str}/raw_jobs.json"

    s3_client.put_object(
        Bucket=bucket_name,
        Key=file_key,
        Body=json.dumps(data, ensure_ascii=False, indent=2),
        ContentType='application/json'
    )

    return file_key

if __name__ == "__main__":
    extract_gupy_jobs()
