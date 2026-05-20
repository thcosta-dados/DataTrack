import os
import json
import requests
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# Lista padrao de termos (8 termos cobrindo a area de dados)
SEARCH_TERMS = [
    "data engineering", "engenharia de dados",
    "data analytics", "analise de dados",
    "data science", "ciencia de dados",
    "business intelligence", "machine learning"
]

def extract_jooble_jobs():
    api_key = os.getenv("JOOBLE_API_KEY", "").strip()
    
    # Tratamento defensivo: Se nao houver chave, pulamos graciosamente sem quebrar a DAG
    if not api_key:
        print("\n[AVISO] JOOBLE_API_KEY nao foi configurada no .env.")
        print("-> Pulando a extracao do Jooble graciosamente para nao travar o pipeline.")
        return "skipped_no_key"

    print(f"Iniciando extracao do Jooble via API...")
    # URL padrao internacional da API do Jooble (nao bloqueada por Cloudflare)
    url = f"https://jooble.org/api/{api_key}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    all_jobs = []
    
    for term in SEARCH_TERMS:
        print(f"Buscando vagas no Jooble para: '{term}'...")
        payload = {
            "keywords": term,
            "location": "Brazil", # Deve ser em Ingles para a API global funcionar
            "page": "1" # Buscamos a primeira pagina de resultados de cada termo
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("jobs", [])
                print(f"  -> Sucesso! Encontradas {len(jobs)} vagas.")
                
                # Adiciona metadados sobre qual termo gerou a vaga
                for job in jobs:
                    job["search_term"] = term
                
                all_jobs.extend(jobs)
            else:
                print(f"  -> Erro na API do Jooble (Status {response.status_code}): {response.text}")
                
        except Exception as e:
            print(f"  -> Falha ao conectar na API do Jooble para '{term}': {e}")
            
    print(f"\nTotal bruto extraido do Jooble: {len(all_jobs)} vagas.")
    
    final_data = {
        "source": "jooble",
        "extracted_at": datetime.now().isoformat(),
        "total_results": len(all_jobs),
        "results": all_jobs
    }
    
    # Salva no MinIO (Bronze Layer)
    file_key = _upload_to_minio(final_data)
    print(f"Dados do Jooble salvos no MinIO: s3://datatrack-bronze/{file_key}")
    return file_key


def _upload_to_minio(data):
    """
    Conecta ao MinIO e salva o JSON na camada Bronze,
    particionado por data (jooble/YYYY-MM-DD/raw_jobs.json).
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

    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError:
        s3_client.create_bucket(Bucket=bucket_name)

    date_str = datetime.now().strftime('%Y-%m-%d')
    file_key = f"jooble/{date_str}/raw_jobs.json"

    s3_client.put_object(
        Bucket=bucket_name,
        Key=file_key,
        Body=json.dumps(data, ensure_ascii=False, indent=2),
        ContentType='application/json'
    )

    return file_key

if __name__ == "__main__":
    # Teste de execucao direta
    extract_jooble_jobs()
