# DataTrack — Resumo da Fase 4 & 4.1 (Gold Layer com dbt Core & Otimizações)

Este documento apresenta o resumo da **Fase 4** (Modelagem Dimensional) e **Fase 4.1** (Melhorias Arquiteturais e DevOps), explicando o que foi implementado, as decisões tomadas e fornecendo instruções fluidas para iniciarmos a **Fase 5** (Entrega).

---

## 1. O que construímos na Fase 4 & 4.1

Nesta fase, estruturamos a camada analítica final (**Gold Layer**) e introduzimos boas práticas de mercado em observabilidade, monitoramento de dados e engenharia de software (CI/CD):

1. **dbt-core e Isolamento de Ambiente:** Configuração do dbt no virtualenv Python 3.12 (`dbt-env/`) para superar incompatibilidades com o Python 3.14 do sistema.
2. **Modelagem Dimensional (Star Schema):**
   * **Staging:** Criação de views padronizadas das tabelas da Silver (`stg_jobs`, `stg_companies`, `stg_locations`).
   * **Intermediate:** Lógicas para explodir as skills de vagas em linhas (`int_jobs_with_skills`), classificação consolidada (`int_jobs_classified`) e cálculo de porte das empresas (`int_company_size`).
   * **Marts (Esquema Estrela):** Tabelas finais e incrementais consumíveis:
     * Fato: `fact_job_posting` (incremental com surrogate keys).
     * Dimensões: `dim_company`, `dim_location`, `dim_skill`, `dim_seniority` e `dim_area`.
     * Agregações analíticas: `agg_skills_frequency` e `agg_market_overview`.
3. **Qualidade de Dados (Testes):** 68 restrições nativas no dbt (not nulos, chaves únicas, chaves estrangeiras, valores aceitos) e 1 teste customizado de integridade referencial.
4. **Camada de Auditoria e Observabilidade:** Gravação diária automática do status, contadores e tempo de execução de cada tarefa do pipeline na tabela `silver.pipeline_logs`.
5. **Monitoramento de Novas Skills:** Identificador regex inteligente em Python que detecta termos capitalizados e tecnologias novas não mapeadas nas descrições de vagas, salvando-os na tabela `silver.unmapped_skills_logs`.
6. **Integração Contínua (CI):** Pipeline configurado via GitHub Actions que simula o banco de dados PostgreSQL do zero em container temporário, valida os testes da Silver (pytest) e roda o dbt de forma totalmente isolada.

---

## 2. Decisões Técnicas Justificáveis em Entrevistas

Se um recrutador sênior perguntar o porquê de cada componente nesta fase, estas são as justificativas profissionais:

* **Por que dbt e não SQL puro/Stored Procedures?**
  > "O dbt traz boas práticas de desenvolvimento de software para o SQL: controle de versão, documentação gerada automaticamente via lineage de dependências, testes integrados nativos no schema, e materializações incrementais declarativas simples sem necessidade de escrever lógicas complexas de MERGE/UPSERT manuais."
* **Por que o Star Schema (Fato e Dimensões) na Gold Layer?**
  > "O Star Schema simplifica drasticamente a escrita de queries para ferramentas de BI e dashboards. Ele reduz junções complexas (joins) e melhora a performance de agregação de dados ao separar fatos numéricos (métricas) de atributos descritivos (dimensões), facilitando filtros dinâmicos."
* **Por que criar tabelas agregadas analíticas (`agg_`) na Gold Layer?**
  > "Isso é chamado de pré-agregação de dados. Em vez de o dashboard (Streamlit) realizar junções pesadas e contagens a cada acesso do usuário, a Gold Layer deixa os dados sumarizados prontos para leitura rápida. Isso otimiza a performance do painel web e reduz custos de processamento no banco de dados na nuvem."
* **Por que criar um log de auditoria física no banco e não apenas usar os logs do Airflow?**
  > "Logs do Airflow servem para desenvolvedores depurarem tarefas pontuais. Uma tabela de auditoria física no banco de dados permite expor métricas de integridade de dados (data quality) no próprio dashboard, dando visibilidade de governança e facilitando alertas operacionais sobre desvios volumétricos nas extrações de forma automatizada."

