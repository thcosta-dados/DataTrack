-- stg_companies.sql
-- Leitura da silver.companies com padronizacao de campos.
-- Esta tabela e a dimensao de empresas unicas identificadas no processo de deduplicacao.

with source as (
    select * from {{ source('silver', 'companies') }}
),

renamed as (
    select
        id                              as company_id,
        -- Garante que o nome nunca chegue nulo na Gold
        coalesce(name, 'Empresa nao informada') as company_name
    from source
)

select * from renamed
