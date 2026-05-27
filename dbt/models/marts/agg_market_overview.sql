-- agg_market_overview.sql
-- Visao consolidada do mercado de dados — alimenta a pagina "Visao Geral" do dashboard.
-- Contem metricas agregadas pre-calculadas para evitar queries pesadas em tempo real.
--
-- Metricas geradas:
--   - Total de vagas ativas por area
--   - Distribuicao por senioridade dentro de cada area
--   - Proporcao de vagas remotas por area
--   - Top skills por area (top 10)

with jobs as (
    select * from {{ ref('fact_job_posting') }}
),

skills as (
    select * from {{ ref('int_jobs_with_skills') }}
),

-- Metricas por area e senioridade
area_seniority_metrics as (
    select
        area_code,
        seniority_code,
        count(*)                                           as total_jobs,
        round(
            100.0 * sum(case when is_remote then 1 else 0 end)
            / nullif(count(*), 0),
            1
        )                                                  as pct_remote
    from jobs
    -- Janela de 30 dias para a visao geral (dados recentes)
    where posted_date >= current_date - interval '30 days'
    group by area_code, seniority_code
),

-- Top 10 skills por area nos ultimos 30 dias
top_skills_per_area as (
    select
        job_area,
        skill,
        count(distinct skills.job_id)                     as skill_count,
        -- rank() para selecionar as top 10 por area
        rank() over (
            partition by job_area
            order by count(distinct skills.job_id) desc
        )                                                  as skill_rank
    from skills
    -- JOIN com fact para filtrar por data
    inner join jobs
        on skills.job_id = jobs.job_id
    where jobs.posted_date >= current_date - interval '30 days'
    group by job_area, skill
),

final_overview as (
    select
        m.area_code,
        m.seniority_code,
        m.total_jobs,
        m.pct_remote,
        current_date as reference_date
    from area_seniority_metrics m
)

select * from final_overview
