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
        case
            -- United Kingdom / Reino Unido
            when lower(location_name) like '%united kingdom%'
              or lower(location_name) like '%uk%'
              or lower(location_name) like '%london%'
              or lower(location_name) like '%england%' then 'GB'
            -- Canada
            when lower(location_name) like '%canada%'
              or lower(location_name) like '%ontario%'
              or lower(location_name) like '%toronto%'
              or lower(location_name) like '%vancouver%' then 'CA'
            -- Chile
            when lower(location_name) like '%chile%'
              or lower(location_name) like '%santiago%' then 'CL'
            -- USA / Estados Unidos
            when lower(location_name) like '%usa%'
              or lower(location_name) like '%united states%'
              or lower(location_name) like '%us%'
              or lower(location_name) like '%new york%'
              or lower(location_name) like '%california%' then 'US'
            -- Brasil
            when lower(location_name) like '%brasil%'
              or lower(location_name) like '%brazil%'
              or lower(location_name) like '%sp%'
              or lower(location_name) like '%rj%'
              or lower(location_name) like '%mg%'
              or lower(location_name) like '%rs%'
              or lower(location_name) like '%sc%'
              or lower(location_name) like '%pr%'
              or lower(location_name) like '%ba%'
              or lower(location_name) like '%ce%'
              or lower(location_name) like '%pe%'
              or lower(location_name) like '%go%'
              or lower(location_name) like '%sao paulo%'
              or lower(location_name) like '%rio de janeiro%'
              or lower(location_name) like '%belo horizonte%'
              or lower(location_name) like '%porto alegre%'
              or lower(location_name) like '%curitiba%'
              or lower(location_name) like '%salvador%'
              or lower(location_name) like '%florianopolis%'
              or lower(location_name) like '%fortaleza%'
              or lower(location_name) like '%recife%'
              or lower(location_name) like '%alphaville%'
              or lower(location_name) like '%barueri%'
              or lower(location_name) like '%campinas%'
              or lower(location_name) like '%nao informado%'
              or lower(location_name) like '%desconhecido%' then 'BR'
            -- Se for "remote", "worldwide" ou "anywhere" sem país explícito
            when lower(location_name) like '%remote%'
              or lower(location_name) like '%worldwide%'
              or lower(location_name) like '%anywhere%' then 'Global'
            -- Padrão como Brasil se não cair em nenhum outro
            else 'BR'
        end as country_code
    from locations
)

select
    location_id,
    location_name,
    is_remote,
    country_code,
    case
        when country_code = 'BR' then 'Brasil'
        when country_code = 'US' then 'Estados Unidos'
        when country_code = 'CA' then 'Canadá'
        when country_code = 'CL' then 'Chile'
        when country_code = 'GB' then 'Reino Unido'
        else 'Global/Não Informado'
    end as country_name
from final

