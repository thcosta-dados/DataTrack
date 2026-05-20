import os
import json
import requests
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

def extract_remoteok_jobs():
    print("Iniciando extracao do RemoteOK...")
    url = "https://remoteok.com/api"
    
    # Headers para evitar erro 403 (RemoteOK bloqueia requests vazias de python-requests)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            raw_data = response.json()
            
            # A API da RemoteOK retorna a primeira posicao como metadados/legal (legal/terms)
            # e os restantes sao as vagas reais.
            # Vamos separar para garantir que nao quebre no parse
            jobs = []
            metadata = {}
            
            if isinstance(raw_data, list) and len(raw_data) > 0:
                metadata = raw_data[0] # Contem termos de uso do RemoteOK
                jobs = raw_data[1:]    # Vagas reais
                
            print(f"-> Sucesso! {len(jobs)} vagas totais recebidas no feed do RemoteOK.")
            
            final_data = {
                "source": "remoteok",
                "extracted_at": datetime.now().isoformat(),
                "terms": metadata,
                "total_results": len(jobs),
                "results": jobs
            }
            
            # Faz upload do feed completo para a Bronze (Medallion pura)
            file_key = _upload_to_minio(final_data)
            print(f"Dados do RemoteOK salvos no MinIO: s3://datatrack-bronze/{file_key}")
            return file_key
        else:
            print(f"-> Erro ao chamar API do RemoteOK (Status {response.status_code}): {response.text}")
            return None
            
    except Exception as e:
        print(f"-> Falha ao conectar ou extrair da API do RemoteOK: {e}")
        return None


def _upload_to_minio(data):
    """
    Conecta ao MinIO e salva o JSON na camada Bronze,
    particionado por data (remoteok/YYYY-MM-DD/raw_jobs.json).
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
    file_key = f"remoteok/{date_str}/raw_jobs.json"

    s3_client.put_object(
        Bucket=bucket_name,
        Key=file_key,
        Body=json.dumps(data, ensure_ascii=False, indent=2),
        ContentType='application/json'
    )

    return file_key

if __name__ == "__main__":
    extract_remoteok_jobs()
