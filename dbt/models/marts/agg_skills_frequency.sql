-- agg_skills_frequency.sql
-- Snapshot diario de frequencia de skills por area de dados.
-- Responde perguntas como: "Python cresceu ou caiu em vagas de DE nos ultimos 30 dias?"
-- Este modelo alimenta o grafico de tendencias de skills no dashboard Streamlit.
--
-- Logica:
--   Para cada (skill, area, data_referencia), contamos quantas vagas postadas
--   naquele dia demandavam aquela skill naquela area.

with skills as (
    select * from {{ ref('int_jobs_with_skills') }}
),

aggregated as (
    select
        skill,
        job_area,
        posted_date                      as reference_date,
        count(distinct job_id)           as job_count,
        -- Data em que o modelo rodou (util para rastrear historico de snapshots)
        current_date                     as snapshot_date
    from skills
    -- Limita a janela de analise a 90 dias para manter a tabela enxuta
    where posted_date >= current_date - interval '90 days'
    group by skill, job_area, posted_date
)

select * from aggregated
