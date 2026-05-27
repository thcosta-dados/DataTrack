-- dim_company.sql
-- Dimensao de empresas: junta stg_companies com o porte calculado em int_company_size.
-- Resultado: uma linha por empresa com nome e classificacao de porte.

with companies as (
    select * from {{ ref('stg_companies') }}
),

company_size as (
    select * from {{ ref('int_company_size') }}
),

final as (
    select
        c.company_id,
        c.company_name,
        -- LEFT JOIN: empresas sem vagas nos ultimos 30 dias recebem 'pequena'
        coalesce(cs.company_size, 'pequena') as company_size,
        coalesce(cs.total_postings_30d, 0)   as postings_last_30d
    from companies c
    left join company_size cs
        on c.company_id = cs.company_id
)

select * from final
