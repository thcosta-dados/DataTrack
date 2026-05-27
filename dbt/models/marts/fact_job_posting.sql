-- fact_job_posting.sql
-- Tabela fato central do star schema: uma linha por vaga unica.
-- Materializada como INCREMENTAL para que execucoes diarias processem
-- apenas as vagas novas, sem reprocessar o historico inteiro.
--
-- Estrategia incremental:
--   - unique_key: job_id (garante idempotencia — sem duplicatas mesmo se rodar duas vezes)
--   - Filtro: apenas registros com ingested_at mais recente que o maximo ja na tabela
--
-- Essa e a materialization correta para uma fact table que cresce diariamente.

{{
    config(
        materialized='incremental',
        unique_key='job_id',
        on_schema_change='fail'
    )
}}

with jobs as (
    select * from {{ ref('int_jobs_classified') }}
),

areas as (
    select * from {{ ref('dim_area') }}
),

seniorities as (
    select * from {{ ref('dim_seniority') }}
),

final as (
    select
        -- Chave primaria
        j.job_id,

        -- Chaves estrangeiras para as dimensoes
        j.company_id,
        j.location_id,

        -- Joins para pegar os IDs das dimensoes estaticas (area e seniority)
        -- Usamos LEFT JOIN para nao perder vagas cujo codigo nao resolve na dim
        a.area_code,
        s.seniority_code,

        -- Atributos da vaga
        j.job_title,
        j.job_url,
        j.posted_date,
        j.is_remote,
        j.is_hybrid,
        j.has_skills,

        -- Rastreabilidade: quais fontes geraram esta vaga
        j.source_ids,

        -- Data de ingestao (usada pelo filtro incremental)
        j.ingested_at

    from jobs j
    left join areas a
        on j.area = a.area_code
    left join seniorities s
        on j.seniority = s.seniority_code

    -- Filtro incremental: na primeira execucao processa tudo.
    -- Nas execucoes seguintes, so pega registros novos desde o ultimo run.
    {% if is_incremental() %}
        where j.ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}
)

select * from final
