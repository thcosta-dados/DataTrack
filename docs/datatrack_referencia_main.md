# DataTrack — Documento de Referência do Projeto

> Este arquivo serve como contexto completo para novas sessões de orientação técnica.
> Cole-o no início de qualquer nova conversa e inicie com:
> "Continuo o projeto DataTrack. Estou na Fase [X]. [Descreva o que quer resolver]"
>
> O assistente não vai rediagnosticar o problema nem perguntar sobre os
> empreendimentos anteriores — o projeto já está definido. Descreva o estado
> atual e a dúvida específica.

---

## 1. Perfil do Estudante

**Nome:** Thiago, 25 anos
**Curso:** Tecnologia em Banco de Dados — Universidade Presbiteriana Mackenzie (2026–2028)
**Objetivo imediato:** Primeiro estágio em Engenharia de Dados
**Objetivo de longo prazo:** Atuação internacional em 3–5 anos

**Habilidades atuais:**
- SQL: intermediário (certificações FGV e Udemy)
- Python: iniciante
- Excel e Power BI: conhecimento básico
- Engenharia de dados formal: nenhuma experiência prévia

**Background diferenciador:**
- Fundador de dois negócios (alimentação e acessórios): raciocínio de negócio acima da média para um candidato sem experiência formal em dados. Esse background não é o objeto do projeto, mas é um ativo real de narrativa em entrevista — especialmente para explicar por que o DataTrack foi construído com foco em produto e não apenas como exercício técnico
- Formação militar no CPOR/RJ (Comunicações), 5º lugar no pelotão: disciplina e capacidade de execução sob estrutura
- Perfil empreendedor é diferencial de portfólio, não elemento decorativo

---

## 2. Postura do Orientador Técnico

O assistente atua como orientador técnico estratégico, não como motivador. Isso significa:

- Fazer perguntas antes de dar respostas quando o contexto for ambíguo
- Apontar erros de raciocínio com precisão e sem hesitação, explicando o porquê e o caminho correto
- Basear todas as recomendações em fatos técnicos e de mercado, nunca em conceitos genéricos
- Avaliar cada ideia pelo critério duplo: viabilidade técnica para iniciante + valor real para recrutador
- Nunca validar ideias fracas para não desanimar
- Nunca sugerir o que qualquer tutorial do YouTube já reproduz identicamente

**Critério final de qualidade:**
> "Se um engenheiro de dados sênior visse esse repositório no GitHub, ele conseguiria identificar que a pessoa entende pipelines, modelagem e decisões de arquitetura — ou pareceria só mais um tutorial com nome diferente?"

---

## 3. Definição do Projeto

### Nome
**DataTrack**

### O que é
Plataforma de inteligência de mercado de trabalho para a área de dados. O sistema coleta vagas de múltiplas fontes, processa, deduplica e classifica por área e senioridade, entrega os resultados via dashboard web (Streamlit) e e-mail digest diário — tudo orquestrado pelo Apache Airflow, com deploy na AWS.

### Problema que resolve
Não existe ferramenta consolidada e gratuita que:
1. Agregue vagas de dados de múltiplas fontes sem duplicação
2. Classifique por área (DE, DS, Analytics, ML, BI) e senioridade automaticamente
3. Extraia e monitore tendências de skills ao longo do tempo
4. Entregue dados atualizados diariamente via dashboard e alerta por e-mail

### Público-alvo
Qualquer pessoa em transição para a área de dados: iniciantes, profissionais em requalificação, pessoas procurando crescimento de júnior para pleno.

### Por que é forte como portfólio
- Resolve uma dor real que o próprio avaliador técnico pode ter sentido
- Combina ingestão + deduplicação + transformação + orquestração + modelagem dimensional + entrega
- Tem um produto consumível por qualquer pessoa, não só pelo autor
- Cada decisão técnica é justificável e defensável sob pressão de entrevista

---

## 4. Decisões Tomadas (não reabrir sem justificativa técnica nova)

| # | Decisão | Escolha | Justificativa |
|---|---|---|---|
| 1 | Ambiente de execução | Local com Docker Compose durante desenvolvimento → AWS free tier em produção | Padrão profissional: debug isolado localmente, deploy só quando estável |
| 2 | Interface de entrega | Dashboard Streamlit + e-mail digest via Airflow | São camadas complementares e independentes. O Airflow não fica fraco com o dashboard — ele orquestra os dois |
| 3 | Escopo de vagas | Apenas área de dados (5 categorias) | Taxonomia precisa, narrativa coesa, altamente relevante para quem avalia o portfólio |
| 4 | Qualidade vs velocidade | Prioridade total para qualidade e excelência técnica | Thiago não tem pressa. Cada camada deve ser feita com profundidade real |

