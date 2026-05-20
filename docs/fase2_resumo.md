# Resumo da Fase 2: Ingestão de Múltiplas Fontes (Bronze Layer)

Este documento resume a conclusão bem-sucedida da **Fase 2** do projeto **DataTrack**, detalhando os resultados obtidos, a arquitetura de ingestão finalizada e os próximos passos para a Fase 3.

---

## 1. Status Geral da Fase

- **Status**: Concluído (100% Funcional e Validado)
- **Duração Total da Ingestão**: ~2 minutos (execução em paralelo)
- **Total de Fontes Ativas**: 4 (Adzuna, Gupy, Jooble e RemoteOK)
- **Armazenamento**: MinIO (Bronze Layer em JSON cru particionado por data `YYYY-MM-DD/raw_jobs.json`)

---

## 2. Check-up de Arquitetura e Engenharia

### Segurança de Credenciais e Infraestrutura
* **Segurança de Variáveis de Ambiente**: Nenhuma chave de API (Adzuna ou Jooble) está hardcoded. Todas são injetadas dinamicamente via arquivo `.env` (excluído pelo `.gitignore`) e mapeadas no `docker-compose.yml`.
* **Resiliência a Chaves de API**: O extrator do Jooble detecta a ausência da chave e pula graciosamente a execução logando um aviso em vez de travar o pipeline diário.
* **WAF / Bypass de Bloqueios**:
  * **RemoteOK**: Cabeçalho de `User-Agent` simulado impede bloqueio HTTP 403 padrão.
  * **Jooble**: Direcionado para o endpoint global (`jooble.org`) para contornar o bloqueio Cloudflare rígido existente no domínio brasileiro (`br.jooble.org`).
  * **Gupy**: Simulação de comportamento de scroll humano e espera dinâmica via Playwright.

### Eficiência e Performance
* **Execução Assíncrona e Concorrência**: As 4 tarefas de ingestão rodam de forma concorrente no Airflow:
  ```
                    ┌─→ extract_adzuna   ─┐
                    ├─→ extract_gupy     ─┤
  [DAG Início] ─────┼─→ extract_jooble   ─┼──→ validate_bronze
                    └─→ extract_remoteok ─┘
  ```
* **Gerenciamento de Recursos**: O extrator Gupy utiliza contextos (`with sync_playwright() as p:`) para garantir o fechamento e desalocação do navegador virtual Chromium, prevenindo vazamentos de memória (Memory Leaks) no container Docker.
* **Comunicação Otimizada (XCom)**: As tarefas do Airflow trocam apenas o caminho de armazenamento (S3 Key) dos arquivos salvos, em vez de trafegar o conteúdo JSON bruto, mantendo o banco de dados do Airflow leve.

---

## 3. Entregáveis de Dados na Bronze (MinIO)

* **Adzuna**: `datatrack-bronze/adzuna/YYYY-MM-DD/raw_jobs.json` (~160 vagas)
* **Gupy**: `datatrack-bronze/gupy/YYYY-MM-DD/raw_jobs.json` (~400 vagas)
* **Jooble**: `datatrack-bronze/jooble/YYYY-MM-DD/raw_jobs.json` (~130 vagas)
* **RemoteOK**: `datatrack-bronze/remoteok/YYYY-MM-DD/raw_jobs.json` (feed de ~500 vagas remotas)

---

## 4. Próxima Fase: Fase 3 — Transformação Camada Silver

O objetivo da Fase 3 é pegar a "bagunça" de dados brutos e semiestruturados salvos na Bronze Layer e transformá-los em tabelas limpas, normalizadas e estruturadas na camada Silver.

### Mudança Estratégica de Infraestrutura:
* **Banco de Dados (PostgreSQL)**: Decidimos utilizar a **Supabase** (PostgreSQL Gerenciado na Nuvem) em vez de subir um container PostgreSQL local no Docker. Isso alivia o consumo de memória do computador e simula uma arquitetura de dados moderna conectando a ingestão local a um banco produtivo em nuvem.

### Principais Desafios:
1. **Configuração da Supabase**: Criação da instância gratuita de PostgreSQL e mapeamento das credenciais seguras no `.env`.
2. **Deduplicação de Vagas**: Utilizar o `rapidfuzz` (distância de Levenshtein) para identificar e agrupar vagas idênticas publicadas em plataformas diferentes.
3. **Normalização de Áreas e Senioridade**: Mapear cargos bagunçados (ex: "Analista de Analytics Sr", "Data Engineer II", "Estagiário de BI") em categorias fixas de Área (Engenharia, Ciência, Analítica, BI) e Senioridade (Júnior, Pleno, Sênior, Estágio/Trainee).
4. **Extração de Skills (Hard Skills)**: Varredura nas descrições de vagas para identificar competências-chave (Python, SQL, AWS, Airflow, Spark, dbt).
