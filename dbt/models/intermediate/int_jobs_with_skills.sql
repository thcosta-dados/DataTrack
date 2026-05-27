-- int_jobs_with_skills.sql
-- Explode o array de skills de cada vaga em linhas individuais.
--
-- Por que isso e necessario?
-- O campo skills_array em stg_jobs e um TEXT[] (array PostgreSQL).
-- Para responder perguntas como "qual skill aparece mais em vagas de DE?",
-- precisamos de uma linha por (job_id, skill) — nao um array por vaga.
-- Essa e a tecnica padrao de normalizacao de arrays em SQL analitico.

with jobs as (
    select * from {{ ref('stg_jobs') }}
),

-- unnest() e a funcao nativa do PostgreSQL para explodir um array em linhas.
-- Para cada vaga com N skills, geramos N linhas identicas exceto pela skill.
exploded as (
    select
        job_id,
        company_id,
        location_id,
        job_area,
        job_seniority,
        posted_date,
        is_remote,
        is_hybrid,
        -- trim() remove espacos extras que podem vir do array apos a extracao
        trim(skill) as skill
    from jobs,
    -- A virgula aqui e a sintaxe LATERAL JOIN implicita do PostgreSQL
    unnest(skills_array) as skill
    -- Filtra skills vazias ou nulas que possam ter escapado do normalizer
    where trim(skill) is not null
      and trim(skill) != ''
)

select * from exploded
