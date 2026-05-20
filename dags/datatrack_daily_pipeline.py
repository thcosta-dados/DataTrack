from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

# Importamos as funcoes de extracao dos plugins
from adzuna_extractor import extract_adzuna_jobs
from gupy_extractor import extract_gupy_jobs
from jooble_extractor import extract_jooble_jobs
from remoteok_extractor import extract_remoteok_jobs

default_args = {
    'owner': 'thiago',
    'depends_on_past': False,
    'start_date': datetime(2026, 5, 15), # Rodar retroativo localmente
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def validate_bronze_layer(**kwargs):
    """
    Valida a presenca dos arquivos na Bronze (MinIO).
    Adzuna, Gupy e RemoteOK sao obrigatorios.
    Jooble so e obrigatorio se a API Key estiver configurada.
    """
    ti = kwargs['ti']
    
    adzuna_file = ti.xcom_pull(task_ids='extract_adzuna')
    gupy_file = ti.xcom_pull(task_ids='extract_gupy')
    jooble_file = ti.xcom_pull(task_ids='extract_jooble')
    remoteok_file = ti.xcom_pull(task_ids='extract_remoteok')
    
    falhas = []
    if not adzuna_file:
        falhas.append("Adzuna")
    if not gupy_file:
        falhas.append("Gupy")
    if not remoteok_file:
        falhas.append("RemoteOK")
        
    # Se o Jooble falhar e nao for o caso de "skipped_no_key", consideramos falha
    if jooble_file != "skipped_no_key" and not jooble_file:
        falhas.append("Jooble")

    if falhas:
        raise ValueError(f"ERRO: As seguintes fontes obrigatorias nao retornaram arquivo: {', '.join(falhas)}. Validacao falhou.")
    
    print("Validacao Bronze concluida com SUCESSO:")
    print(f" - Adzuna: {adzuna_file}")
    print(f" - Gupy: {gupy_file}")
    print(f" - RemoteOK: {remoteok_file}")
    if jooble_file == "skipped_no_key":
        print(" - Jooble: [PULADO] Chave de API ausente.")
    else:
        print(f" - Jooble: {jooble_file}")

# Configuração da DAG
with DAG(
    'datatrack_daily_pipeline',
    default_args=default_args,
    description='Pipeline diária de extração de vagas de dados de múltiplas fontes',
    schedule_interval='0 7 * * *',
    catchup=False,
    tags=['bronze', 'ingestion'],
) as dag:

    # Task 1: Ingestao Adzuna
    task_extract_adzuna = PythonOperator(
        task_id='extract_adzuna',
        python_callable=extract_adzuna_jobs,
    )

    # Task 2: Ingestao Gupy (Playwright)
    task_extract_gupy = PythonOperator(
        task_id='extract_gupy',
        python_callable=extract_gupy_jobs,
    )

    # Task 3: Ingestao Jooble
    task_extract_jooble = PythonOperator(
        task_id='extract_jooble',
        python_callable=extract_jooble_jobs,
    )

    # Task 4: Ingestao RemoteOK
    task_extract_remoteok = PythonOperator(
        task_id='extract_remoteok',
        python_callable=extract_remoteok_jobs,
    )

    # Task 5: Validacao Bronze
    task_validate_bronze = PythonOperator(
        task_id='validate_bronze',
        python_callable=validate_bronze_layer,
        provide_context=True,
    )

    # Execucao paralela de todos os extratores
    [
        task_extract_adzuna,
        task_extract_gupy,
        task_extract_jooble,
        task_extract_remoteok
    ] >> task_validate_bronze
