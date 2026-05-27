-- dim_seniority.sql
-- Dimensao de senioridade: tabela de referencia estatica com a escala de niveis
-- profissionais definida na taxonomia do projeto (referencia_main.md, secao 10).
-- O campo order_rank permite ordenacao correta em graficos (estagio < junior < ... < lead).

select
    seniority_code,
    seniority_label,
    -- order_rank: menor = mais junior, maior = mais senior
    -- Util para ordenar eixos de graficos corretamente no dashboard
    order_rank
from (
    values
        ('estagio',     'Estagiario',   1),
        ('junior',      'Junior',       2),
        ('pleno',       'Pleno',        3),
        ('senior',      'Senior',       4),
        ('especialista','Especialista', 5),
        ('lead',        'Lead / Staff', 6),
        ('unknown',     'Nao Informado',7)
) as t(seniority_code, seniority_label, order_rank)
