# DataTrack — Resumo da Fase 5 (Dashboards, E-mail Digest e Higienização de Dados)

Este documento apresenta o resumo da **Fase 5** do projeto DataTrack, detalhando a construção dos dashboards interativos, a integração do e-mail digest, e as correções de classificação e higienização que garantiram a qualidade dos dados na camada analítica.

---

## 1. O que foi implementado

### A. Dashboards Interativos (Streamlit + Plotly)

Criamos dois dashboards independentes com tema dark/light dinâmico, glassmorphism e micro-animações:

**Dashboard Público** (`dashboard/`) — voltado para candidatos e profissionais de dados:
- **Busca Inteligente** (`app.py`): Filtros dinâmicos por área, senioridade, localização, modalidade de trabalho (multiselect), skills e recência. Drill-down para detalhes da vaga com link direto de candidatura. Indicador visual "200+" quando os resultados excedem o limite.
- **Visão Geral do Mercado** (`pages/2_visao_geral.py`): KPIs no topo (Total de Vagas, Trabalho Híbrido, Trabalho Remoto, Novas Vagas 24h). Gráficos Plotly de distribuição por área, rosca de senioridade, e barras empilhadas de modalidade por área.

**Dashboard Interno** (`dashboard_interno/`) — voltado para monitoramento operacional:
- **Telemetria do Pipeline** (`app.py`): Status da última execução, registros brutos ingeridos, novas vagas deduplicadas, taxa de deduplicação. Gráfico de evolução diária de volumetria por fonte.
- **Histórico de Logs** (`pages/2_logs_execucao.py`): Gráfico de latência operacional (tempo de execução por dia). Tabela de auditoria com drill-down para métricas de volume e rastreamento de erros.
- **Governança de Skills** (`pages/3_skills_nao_mapeadas.py`): Ranking de termos não mapeados com contagem de ocorrências e drill-down para as vagas de origem.

### B. Módulos Compartilhados

Ambos os dashboards seguem a mesma arquitetura modular:
- `database.py` — Consultas SQL centralizadas com cache `@st.cache_data(ttl=3600)`
- `theme.py` — Injeção de CSS dinâmico para suporte a temas claro e escuro
- `.streamlit/config.toml` — Configuração visual padrão
- `.streamlit/secrets.toml` — Credenciais locais (incluído no `.gitignore`)

### C. E-mail Digest (SendGrid)

Criamos o plugin `plugins/email_sender.py` que envia automaticamente um digest diário com:
- Destaques das novas vagas coletadas
- Métricas consolidadas do pipeline (volume, taxa de deduplicação)
- Fallback local: se a API key do SendGrid não estiver configurada, o HTML é salvo em `logs/last_email_digest.html`

A tarefa `send_email_digest` foi integrada à DAG do Airflow e só dispara se o pipeline completo for concluído com sucesso.

---

## 2. Correções e Higienização de Dados

### A. Classificação em Duas Etapas

Resolvemos o problema de vagas "Não Classificadas" (`unknown`) poluindo os dashboards. Muitas eram vagas fora da área de dados (saúde, jornalismo, TI genérico de suporte):

1. **Tech Check**: Filtra se o título ou descrição contêm termos de tecnologia
2. **Data Check**: Valida se a vaga de tecnologia pertence à área de dados
3. **Classificação Final**: Categoriza em uma das 5 sub-áreas de dados

**Impacto:** Tabela fato limpa de 1.743 para **985 vagas qualificadas**, eliminando 758 registros irrelevantes.

### B. Correção de Senioridades

Substituímos comparação por substring por **Regex com word boundaries** (`\b`) para mapear abreviações como `JR`, `PL` e `SR` em qualquer posição do título:

**Impacto:** Vagas com senioridade desconhecida caíram de 1.031 para **789** (242 mapeadas corretamente).

### C. Inferência de Modalidade de Trabalho

Criamos a função `infer_modalidade` que analisa título, localização e descrição para classificar vagas como Remoto, Híbrido ou Presencial:

- Termos remotos: `remoto`, `remote`, `home office`, `teletrabalho`, `wfh`
- Termos híbridos: `hibrido`, `hybrid`, `modelo hibrido`, `dias no escritório`
- Garantia de exclusão mútua: híbrido anula remoto

**Impacto:** 93 vagas híbridas identificadas (antes: 0), 210 remotas, 1.440 presenciais.

### D. Detecção de Trabalho Remoto

Corrigimos falsos negativos na detecção de vagas remotas. APIs como Adzuna e Jooble não possuem campo explícito para isso, e a Gupy trazia falso negativo quando o termo estava apenas no título.

**Impacto:** Indicador de vagas remotas corrigido de ~8.4% para ~11.2%.

### E. Bugs de Integração Corrigidos

1. Operadores PostgreSQL `IN (:param)` → `= ANY(:param)` nos filtros dinâmicos
2. Nomes de colunas incorretos no schema `gold.agg_skills_frequency`
3. Mapeamento de aliases na query de evolução diária do dashboard interno
4. Importação de Pandas ausente no dashboard interno
5. Inicialização de variável `event = None` no painel de governança

---

## 3. Métricas Finais da Gold Layer

| Métrica | Valor |
|---------|-------|
| Total de vagas qualificadas | 985 |
| Vagas remotas (100%) | 51 |
| Vagas híbridas | 70 |
| Vagas presenciais | 864 |
| Testes dbt automatizados | 68 |
| Testes unitários Python | 40+ |

---

## 4. Como Rodar os Dashboards

```bash
# Dashboard Público (porta 8501)
streamlit run dashboard/app.py

# Dashboard Interno (porta 8502)
streamlit run dashboard_interno/app.py
```

Para forçar a atualização dos dados em cache, pressione `C` no navegador ou selecione "Clear cache" no menu do Streamlit.

---

## 5. Decisões Técnicas Relevantes

- **Multiselect de modalidade vs. selectbox**: Optamos pelo multiselect para permitir combinações livres (ex: Remoto + Híbrido, sem Presencial)
- **Card de Trabalho Híbrido vs. Empresas Contratando**: Substituímos o card de empresas pelo de híbrido porque a modalidade de trabalho é informação mais acionável para o candidato
- **Gráfico de latência no topo**: Posicionar no topo da página de logs dá visibilidade imediata ao engenheiro para diagnosticar degradação de performance
- **Classificação em 2 etapas**: Abordagem mais conservadora que elimina falsos positivos sem perder vagas legítimas de dados
- **Regex com \b para senioridade**: Evita falsos positivos (ex: `sr` dentro de `israel`) enquanto captura todas as variações posicionais
