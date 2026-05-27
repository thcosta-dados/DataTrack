-- int_company_size.sql
-- Calcula o porte de cada empresa com base no volume de vagas publicadas
-- nos ultimos 30 dias. E um proxy empirico que nao depende de nenhuma
-- API externa ou dado cadastral.
--
-- Criterio (definido na documentacao do projeto):
--   >= 10 vagas -> grande
--    3-9 vagas  -> media
--    1-2 vagas  -> pequena
--
-- Limitacao documentada: empresas em hiper-crescimento podem ser classificadas
-- como 'grande' mesmo sendo startups pequenas. Esse trade-off e consciente.

with posting_volume as (
    select
        company_id,
        count(*) as total_postings_30d
    from {{ ref('stg_jobs') }}
    -- Janela de 30 dias a partir da data de publicacao da vaga
    where posted_date >= current_date - interval '30 days'
    group by company_id
)

select
    company_id,
    total_postings_30d,
    case
        when total_postings_30d >= 10 then 'grande'
        when total_postings_30d >= 3  then 'media'
        else                               'pequena'
    end as company_size
from posting_volume
