-- dim_area.sql
-- Dimensao de areas de dados: tabela de referencia estatica com as 5 categorias
-- definidas na taxonomia do projeto (referencia_main.md, secao 10).
-- Tabela pequena e imutavel — nao depende de nenhuma fonte Silver.
-- O 'unknown' e incluido para cobrir vagas nao classificadas.

-- Usamos VALUES para definir a dimensao estaticamente — sem leitura de fonte.
-- Essa e uma pratica padrao em dbt para dimensoes de lookup pequenas.

select
    area_code,
    area_label,
    area_order
from (
    values
        ('data_engineering', 'Engenharia de Dados',          1),
        ('data_science',     'Ciencia de Dados',             2),
        ('data_analytics',   'Analise de Dados',             3),
        ('ml_mlops',         'Machine Learning / MLOps',     4),
        ('bi',               'Business Intelligence',        5),
        ('unknown',          'Nao Classificado',             6)
) as t(area_code, area_label, area_order)
