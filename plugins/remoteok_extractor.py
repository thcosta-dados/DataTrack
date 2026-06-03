import os
import json
import requests
from datetime import datetime
from bronze_storage import upload_to_bronze

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
            jobs = []
            metadata = {}

            if isinstance(raw_data, list) and len(raw_data) > 0:
                metadata = raw_data[0]
                jobs = raw_data[1:]

            print(f"-> Sucesso! {len(jobs)} vagas totais recebidas no feed do RemoteOK.")

            final_data = {
                "source": "remoteok",
                "extracted_at": datetime.now().isoformat(),
                "terms": metadata,
                "total_results": len(jobs),
                "results": jobs
            }

            file_key = upload_to_bronze(final_data, "remoteok")
            print(f"Dados do RemoteOK salvos no MinIO: s3://datatrack-bronze/{file_key}")
            return file_key
        else:
            print(f"-> Erro ao chamar API do RemoteOK (Status {response.status_code}): {response.text}")
            return None

    except Exception as e:
        print(f"-> Falha ao conectar ou extrair da API do RemoteOK: {e}")
        return None


if __name__ == "__main__":
    extract_remoteok_jobs()
