import os
import json
import requests
from datetime import datetime
from bronze_storage import upload_to_bronze

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
            "location": "Brazil",
            "page": "1"
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                jobs = data.get("jobs", [])
                print(f"  -> Sucesso! Encontradas {len(jobs)} vagas.")

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

    file_key = upload_to_bronze(final_data, "jooble")
    print(f"Dados do Jooble salvos no MinIO: s3://datatrack-bronze/{file_key}")
    return file_key


if __name__ == "__main__":
    extract_jooble_jobs()