---

## 5. Fontes de Dados

| Fonte | Tipo | Autenticação | Cobertura | Observação |
|---|---|---|---|---|
| **Adzuna** | API REST | API key gratuita | BR + global | Melhor cobertura nacional, documentação clara |
| **Jooble** | API REST | API key gratuita | BR + global | Complementar ao Adzuna |
| **RemoteOK** | API REST | Sem autenticação | Internacional (remoto) | JSON público, sem barreiras |
| **Gupy** | Web scraping | Não se aplica | Brasil (principal ATS) | Maior ATS do Brasil. Empresas como Nubank, iFood, Itaú publicam aqui |

### Por que não LinkedIn ou Indeed
Ambos bloqueiam scrapers ativamente e proíbem coleta nos termos de uso. Um iniciante vai passar mais tempo driblando rate limits, CAPTCHAs e bloqueios de IP do que construindo engenharia real. Isso é armadilha — não vale o esforço.

---

## 6. Arquitetura Completa

### Visão geral (fluxo)

```
Fontes externas (APIs + Scraping)
         |
         v
   Bronze Layer
   AWS S3 — JSON bruto, exatamente como chegou da fonte
         |
         v
   Silver Layer
   PostgreSQL — limpeza, deduplicação, normalização, extração de skills
         |
         v
   Gold Layer
   dbt Core — star schema, modelos dimensionais, marts analíticos
         |
    _____|_____
   |           |
   v           v
Dashboard   E-mail digest
Streamlit   Airflow + SendGrid
```

Tudo dentro do perímetro do Apache Airflow, que orquestra cada etapa como tasks com dependências explícitas.

---

## 7. Camada Bronze — AWS S3

**O que armazena:** dados brutos exatamente como chegaram da fonte, sem nenhuma transformação.

**Por que S3 e não banco de dados diretamente:**
Dados brutos têm estrutura imprevisível e variável entre fontes. Object storage é mais barato, tolerante a mudanças de schema, e dá auditabilidade total — sempre é possível reler o original se alguma transformação posterior introduzir erro. Essa decisão tem nome em entrevista: "raw layer para preservar a fonte da verdade".

**Estrutura de prefixos no bucket:**
```
s3://datatrack-bronze/
  adzuna/2026-05-13/raw_jobs.json
  jooble/2026-05-13/raw_jobs.json
  remoteok/2026-05-13/raw_jobs.json
  gupy/2026-05-13/raw_jobs.json
```

**Biblioteca de scraping:** Playwright (renderiza JavaScript — o Gupy usa React) + BeautifulSoup4 (parsing do HTML resultante). Não usar requests puro para o Gupy: a página não renderiza o conteúdo sem JavaScript.

---

## 8. Camada Silver — PostgreSQL (Supabase)

**O que contém:** dados limpos, deduplicados, normalizados e estruturados para consumo.

**Por que PostgreSQL (via Supabase) e não SQLite:**
SQLite não suporta conexões concorrentes de forma confiável, não tem suporte real a tipos avançados como JSONB, e não existe em nenhuma vaga de DE sênior. PostgreSQL é ACID e maduro. Usaremos a hospedagem gerenciada da **Supabase** (que fornece uma instância de PostgreSQL na nuvem pronta para uso) para evitar consumir recursos de hardware locais (Docker) e para demonstrar proficiência em banco de dados na nuvem desde o início do desenvolvimento da camada estruturada.

### Lógica de deduplicação
Biblioteca: `rapidfuzz`

Uma vaga é considerada duplicata se satisfizer os três critérios simultaneamente:
1. Similaridade de título >= 85% (via `token_sort_ratio` — tolerante a variações de ordem de palavras)
2. Similaridade de empresa >= 90%
3. Mesma localização normalizada
4. Postadas em janela de 3 dias

Hash de dedup: `SHA256(titulo_normalizado + empresa_normalizada + localizacao_normalizada + janela_de_3_dias)`

### Schema principal da Silver

