-- =============================================================================
-- DataTrack — Schema da Camada Silver
-- Execute este arquivo no SQL Editor do Supabase (ou via psql)
-- =============================================================================

-- Cria o schema dedicado para a Silver Layer
CREATE SCHEMA IF NOT EXISTS silver;

-- =============================================================================
-- Tabela intermediaria: todos os registros brutos normalizados, antes da dedup
-- Cada linha = 1 vaga de 1 fonte especifica, sem qualquer agrupamento
-- =============================================================================
CREATE TABLE IF NOT EXISTS silver.raw_jobs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source      VARCHAR(30)  NOT NULL,   -- 'adzuna', 'jooble', 'remoteok', 'gupy'
    source_id   VARCHAR(255),            -- ID original da vaga na plataforma fonte
    title       TEXT,
    company     TEXT,
    location    TEXT,
    description TEXT,
    url         TEXT,
    posted_at   DATE,
    is_remote   BOOLEAN DEFAULT FALSE,
    payload     JSONB,                   -- registro original completo (auditoria)
    ingested_at TIMESTAMP DEFAULT NOW()
);

-- Indice para evitar reprocessamento: source + source_id sao unicos por dia
CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_jobs_source_id
    ON silver.raw_jobs(source, source_id)
    WHERE source_id IS NOT NULL;

-- =============================================================================
-- Tabela de empresas normalizadas
-- =============================================================================
CREATE TABLE IF NOT EXISTS silver.companies (
    id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL
);

-- =============================================================================
-- Tabela de localizacoes normalizadas
-- =============================================================================
CREATE TABLE IF NOT EXISTS silver.locations (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw       TEXT UNIQUE NOT NULL, -- texto original como veio da fonte
    city      TEXT,
    state     VARCHAR(2),
    country   VARCHAR(5) DEFAULT 'BR',
    is_remote BOOLEAN DEFAULT FALSE
);

-- =============================================================================
-- Tabela principal: vagas unicas apos deduplicacao
-- Cada linha = 1 vaga real no mercado (pode ter vindo de N fontes)
-- =============================================================================
CREATE TABLE IF NOT EXISTS silver.jobs (
    job_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_ids  TEXT[],                                -- IDs de todas as fontes que mapearam para esta vaga
    dedup_hash  VARCHAR(64) UNIQUE,                    -- SHA256 da identidade normalizada da vaga
    title       TEXT,
    company_id  UUID REFERENCES silver.companies(id),
    location_id UUID REFERENCES silver.locations(id),
    area        VARCHAR(50),    -- 'data_engineering', 'data_science', 'data_analytics', 'ml_mlops', 'bi'
    seniority   VARCHAR(30),    -- 'estagio', 'junior', 'pleno', 'senior', 'lead'
    skills      TEXT[],         -- skills extraidas da descricao (ex: ['Python', 'SQL', 'Airflow'])
    url         TEXT,
    posted_at   DATE,
    is_remote   BOOLEAN DEFAULT FALSE,
    is_hybrid   BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Indices para as queries mais frequentes no dashboard
CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_dedup_hash  ON silver.jobs(dedup_hash);
CREATE INDEX IF NOT EXISTS idx_jobs_posted_at          ON silver.jobs(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_area               ON silver.jobs(area);
CREATE INDEX IF NOT EXISTS idx_jobs_seniority          ON silver.jobs(seniority);


-- =============================================================================
-- Tabela de Auditoria e Observabilidade do Pipeline (Melhoria C)
-- =============================================================================
CREATE TABLE IF NOT EXISTS silver.pipeline_logs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_date   DATE NOT NULL UNIQUE,
    started_at       TIMESTAMP DEFAULT NOW(),
    ended_at         TIMESTAMP,
    status           VARCHAR(20) DEFAULT 'RUNNING', -- 'RUNNING', 'SUCCESS', 'FAILED'
    adzuna_count     INT DEFAULT 0,
    jooble_count     INT DEFAULT 0,
    remoteok_count   INT DEFAULT 0,
    gupy_count       INT DEFAULT 0,
    raw_inserted     INT DEFAULT 0,
    dedup_new        INT DEFAULT 0,
    dedup_duplicates INT DEFAULT 0,
    classified_count INT DEFAULT 0,
    error_message    TEXT,
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_logs_date ON silver.pipeline_logs(execution_date);

-- =============================================================================
-- Tabela de Monitoramento de Skills Não Mapeadas (Melhoria A)
-- =============================================================================
CREATE TABLE IF NOT EXISTS silver.unmapped_skills_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id      UUID REFERENCES silver.jobs(job_id) ON DELETE CASCADE,
    word        VARCHAR(100) NOT NULL,
    occurred_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_unmapped_skills_word ON silver.unmapped_skills_logs(word);

