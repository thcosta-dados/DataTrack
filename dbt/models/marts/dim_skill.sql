-- dim_skill.sql
-- Dimensao de skills: lista unica de skills extraidas de todas as vagas.
-- Derivada de int_jobs_with_skills (que ja explodiu o array em linhas).
-- Adiciona categorizacao de qual area de dados a skill pertence primariamente.

with skills_raw as (
    select distinct
        skill as skill_name
    from {{ ref('int_jobs_with_skills') }}
    where skill is not null
      and skill != ''
),

-- Geramos um ID unico por skill via surrogate key (hash do nome canonico)
skills_with_id as (
    select
        {{ dbt_utils.generate_surrogate_key(['skill_name']) }} as skill_id,
        skill_name,
        -- Normalizamos para lowercase para facilitar comparacoes futuras
        lower(skill_name) as skill_canonical,
        -- Categorizacao primaria por area de dados
        -- Baseada no dicionario de skills do projeto (referencia_main.md, secao 10)
        case
            when lower(skill_name) in ('python', 'sql', 'spark', 'airflow', 'dbt',
                                        'kafka', 'aws', 'gcp', 'azure', 'docker',
                                        'kubernetes', 'postgresql', 'redshift', 'bigquery',
                                        'snowflake', 'databricks', 'pyspark', 'prefect',
                                        's3', 'glue', 'lambda')
                then 'data_engineering'
            when lower(skill_name) in ('tensorflow', 'pytorch', 'scikit-learn', 'pandas',
                                        'numpy', 'mlflow', 'prophet', 'statsmodels',
                                        'jupyter', 'shap', 'xgboost', 'lightgbm', 'r')
                then 'data_science'
            when lower(skill_name) in ('power bi', 'tableau', 'looker', 'metabase',
                                        'google analytics', 'dax', 'excel', 'superset')
                then 'analytics_bi'
            when lower(skill_name) in ('kubeflow', 'sagemaker', 'bentoml',
                                        'tensorflow serving', 'ray')
                then 'ml_mlops'
            else 'cross_area'
        end as primary_category
    from skills_raw
)

select * from skills_with_id