```sql
-- Todos os registros normalizados (pré-dedup)
CREATE TABLE silver.raw_jobs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source      VARCHAR(30),       -- 'adzuna', 'jooble', 'remoteok', 'gupy'
    source_id   VARCHAR(255),      -- ID original da fonte
    title       TEXT,
    company     TEXT,
    location    TEXT,
    description TEXT,
    url         TEXT,
    posted_at   DATE,
    is_remote   BOOLEAN,
    payload     JSONB,             -- registro original completo
    ingested_at TIMESTAMP DEFAULT NOW()
);

-- Registros após deduplicação
CREATE TABLE silver.jobs (
    job_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_ids  TEXT[],            -- todos os IDs de fontes que mapearam para esta vaga
    dedup_hash  VARCHAR(64) UNIQUE,
    title       TEXT,
    company_id  UUID REFERENCES silver.companies(id),
    location_id UUID REFERENCES silver.locations(id),
    area        VARCHAR(50),       -- 'data_engineering', 'data_science', etc.
    seniority   VARCHAR(30),       -- 'estagio', 'junior', 'pleno', 'senior', etc.
    skills      TEXT[],            -- array de skills extraídas
    url         TEXT,
    posted_at   DATE,
    is_remote   BOOLEAN,
    is_hybrid   BOOLEAN,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

---

## 9. Camada Gold — dbt Core

**O que contém:** modelos dimensionais prontos para consumo analítico.

**Por que dbt e não SQL puro:**
dbt tem controle de versão de transformações, lineage automático (sabe de onde cada coluna veio), testes nativos (not_null, unique, accepted_values), documentação gerada automaticamente, e aparece em aproximadamente 70% das vagas de DE pleno e sênior no Brasil. Um iniciante que domina dbt sai na frente de candidatos com anos a mais de experiência que nunca tocaram na ferramenta.

### Estrutura de modelos dbt

```
models/
  staging/
    stg_jobs.sql              -- leitura direta da silver, renomeação de campos
    stg_companies.sql
    stg_locations.sql
  intermediate/
    int_jobs_with_skills.sql  -- explode o array de skills para linhas individuais
    int_jobs_classified.sql   -- aplica classificação de área e senioridade
  marts/
    dim_company.sql
    dim_location.sql
    dim_skill.sql
    dim_seniority.sql
    dim_area.sql
    fact_job_posting.sql      -- tabela fato central
    agg_skills_frequency.sql  -- snapshot diário de frequência de skills por área
    agg_market_overview.sql   -- visão consolidada do mercado
```

### Star schema (tabela fato + dimensões)

```
fact_job_posting
├── job_id            PK
├── company_id        FK → dim_company
├── location_id       FK → dim_location
├── area_id           FK → dim_area
├── seniority_id      FK → dim_seniority
├── posted_date
├── source
├── is_remote
├── is_hybrid
└── ingestion_date

dim_company:   company_id, name, domain, company_size ('grande', 'media', 'pequena')
dim_location:  location_id, city, state, country, is_remote_first
dim_area:      area_id, code, label (ex: 'data_engineering' → 'Engenharia de Dados')
dim_seniority: seniority_id, code, label, order_rank
dim_skill:     skill_id, name, canonical_name, category
```

---

## 10. Taxonomia de Áreas e Skills

### Áreas cobertas (5 categorias)

| Código | Label |
|---|---|
| `data_engineering` | Engenharia de Dados |
| `data_science` | Ciência de Dados |
| `data_analytics` | Análise de Dados |
| `ml_mlops` | Machine Learning / MLOps |
| `bi` | Business Intelligence |

### Classificação de senioridade

`estagio` → `junior` → `pleno` → `senior` → `especialista` → `lead`

Identificação por palavras-chave no título e descrição. Exemplos: "estagiário", "Jr.", "Pleno", "Sênior", "Staff", "Principal".

### Recência (filtro temporal para o usuário final)

O campo `posted_at` já existe no schema Silver. Na Gold layer e no Dashboard, o usuário pode filtrar por:

| Opção | Lógica |
|---|---|
| Últimas 24 horas | `posted_at >= NOW() - INTERVAL '1 day'` |
| Últimos 3 dias | `posted_at >= NOW() - INTERVAL '3 days'` |
| Última semana | `posted_at >= NOW() - INTERVAL '7 days'` |

Esse filtro não exige nenhum campo novo — é apenas um WHERE dinâmico no momento da consulta. A Bronze coleta tudo (janela de 7 dias via `max_days_old`), e o usuário final refina conforme a urgência.

### Porte da empresa (métrica derivada)

Não depende de fonte externa. É calculado empiricamente a partir dos dados que já coletamos:

| Classificação | Critério (vagas publicadas em 30 dias) |
|---|---|
| `grande` | 10+ vagas na área de dados |
| `media` | 3–9 vagas |
| `pequena` | 1–2 vagas |

Implementação no dbt (Gold layer):
```sql
-- models/intermediate/int_company_size.sql
WITH posting_volume AS (
    SELECT company, COUNT(*) AS total_postings
    FROM silver.jobs
    WHERE posted_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY company
)
SELECT
    company,
    CASE
        WHEN total_postings >= 10 THEN 'grande'
        WHEN total_postings >= 3  THEN 'media'
        ELSE 'pequena'
    END AS company_size
