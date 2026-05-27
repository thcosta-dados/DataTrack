-- int_jobs_classified.sql
-- Consolida os campos de classificacao das vagas para alimentar a tabela fato.
-- Aplica fallback explicito para area e senioridade nulas (garantia de qualidade).
-- Esta camada centraliza a logica de negocio antes dos marts.

with jobs as (
    select * from {{ ref('stg_jobs') }}
),

classified as (
    select
        job_id,
        job_sk,
        company_id,
        location_id,
        job_title,
        job_url,
        posted_date,
        is_remote,
        is_hybrid,
        source_ids,
        ingested_at,

        -- Fallback explicito: se area ou seniority chegarem nulos (registro antigo
        -- antes do normalizer), classificamos como 'unknown' para nao quebrar joins
        coalesce(nullif(trim(job_area), ''), 'unknown')      as area,
        coalesce(nullif(trim(job_seniority), ''), 'unknown') as seniority,

        -- Marca se a vaga tem ao menos uma skill extraida (util para qualidade)
        case
            when array_length(skills_array, 1) > 0 then true
            else false
        end as has_skills

    from jobs
)

select * from classified
where area not in ('non_tech', 'non_data')
