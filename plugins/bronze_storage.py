"""
plugins/bronze_storage.py
--------------------------
Modulo compartilhado para upload de dados brutos na Bronze Layer (MinIO/S3).

Todas as fontes de extracao usam este modulo em vez de cada uma ter sua
propria copia da mesma funcao _upload_to_minio. Centralizar elimina
duplicacao e garante que mudancas (ex: troca de bucket, endpoint)
se propaguem para todos os extractors de uma vez.
"""
import os
import json
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

MINIO_ENDPOINT = "http://minio:9000"
BRONZE_BUCKET = "datatrack-bronze"


def upload_to_bronze(data: dict, source_name: str) -> str:
    """
    Conecta ao MinIO e salva o JSON na camada Bronze,
    particionado por fonte e data: {source}/{YYYY-MM-DD}/raw_jobs.json

    Retorna a file_key (path completo dentro do bucket).
    """
    minio_user = os.getenv("MINIO_ROOT_USER", "admin")
    minio_password = os.getenv("MINIO_ROOT_PASSWORD", "adminpassword")

    s3_client = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=minio_user,
        aws_secret_access_key=minio_password,
        region_name="us-east-1",
    )

    # Cria o bucket se nao existir (idempotente)
    try:
        s3_client.head_bucket(Bucket=BRONZE_BUCKET)
    except ClientError:
        s3_client.create_bucket(Bucket=BRONZE_BUCKET)

    date_str = datetime.now().strftime("%Y-%m-%d")
    file_key = f"{source_name}/{date_str}/raw_jobs.json"

    s3_client.put_object(
        Bucket=BRONZE_BUCKET,
        Key=file_key,
        Body=json.dumps(data, ensure_ascii=False, indent=2),
        ContentType="application/json",
    )

    return file_key