FROM posting_volume
```

**Por que isso funciona como proxy:** empresas grandes (Nubank, iFood, Itaú) naturalmente publicam mais vagas do que startups de 20 pessoas. O volume de postagens é um indicador observável e defensável — sem precisar de APIs externas de CNPJ ou dados cadastrais.

**Limitação documentada:** uma empresa pequena em fase de hiper-crescimento pode publicar muitas vagas e ser classificada como "grande". Essa limitação deve ser mencionada no README como trade-off consciente.

### Skills por área (extração via regex + dicionário)

**Limitação conhecida:** o dicionário cobre apenas skills mapeadas manualmente. Skills novas que surgirem no mercado não serão detectadas até que o dicionário seja atualizado. Essa limitação precisa ser documentada explicitamente no README e ter uma estratégia de resposta antes do deploy — mesmo que a estratégia inicial seja revisão manual periódica.

**Data Engineering:** Python, SQL, Spark, Airflow, dbt, Kafka, AWS, GCP, Azure, Docker, Kubernetes, PostgreSQL, Redshift, BigQuery, Snowflake, Databricks, PySpark, Prefect, Luigi, S3, Glue, Lambda

**Data Science:** Python, R, TensorFlow, PyTorch, scikit-learn, pandas, NumPy, MLflow, Prophet, statsmodels, Jupyter, SHAP, XGBoost, LightGBM

**Analytics:** SQL, Power BI, Tableau, Looker, Metabase, Google Analytics, DAX, Excel, Superset

**ML/MLOps:** MLflow, Kubeflow, SageMaker, BentoML, Docker, Kubernetes, TensorFlow Serving, Ray

**BI:** Power BI, Tableau, Looker, Qlik, MicroStrategy, DAX, SQL, MQL

---

## 11. Orquestração — Apache Airflow

### Por que Airflow e não CRON

CRON executa comandos. Airflow gerencia dependências entre tasks, tem retry automático com backoff exponencial, UI de monitoramento, backfill de datas históricas, tratamento de falhas parciais, alertas por e-mail em falha, e é o padrão de mercado que aparece em entrevistas. Para uma pipeline com 8+ tasks encadeadas e dependências entre fontes, CRON seria indefensável em entrevista.

### DAG principal: `datatrack_daily_pipeline`

**Schedule:** `0 7 * * *` (todo dia às 7h BRT)

**Estrutura de tasks e dependências:**

```
extract_adzuna  ─┐
extract_jooble   ├──→  validate_bronze  ──→  silver_deduplicate  ──→  silver_normalize
extract_remoteok │                                                          │
extract_gupy    ─┘                                                          │
                                                                            v
                                                                        dbt_run
                                                                            │
                                                              ┌─────────────┴──────────────┐
                                                              v                            v
                                                    streamlit_refresh            send_email_digest
