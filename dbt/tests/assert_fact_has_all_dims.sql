-- tests/assert_fact_has_all_dims.sql
-- Teste generico de integridade referencial para a fact table.
-- Verifica que todas as company_id e location_id da fact_job_posting
-- existem nas suas respectivas dimensoes.
--
-- Convencao dbt: um teste customizado de arquivo retorna 0 linhas se passou,
-- e > 0 linhas se falhou. O dbt falha o teste quando o resultado nao e vazio.

-- Vagas cuja company_id nao existe em dim_company
select
    'orphan_company' as check_type,
    f.job_id,
    f.company_id as orphan_id
from {{ ref('fact_job_posting') }} f
left join {{ ref('dim_company') }} c
    on f.company_id = c.company_id
where c.company_id is null

union all

-- Vagas cuja location_id nao existe em dim_location
select
    'orphan_location' as check_type,
    f.job_id,
    f.location_id as orphan_id
from {{ ref('fact_job_posting') }} f
left join {{ ref('dim_location') }} l
    on f.location_id = l.location_id
where l.location_id is null
