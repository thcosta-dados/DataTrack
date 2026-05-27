-- stg_locations.sql
-- Leitura da silver.locations com padronizacao de campos.
-- Armazena localidades unicas ja normalizadas pelo processo Silver.

with source as (
    select * from {{ source('silver', 'locations') }}
),

renamed as (
    select
        id                                      as location_id,
        -- 'raw' e a string bruta de localizacao vinda da fonte original
        coalesce(raw, 'Nao informado')          as location_name,
        -- Campos opcionais que podem estar preenchidos ou nulos
        city,
        state,
        coalesce(country, 'BR')                 as country,
        -- Indica se e uma posicao 100% remota
        coalesce(is_remote, false)              as is_remote
    from source
)

select * from renamed