```

### Descrição de cada task

| Task | Operador | Responsabilidade |
|---|---|---|
| `extract_adzuna` | PythonOperator | Chama a API com paginação, salva JSON no S3 |
| `extract_jooble` | PythonOperator | Chama a API, salva JSON no S3 |
| `extract_remoteok` | PythonOperator | Chama endpoint público, salva JSON no S3 |
| `extract_gupy` | PythonOperator | Playwright scraping com seletores semânticos, salva JSON no S3 |
| `validate_bronze` | PythonOperator | Verifica se todos os arquivos chegaram; valida schema mínimo; falha a DAG se alguma fonte não entregou |
| `silver_deduplicate` | PythonOperator | Lê S3, aplica rapidfuzz, identifica duplicatas, carrega no PostgreSQL |
| `silver_normalize` | PythonOperator | Normaliza campos, extrai skills via dicionário, classifica área e senioridade |
| `dbt_run` | BashOperator | Executa `dbt run` + `dbt test` — falha a DAG se algum teste falhar |
| `streamlit_refresh` | PythonOperator | Invalida cache do Streamlit (ou simplesmente aguarda leitura direta do banco) |
| `send_email_digest` | PythonOperator | Consulta gold layer, monta e-mail HTML com vagas novas e resumo de mercado, envia via SendGrid |

---

## 12. Dashboard Streamlit — Estrutura de Páginas

| Página | Conteúdo |
|---|---|
| **Visão geral do mercado** | Total de vagas ativas por área, distribuição por senioridade, top 10 cidades, proporção remoto/híbrido/presencial |
| **Tendências de skills** | Skills mais demandadas por área, skills em crescimento nos últimos 30 dias vs 30 dias anteriores, heatmap área × skill |
| **Busca de vagas** | Filtros combinados: área, senioridade, localização, skill específica, modalidade, recência (24h / 3 dias / 7 dias), porte da empresa (grande / média / pequena); resultado com link para vaga original |
| **Inteligência de empresas** | Quais empresas mais contratam, para quais áreas, com quais skills, evolução ao longo do tempo |

---

## 13. Stack Técnica Completa

| Camada | Tecnologia | Por que essa e não outra |
|---|---|---|
| Orquestração | Apache Airflow | Padrão de mercado, DAGs com dependências reais, retry, backfill, UI de monitoramento |
| Ingestão de APIs | Python + `requests` | Simples, direto, sem overhead desnecessário |
| Scraping | `playwright` + `beautifulsoup4` | Playwright renderiza JavaScript (Gupy usa React); BS4 para parsing do DOM |
| Raw storage | AWS S3 | Barato, tolerante a schema changes, auditável, padrão de data lakehouse |
| Banco de dados | PostgreSQL (Supabase Cloud) | ACID, maduro, hospedagem em nuvem gratuita, elimina overhead de banco de dados rodando localmente no Docker |
| Transformação | dbt Core | Padrão moderno de DE, lineage automático, testes nativos, documentação gerada |
| Deduplicação | `rapidfuzz` | Fuzzy string matching eficiente para deduplicação de registros textuais |
| Dashboard | Streamlit | Python-native, deploy gratuito no Streamlit Community Cloud, sem frontend separado |
| E-mail | Airflow + SendGrid | Free tier de 100 e-mails/dia, entrega profissional com tracking |
| Containerização | Docker Compose | Ambiente reprodutível localmente antes do deploy |
| Cloud | AWS (S3 + RDS + EC2) | Free tier disponível, padrão de mercado, vale citar no CV |

### Por que NÃO usar estas tecnologias

| Tecnologia descartada | Motivo |
|---|---|
| Apache Spark | Volume de vagas (estimado: 1.000–10.000/dia) cabe em memória RAM. Spark tem overhead de cluster que não se justifica aqui. Usar Spark seria over-engineering sem nenhuma vantagem prática — e um engenheiro sênior percebe isso imediatamente |
| Apache Kafka | Não há requisito de ingestão em tempo real. Pipeline batch diário resolve o problema com muito menos complexidade operacional |
| Snowflake ou BigQuery | Free tier limitado demais para desenvolvimento contínuo. PostgreSQL é suficiente para a escala e demonstra design de banco relacional com mais clareza |
| FastAPI | Streamlit lê direto do banco. Adicionar uma camada de API REST seria uma abstração desnecessária nessa arquitetura |
| Prefect ou Dagster | Airflow aparece em aproximadamente 80% das vagas de DE no Brasil. Entrevistas técnicas vão perguntar sobre Airflow |
| Luigi | Obsoleto para novos projetos. Sem UI nativa, sem suporte ativo relevante |

---

## 14. Infraestrutura

### Ambiente local (desenvolvimento e testes)

```yaml
# docker-compose.yml — serviços principais
services:
  postgres:
    image: postgres:15
    # Silver e Gold layers localmente

  minio:
    image: minio/minio
    # Equivalente local do S3 para Bronze layer

  airflow-webserver:
    image: apache/airflow:2.8
    # Interface gráfica das DAGs

  airflow-scheduler:
    image: apache/airflow:2.8
    # Execução das tasks

  streamlit:
    build: ./dashboard
    # Visualização local do resultado
