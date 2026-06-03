import os
import json
import time
import base64
import urllib.parse
from datetime import datetime
from playwright.sync_api import sync_playwright
from bronze_storage import upload_to_bronze

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
        browser = p.chromium.launch(headless=True)
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

    final_data = {
        "source": "gupy",
        "extracted_at": datetime.now().isoformat(),
        "total_results": len(all_jobs),
        "results": all_jobs
    }

    file_key = upload_to_bronze(final_data, "gupy")
    print(f"Sucesso! Dados da Gupy salvos no MinIO: s3://datatrack-bronze/{file_key}")
    return file_key


def _scrape_gupy_term(page, term):
    search_url = f"https://portal.gupy.io/job-search/term={term.replace(' ', '%20')}"
    page.goto(search_url, wait_until="networkidle", timeout=60000)

    # Esperamos um pouco a mais para garantir a renderizacao dos cards via React
    page.wait_for_timeout(3000)

    # Scrola a pagina para carregar mais resultados (lazy loading)
    for _ in range(3):
        page.keyboard.press("End")
        page.wait_for_timeout(1000)

    job_cards = page.query_selector_all("a[href*='.gupy.io/job/']")

    collected = []

    for card in job_cards[:MAX_JOBS_PER_TERM]:
        try:
            full_text = card.inner_text()
            url = card.get_attribute("href")

            if url and url.startswith("/"):
                url = f"https://portal.gupy.io{url}"

            lines = [line.strip() for line in full_text.split('\n') if line.strip()]

            job_data = {
                "url": url,
                "raw_text": full_text,
                "lines": lines
            }

            if len(lines) >= 3:
                job_data["company"] = lines[0]
                job_data["title"] = lines[1]
                job_data["location"] = lines[2]

            # Extrai source_id decodificando o token da URL da Gupy
            source_id = None
            if url:
                parsed_url = urllib.parse.urlparse(url)
                path_parts = parsed_url.path.strip("/").split("/")
                if "job" in path_parts:
                    idx = path_parts.index("job")
                    if idx + 1 < len(path_parts):
                        token = path_parts[idx + 1]
                        try:
                            padded_token = token + "=" * ((4 - len(token) % 4) % 4)
                            decoded_bytes = base64.b64decode(padded_token)
                            decoded_dict = json.loads(decoded_bytes.decode("utf-8"))
                            job_id = decoded_dict.get("jobId")
                            if job_id:
                                source_id = str(job_id)
                        except Exception:
                            source_id = token

            location = job_data.get("location", "")
            is_remote = False
            if location:
                is_remote = any(x in location.lower() for x in ["remoto", "home office", "remote"])

            job_data["source_id"] = source_id
            job_data["is_remote"] = is_remote
            job_data["posted_at"] = datetime.now().isoformat()

            collected.append(job_data)
        except Exception as e:
            print(f"    -> Aviso: Falha ao fazer parse de um card: {e}")

    print(f"  -> Coletadas {len(collected)} vagas na pagina atual.")
    return collected


if __name__ == "__main__":
    extract_gupy_jobs()
