import os
import json
import requests
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

def extract_adzuna_jobs():
    app_id = os.getenv('ADZUNA_APP_ID')
    app_key = os.getenv('ADZUNA_APP_KEY')
    
    if not app_id or not app_key:
        raise ValueError("Credenciais do Adzuna não encontradas.")
    
    # Busca simplificada em formato de lista 
    # (a API do Adzuna não lida bem com queries booleanas muito longas)
    search_terms = [
        "data engineering", "engenharia de dados",
        "data analytics", "análise de dados",
        "data science", "ciência de dados",
        "business intelligence", "machine learning"
    ]
    
    country = 'br'
    page = 1
    
    all_jobs = []
    
    print(f"Iniciando extração do Adzuna para TODA a área de dados...")
    
    for term in search_terms:
        print(f"Buscando vagas para: '{term}'...")
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
        params = {
            'app_id': app_id,
            'app_key': app_key,
            'results_per_page': 50,
            'what': term,
            'content-type': 'application/json'
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            jobs = data.get('results', [])
            all_jobs.extend(jobs)
            print(f"  -> Encontradas {len(jobs)} vagas nesta página.")
        else:
            print(f"  -> Erro ao buscar '{term}': HTTP {response.status_code}")
            
    print(f"\nTotal bruto extraído: {len(all_jobs)} vagas.")
    print(f"(Atenção: existem duplicatas, mas o nosso algoritmo da Camada Silver cuidará disso!)")
    
    # Criar um JSON único com todos os resultados combinados
    final_data = {
        "source": "adzuna",
        "extracted_at": datetime.now().isoformat(),
        "total_results": len(all_jobs),
        "results": all_jobs
    }
    
    # Configuração da nossa Despensa (MinIO)
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
    
    # Criar a pasta principal (bucket) se não existir
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError:
        s3_client.create_bucket(Bucket=bucket_name)
        
    # Salvar o arquivo JSON no formato Bronze
    date_str = datetime.now().strftime('%Y-%m-%d')
    file_key = f"adzuna/{date_str}/raw_jobs.json"
    
    s3_client.put_object(
        Bucket=bucket_name,
        Key=file_key,
        Body=json.dumps(final_data, ensure_ascii=False, indent=2),
        ContentType='application/json'
    )
    
    print(f"Sucesso! Dados salvos no MinIO: s3://{bucket_name}/{file_key}")
    return file_key

if __name__ == "__main__":
    extract_adzuna_jobs()