```

### Ambiente AWS (produção)

| Serviço AWS | Uso no projeto | Limites do free tier |
|---|---|---|
| S3 | Bronze layer — JSON bruto de todas as fontes | 5 GB armazenamento grátis |
| Supabase (Cloud PostgreSQL) | Silver + Gold layers | Instância gerenciada dedicada gratuita, suporte nativo a extensões e conexões remotas fáceis |
| EC2 t2.micro | Airflow + Playwright scraping | 750 horas/mês, 12 meses grátis |
| Streamlit Community Cloud | Dashboard web público | Gratuito permanente |

### Migração local → AWS
1. Substituir variáveis de conexão do MinIO pelas credenciais do S3
2. Conectar o Airflow local e o dashboard final diretamente à string de conexão da nuvem fornecida pelo Supabase
3. Empacotar Airflow em Docker e deployar no EC2
4. Conectar Streamlit Community Cloud ao RDS via variáveis de ambiente secretas
5. Documentar todo o processo de migração no README — isso sozinho já é diferencial de portfólio

---

## 15. O Que Cada Componente Prova Para um Recrutador Sênior

| Componente | O que demonstra na prática |
|---|---|
| Ingestão de múltiplas APIs | Sabe consumir endpoints REST com paginação, autenticação e tratamento de erros |
| Scraping com Playwright | Entende renderização de páginas JavaScript, seletores semânticos, resiliência a mudanças de layout |
| Bronze layer em S3 | Conhece o padrão de raw layer e o conceito de fonte da verdade imutável |
| Deduplicação com rapidfuzz | Resolve um problema real de qualidade de dados com lógica própria, não apenas carrega registros |
| Silver em PostgreSQL (Supabase) com schema definido | Sabe modelar banco de dados relacional na nuvem, criar constraints e pensar em integridade dos dados |
| dbt com staging → intermediate → marts | Domina a camada de transformação do stack moderno de DE |
| Star schema com tabela fato e dimensões | Entende modelagem dimensional para consumo analítico |
| Airflow com DAG de múltiplas tasks paralelas e dependentes | Usa orquestração real, não só agendamento — entende retries, sensores e dependency management |
| Deploy na AWS | O projeto sai do "roda só no meu PC" — tem endereço real, URL pública |
| Produto acessível por outras pessoas | Construiu algo com valor externo, não um exercício acadêmico |

---

## 16. Riscos e Armadilhas Comuns

| Risco | Por que acontece | Como evitar |
|---|---|---|
| Gupy muda o HTML e o scraper quebra | ATS atualizam o layout sem aviso | Usar seletores semânticos (aria-label, data-testid) em vez de classes CSS geradas dinamicamente. Monitorar no Airflow com alerta por e-mail em falha |
| API da Adzuna atinge o limite diário | Free tier tem cota de requisições | Implementar paginação correta. Armazenar IDs já coletados para não recoletar o mesmo registro no dia seguinte |
| Deduplicação com falsos positivos | Threshold muito agressivo junta vagas diferentes | Testar o threshold do rapidfuzz com dados reais antes de fixar. Logar casos limítrofes (75%–89%) em tabela de revisão |
| DAG monolítica e não testável | Iniciante coloca toda a lógica em um único PythonOperator | Cada task deve ter uma única responsabilidade. Funções de negócio ficam em módulos Python separados — a task só os chama |
| dbt sem testes | Não saber que dbt tem um sistema de testes embutido | Criar `schema.yml` com testes `not_null`, `unique` e `accepted_values` desde o primeiro modelo. Falha de teste deve quebrar a DAG |
| Credenciais no código | Inexperiência com boas práticas de segurança | Usar Airflow Variables e Connections para credenciais. Nunca fazer commit de API keys. Usar `.env` com Docker e `.gitignore` correspondente |
| Over-engineering sem escala | Adicionar tecnologias para impressionar sem justificativa | Cada ferramenta deve ter uma razão técnica defensável. "Usei porque achei legal" não funciona em entrevista |
| Skills não mapeadas pelo dicionário | Ferramenta nova surge no mercado e não está no dicionário | Documentar a limitação no README. Definir processo de revisão periódica do dicionário antes do deploy |

---

## 17. Roadmap de Implementação

### Fase 1 — Fundação local (2–3 semanas)
- Setup do Docker Compose com todos os serviços (Airflow, PostgreSQL, MinIO)
- Implementar extractor da Adzuna (API mais simples para começar)
- Gravar JSON bruto no MinIO (equivalente local do S3)
- Criar DAG básica com 1 extractor + validate_bronze
- Testar o ciclo completo localmente antes de adicionar mais fontes

### Fase 2 — Múltiplas fontes (2 semanas)
- Adicionar extractors do Jooble e RemoteOK
- Implementar scraping do Gupy com Playwright
- Paralelizar os 4 extractors na DAG
- Implementar validate_bronze que falha se alguma fonte não entregou

### Fase 3 — Silver layer (2 semanas)
- Configurar projeto na Supabase e criar schema PostgreSQL silver com todas as tabelas na nuvem
- Implementar lógica de deduplicação com rapidfuzz
- Normalizar campos: área, senioridade, skills, localização
- Adicionar tasks silver na DAG com dependência do validate_bronze

### Fase 4 — Gold layer com dbt (2 semanas)
- Setup do dbt Core no projeto (profiles, packages)
- Criar modelos staging → intermediate → marts
- Implementar star schema completo
- Adicionar testes dbt em todos os modelos (not_null, unique, accepted_values)
- Integrar `dbt run && dbt test` como BashOperator na DAG

### Fase 5 — Entrega (1–2 semanas)
- Dashboard Streamlit com as 4 páginas definidas
- E-mail digest formatado em HTML com vagas novas + resumo do mercado
- Tasks de entrega na DAG com dependência do dbt_run
- Testar o ciclo completo de ponta a ponta

### Fase 6 — Deploy na AWS e documentação (1–2 semanas)
- Migrar MinIO → AWS S3
- (Opcional) Migrar Supabase → AWS RDS (ou manter no Supabase, demonstrando arquitetura multi-cloud/híbrida moderna)
- Deploy do Airflow no EC2
- Deploy do Streamlit no Streamlit Community Cloud
- README completo com: diagrama de arquitetura, decisões técnicas, como rodar localmente, como fazer deploy
- Documentar pelo menos um problema real encontrado durante o desenvolvimento e como foi resolvido

---

## 18. Nota do Projeto e O Que Elevaria a Nota

**Nota atual do design: 8,5 / 10**

Esta nota é honesta para o contexto: um candidato a primeiro estágio em DE, sem experiência formal, propondo uma arquitetura completamente defensável com stack moderno e produto real.

**O que garante os 8,5:**
- Multi-source ingestion com API e scraping
- Medallion architecture com justificativa clara de cada camada
- dbt no lugar de SQL puro nas transformações
- Airflow com DAG de tasks paralelas e dependentes reais
- Deduplicação com lógica própria (não apenas carregar registros)
- Star schema com modelagem dimensional
- Deploy na AWS
- Produto com valor externo real

**O que impede de chegar ao 9,5:**
- Sem pipeline de CI/CD (GitHub Actions rodando `dbt test` a cada pull request)
- Sem camada de observabilidade além dos logs do Airflow
- Extração de skills baseada em regex e dicionário — funcional, mas um engenheiro sênior vai perguntar o que acontece quando uma skill nova surge no mercado. Essa pergunta precisa de resposta antes do deploy
- Sem estratégia explícita de data retention (quanto tempo os dados ficam no S3? E no RDS?)

**O que elevaria para 9,5:**
1. Adicionar GitHub Actions com `dbt test` no CI
2. Adicionar testes de qualidade com Great Expectations ou pelo menos fixtures de validação de schema
3. Documentar explicitamente a estratégia de tratamento de skills não mapeadas
4. Adicionar política de retenção de dados e particionamento no S3 por data

---

## 19. Como Usar Este Documento em Novas Conversas

Cole o conteúdo completo deste arquivo no início de uma nova conversa e comece com:

> "Continuo o projeto DataTrack. Estou na Fase [X] do roadmap. [Descreva o que quer resolver ou onde travou]"

O assistente vai manter o contexto completo: perfil do Thiago, stack escolhida, decisões já tomadas, arquitetura definida e os critérios de qualidade acordados.

Não é necessário reexplicar o projeto nem os empreendimentos anteriores. Apenas descreva o estado atual e a dúvida específica.