---

## 3. Instruções de Transição Fluida para a Fase 5 (Entrega)

A **Fase 5** tem como objetivo expor os dados limpos, refinados e testados da Gold Layer para o usuário final. Ela será composta de duas entregas independentes:

```
                  +--------------------------------+
                  |    Supabase (Camada Gold)      |
                  +---------------+----------------+
                                  |
            +---------------------+---------------------+
            | (Leitura Direta)                          | (Orquestração Diária)
            v                                           v
+-----------------------+                   +-----------------------+
|  Dashboard Streamlit  |                   |  E-mail Digest HTML   |
| (Filtros e Gráficos)  |                   |  (SendGrid + Airflow) |
+-----------------------+                   +-----------------------+
```

### Passo 1: Preparação do Ambiente Streamlit
O Streamlit é um framework Python focado em criar aplicações web interativas de forma rápida. Para começar, precisamos:

1. **Instalar o Streamlit** no ambiente Python global ou no virtualenv:
   ```bash
   pip install streamlit
   ```
2. **Criar a estrutura da pasta de Entrega:**
   Criaremos uma pasta `dashboard/` na raiz do projeto contendo:
   * `app.py`: O ponto de entrada principal do painel.
   * `pages/`: Pasta para o Streamlit reconhecer rotas de páginas adicionais automaticamente (Páginas: Visão Geral, Tendências de Skills, Busca de Vagas, Inteligência de Empresas).
3. **Gerenciar as credenciais com segurança:**
   O Streamlit usa uma pasta oculta `.streamlit/` para ler segredos locais. Criaremos o arquivo `dashboard/.streamlit/secrets.toml`:
   ```toml
   # secrets.toml — Nunca vai para o git
   [connections.postgresql]
   dialect = "postgresql"
   url = "postgresql://postgres.ywgzpiqavvtisqqzvbli:DataTrack_DB_Secure_2026!@aws-1-us-west-2.pooler.supabase.com:5432/postgres"
   ```

### Passo 2: Construção das Páginas do Dashboard
Desenvolveremos as páginas utilizando conexões seguras e eficientes, aproveitando o cache de leitura do Streamlit (`@st.cache_data`) para não sobrecarregar o Supabase com consultas repetidas:

* **Página 1: Visão Geral do Mercado:** Exibição dos KPIs gerais (total de vagas, % de vagas remotas) baseados em `agg_market_overview`. Distribuição de vagas por nível de senioridade e área em gráficos de barras e rosca.
* **Página 3: Busca Dinâmica de Vagas:** Filtros integrados (Área, Senioridade, Modalidade de Trabalho, Localização e Skills) permitindo ao usuário buscar vagas específicas e obter o link original da publicação de forma rápida.
* **Página 4: Telemetria e Saúde do Pipeline:** Página de governança apresentando os dados do `silver.pipeline_logs` e os termos não mapeados coletados em `silver.unmapped_skills_logs`, demonstrando a robustez do pipeline de forma pública.

### Passo 3: Configuração do E-mail Digest
O e-mail semanal/diário alerta o usuário sobre novas oportunidades no mercado:

1. **Setup do SendGrid (ou SMTP padrão):** Integração de um serviço de envio de e-mails para garantir taxas altas de entrega nas caixas de entrada.
2. **Desenvolvimento do Template HTML:** Um design profissional contendo os principais destaques de vagas de dados coletadas nas últimas 24h e um link para o painel Streamlit público.
3. **Criação da task no Airflow:** Adição da task `task_send_email_digest` no final da nossa DAG diária.

---

## 4. Próximo Passo Prático para Iniciar a Fase 5

Quando estiver pronto, iniciaremos com a **Preparação da Infraestrutura do Streamlit**:
1. Criar a pasta `dashboard/` e configurar a conexão em `.streamlit/secrets.toml`.
2. Escrever o script base `app.py` estruturando o layout interativo multipágina com navegação fluida e o design moderno (curadoria de cores HSL e fontes customizadas do Google Fonts para causar impacto visual imediato).
