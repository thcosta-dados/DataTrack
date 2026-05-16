from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

# Importamos a função de extração que criamos na pasta plugins
from adzuna_extractor import extract_adzuna_jobs

default_args = {
    'owner': 'thiago',
    'depends_on_past': False,
    'start_date': datetime(2026, 5, 15), # Data no passado para que a DAG rode imediatamente ao ser ligada
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2, # Se der erro na API, ele tenta de novo
    'retry_delay': timedelta(minutes=5),
}

def validate_bronze_layer(**kwargs):
    """
    Verifica se o arquivo realmente foi salvo.
    Se o extrator falhar silenciosamente, essa task falha e avisa a gente.
    """
    ti = kwargs['ti']
    # 'xcom_pull' puxa o retorno (o caminho do arquivo) que a task anterior gerou
    file_key = ti.xcom_pull(task_ids='extract_adzuna')
    
    if not file_key:
        raise ValueError("ERRO: A task de extração não retornou o caminho do arquivo. Validação falhou.")
    
    print(f"Validação Bronze concluída com SUCESSO: Arquivo {file_key} verificado.")

# Configuração principal da nossa Automação (DAG)
with DAG(
    'datatrack_daily_pipeline',
    default_args=default_args,
    description='Pipeline diária de extração de vagas de dados',
    schedule_interval='0 7 * * *', # Executa todos os dias às 7h da manhã
    catchup=False,
    tags=['bronze', 'ingestion'],
) as dag:

    # Task 1: Nossa extração da Adzuna
    task_extract_adzuna = PythonOperator(
        task_id='extract_adzuna',
        python_callable=extract_adzuna_jobs,
    )

    # Task 2: Validação se os dados chegaram na Bronze
    task_validate_bronze = PythonOperator(
        task_id='validate_bronze',
        python_callable=validate_bronze_layer,
        provide_context=True,
    )

    # Ordem de execução: A setinha diz que a Extração vem ANTES da Validação
    task_extract_adzuna >> task_validate_bronze
