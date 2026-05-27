-- stg_jobs.sql
-- Leitura direta da silver.jobs com padronizacao de nomenclatura para a Gold.
-- Responsabilidade: renomear campos, castings seguros e adicionar surrogate_key.
-- Nenhuma logica de negocio aqui — so traducao de nomenclatura.

with source as (
    select * from {{ source('silver', 'jobs') }}
),

renamed as (
    select
        -- Chave primaria
        job_id,

        -- Surrogate key gerada via hash deterministico (titulo + empresa + local)
        -- Util para joins futuros sem depender de UUID diretamente
        {{ dbt_utils.generate_surrogate_key(['job_id']) }} as job_sk,

        -- Referencias as dimensoes da silver
        company_id,
        location_id,

        -- Dados da vaga
        title                               as job_title,
        area                                as job_area,
        seniority                           as job_seniority,
        skills                              as skills_array,
        url                                 as job_url,
        posted_at                           as posted_date,

        -- Modalidade
        coalesce(is_remote, false)          as is_remote,
        coalesce(is_hybrid, false)          as is_hybrid,

        -- Array de IDs de fontes (Adzuna, Gupy, Jooble, RemoteOK)
        source_ids,

        -- Auditoria
        created_at                          as ingested_at

    from source
    -- Filtra registros sem titulo (invalidos para analise)
    where title is not null
)

select * from renamed
