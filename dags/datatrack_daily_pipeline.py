from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Importamos as funcoes de extracao dos plugins (Bronze Layer)
from adzuna_extractor import extract_adzuna_jobs
from gupy_extractor import extract_gupy_jobs
from jooble_extractor import extract_jooble_jobs
from remoteok_extractor import extract_remoteok_jobs

# Importamos as funcoes da Silver Layer
from silver.loader import load_all_sources
from silver.deduplicator import run as deduplicate
from silver.normalizer import run as normalize

# Importamos a entrega (E-mail Digest)
from email_sender import send_daily_digest

default_args = {
    'owner': 'thiago',
    'depends_on_past': False,
    'start_date': datetime(2026, 5, 15),
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

    adzuna_file   = ti.xcom_pull(task_ids='extract_adzuna')
    gupy_file     = ti.xcom_pull(task_ids='extract_gupy')
    jooble_file   = ti.xcom_pull(task_ids='extract_jooble')
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
        raise ValueError(
            f"ERRO: As seguintes fontes obrigatorias nao retornaram arquivo: "
            f"{', '.join(falhas)}. Validacao falhou."
        )

    print("Validacao Bronze concluida com SUCESSO:")
    print(f" - Adzuna: {adzuna_file}")
    print(f" - Gupy: {gupy_file}")
    print(f" - RemoteOK: {remoteok_file}")
    if jooble_file == "skipped_no_key":
        print(" - Jooble: [PULADO] Chave de API ausente.")
    else:
        print(f" - Jooble: {jooble_file}")


# =============================================================================
# Configuracao da DAG
# =============================================================================
with DAG(
    'datatrack_daily_pipeline',
    default_args=default_args,
    description='Pipeline diaria de extracao, transformacao e carga de vagas de dados',
    schedule_interval='50 5 * * *', # 05:50 AM todos os dias
    catchup=False,
    tags=['bronze', 'silver', 'gold', 'ingestion', 'transformation', 'dbt'],
) as dag:

    # ------------------------------------------------------------------
    # Bronze Layer: extracao paralela das 4 fontes
    # ------------------------------------------------------------------
    task_extract_adzuna = PythonOperator(
        task_id='extract_adzuna',
        python_callable=extract_adzuna_jobs,
    )

    task_extract_gupy = PythonOperator(
        task_id='extract_gupy',
        python_callable=extract_gupy_jobs,
    )

    task_extract_jooble = PythonOperator(
        task_id='extract_jooble',
        python_callable=extract_jooble_jobs,
    )

    task_extract_remoteok = PythonOperator(
        task_id='extract_remoteok',
        python_callable=extract_remoteok_jobs,
    )

    # Validacao: falha a DAG se alguma fonte obrigatoria nao entregou arquivo
    task_validate_bronze = PythonOperator(
        task_id='validate_bronze',
        python_callable=validate_bronze_layer,
        provide_context=True,
    )

    # ------------------------------------------------------------------
    # Silver Layer: carga, deduplicacao e normalizacao
    # As 3 tasks rodam em sequencia — cada uma depende da anterior
    # ------------------------------------------------------------------

    # Lê os JSON do MinIO e carrega em silver.raw_jobs (Supabase)
    task_silver_load = PythonOperator(
        task_id='silver_load_raw',
        python_callable=load_all_sources,
        provide_context=True,
    )

    # Detecta duplicatas entre fontes e consolida em silver.jobs
    task_silver_dedup = PythonOperator(
        task_id='silver_deduplicate',
        python_callable=deduplicate,
        provide_context=True,
    )

    # Classifica area, senioridade e extrai skills de cada vaga
    task_silver_normalize = PythonOperator(
        task_id='silver_normalize',
        python_callable=normalize,
        provide_context=True,
    )

    # ------------------------------------------------------------------
    # Gold Layer: executa dbt run + dbt test
    # Roda APENAS apos a normalizacao Silver estar completa.
    # O BashOperator usa o virtualenv Python 3.12 dedicado ao dbt,
    # montado no container via volume ./dbt:/opt/airflow/dbt
    # ------------------------------------------------------------------
    task_dbt_run = BashOperator(
        task_id='dbt_run',
        bash_command=(
            '/opt/airflow/dbt-env/bin/dbt run '
            '--project-dir /opt/airflow/dbt '
            '--profiles-dir /opt/airflow/dbt '
            '&& /opt/airflow/dbt-env/bin/dbt test '
            '--project-dir /opt/airflow/dbt '
            '--profiles-dir /opt/airflow/dbt'
        ),
    )

    # Envio do e-mail resumo diário (Fase 5)
    task_send_email = PythonOperator(
        task_id='send_email_digest',
        python_callable=send_daily_digest,
        provide_context=True,
    )

    # ------------------------------------------------------------------
    # Grafo de dependencias
    #
    # extract_adzuna  --+
    # extract_gupy     +--> validate_bronze --> silver_load_raw --> silver_deduplicate --> silver_normalize --> dbt_run --> send_email_digest
    # extract_jooble   |
    # extract_remoteok --+
    # ------------------------------------------------------------------
    [
        task_extract_adzuna,
        task_extract_gupy,
        task_extract_jooble,
        task_extract_remoteok,
    ] >> task_validate_bronze >> task_silver_load >> task_silver_dedup >> task_silver_normalize >> task_dbt_run >> task_send_email
