-- dim_location.sql
-- Dimensao de localidades: padroniza o campo de localizacao para analise geografica.
-- Como a silver armazena strings livres (ex: 'Sao Paulo', 'Remote', 'Brasil'),
-- fazemos uma normalizacao basica para separar localidades remotas das presenciais.

with locations as (
    select * from {{ ref('stg_locations') }}
),

final as (
    select
        location_id,
        location_name,
        is_remote,
        -- Inferencia de pais: padrao Brasil para vagas sem indicacao explicita
        -- Vagas remotas internacionais geralmente tem 'Remote' ou 'Worldwide' no nome
        case
            when is_remote = true then 'Remote'
            when lower(location_name) like '%brasil%'
              or lower(location_name) like '%brazil%'
              or lower(location_name) like '%sp%'
              or lower(location_name) like '%rio%'
              or lower(location_name) like '%sao paulo%'
              or lower(location_name) like '%remote%' then 'BR'
            else 'BR'
        end as country_code
    from locations
)

select * from final
