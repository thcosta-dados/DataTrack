# Resumo da Fase 3: Construção da Camada Silver (DataTrack)

A Fase 3 representou o coração do nosso processo de Engenharia de Dados. Depois de coletarmos os dados brutos e armazenarmos no nosso Data Lake (MinIO) durante a Fase 2 (Bronze Layer), o nosso objetivo nesta fase foi limpar, cruzar, deduplicar e enriquecer esses dados para que eles tivessem valor analítico real.

Aqui documentamos tudo o que fizemos, explicando as decisões arquiteturais, os desafios técnicos enfrentados e os resultados finais alcançados.

---

## 1. A Decisão Arquitetural: Por que Supabase/PostgreSQL?

Uma das primeiras perguntas que surgem é: *"Por que não continuamos usando o MinIO na camada Silver?"*

**A resposta:** Arquiteturalmente, aplicamos o padrão **Medallion (Bronze, Silver, Gold)** dividindo o armazenamento por propósitos.
* **Bronze (MinIO):** Perfeito para dados semi-estruturados (JSONs). É o nosso Data Lake barato e infinito para os dados brutos dos nossos raspadores e extratores.
* **Silver (Supabase/PostgreSQL):** Precisávamos fazer cruzamentos (JOINs), validações complexas de unicidade, deduplicações inteligentes e atualizações incrementais (UPSERTs). Fazer isso diretamente em arquivos brutos no MinIO seria ineficiente e lento. Portanto, construímos a Silver Layer em um Banco de Dados Relacional. Escolhemos a Supabase Cloud por nos oferecer um PostgreSQL gerenciado na nuvem e simular perfeitamente um ambiente corporativo real.

## 2. Modelagem do Banco (Schema Silver)

Desenhamos um modelo relacional robusto com as seguintes tabelas dentro do schema `silver`:
* `silver.raw_jobs`: Tabela de transição (landing table) onde todos os dados brutos das 4 fontes aterrissam de forma padronizada. Cada linha representa uma vaga de uma fonte específica, contendo o payload original para fins de auditoria.
* `silver.companies`: Dimensão de empresas únicas (evita a redundância de salvar o nome da empresa milhares de vezes).
* `silver.locations`: Dimensão de localidades normalizadas (identificando inclusive se a vaga é remota).
* `silver.jobs`: A tabela principal (Fato). Aqui só entram vagas purificadas, consolidadas e deduplicadas.

## 3. O Funil de Tratamento (ETL em Python)

Construímos o fluxo de transformação usando a separação de responsabilidades (cada script executa apenas uma tarefa lógica). Esse fluxo é orquestrado de ponta a ponta pelo Apache Airflow:

### Passo 3.1 - Ingestão (Loader)
O `loader.py` conecta no MinIO, lê os JSONs gerados pela extração e insere tudo na tabela `raw_jobs`. Neste passo, padronizamos as chaves do JSON para que uma vaga da Gupy e uma vaga da Adzuna tenham a mesma estrutura inicial.

### Passo 3.2 - Deduplicação Inteligente
Aqui enfrentamos o maior desafio de lidar com dados coletados de múltiplas APIs: a mesma vaga é postada em múltiplos portais. Como saber que a vaga "Engenheiro de Dados Sênior" na Adzuna é a mesma postada na Jooble?

Implementamos o `deduplicator.py`:
* **Fuzzy Matching:** Usamos a biblioteca `rapidfuzz` para comparar títulos de vagas e nomes de empresas de forma aproximada. Se a similaridade for igual ou superior aos limiares de calibração (85% para título e 90% para empresa), consideramos iguais.
* **Hashing Determinístico:** Criamos um hash `SHA256` combinando o Título, Empresa, Localização e uma janela de data de 3 dias. Esse hash é a "impressão digital" da vaga. Se outra fonte trouxe uma vaga que gere o mesmo hash, ela é agrupada (adicionamos o novo `source_id` ao array de referências da vaga existente, sem duplicar a linha).

### Passo 3.3 - Enriquecimento (Normalizer)
Vagas brutas vêm com textos enormes na descrição, o que é inviável para análises diretas. O `normalizer.py` age como um classificador:
* Mapeia palavras-chave e classifica a **Área** da vaga (ex: Engenharia de Dados, Ciência de Dados, Analytics, BI, MLOps).
* Avalia se o título contém termos como "Jr", "Pleno" ou "Sênior" para definir a **Senioridade**.
* Lê a descrição da vaga (usando expressões regulares em Python com limites de palavras) e extrai uma lista estruturada de **Skills** técnicas (ex: `['Python', 'SQL', 'Airflow', 'AWS']`).

---

## 4. Bugs Saneados no Check-up Geral

Durante a validação final da Fase 3, identificamos e corrigimos problemas silenciosos de dados que comprometiam o pipeline:
1. **Swap de Campos no Scraper Gupy:** O extrator salvava empresa na coluna de título e vice-versa. Corrigimos a ordem de extração dos seletores HTML e adicionamos decodificação em base64 da URL para extrair o ID numérico nativo da Gupy (`jobId`).
2. **Parse de Datas ISO:** A função de data falhava ao ler carimbos ISO com timezone (ex: `Z` ou `+03:00`), convertendo todas as datas para `NULL`. Ajustamos a limpeza da string para processar apenas a fração temporal sem timezone (`YYYY-MM-DDTHH:MM:SS`).
3. **Mapeamento do Loader:** O mapeamento do dicionário Gupy tentava ler chaves de API oficiais inexistentes. Ajustamos para ler as chaves de Playwright reais (`raw_text`, `location`, `url`, `is_remote`, `source_id`).
4. **Alinhamento do Banco (Backfill):** Como as execuções anteriores estavam corrompidas no banco de dados, criamos e executamos scripts de saneamento para corrigir as datas retrógradas e reconstruir o schema.

---

## 5. O Gargalo e a Otimização Extrema

Durante a execução da DAG no Airflow, esbarramos no clássico problema de Engenharia de Dados: o **N+1 Queries Problem**.
Como estávamos consultando e inserindo vagas linha a linha de forma isolada, o Airflow levou **1 hora e 34 minutos** para deduplicar as vagas (pois abria e fechava milhares de conexões de rede com a Supabase na nuvem).

**A Solução Técnica implementada:**
1. **Connection Sharing:** Modificamos nossos scripts (`db.py` e `deduplicator.py`) para abrir uma *única conexão TCP* e passá-la como parâmetro para todas as funções (`shared_conn`), reaproveitando o canal de comunicação e agrupando operações em lote.
2. **In-Memory Lookup Caches:** Em vez de consultar o banco a cada vaga para verificar se a empresa ou localização já existiam (SELECT), passamos a carregar todas as empresas de uma vez só na memória (Dicionário Python) no início da tarefa. A busca que antes levava 100ms no banco passou a levar microssegundos na RAM.
3. **Pré-normalização Estática:** Pre-normalizamos strings e dicionários de termos de taxonomia em tempo de compilação/importação, poupando milhões de chamadas unicode desnecessárias por loop.

**Resultado da Otimização:** O tempo de execução da mesma tarefa caiu de **1h34m** para meros **segundos**.

---

## 6. Resultados Reais Obtidos no Supabase

Após o saneamento de datas e a reconstrução das tabelas da Silver Layer, obtivemos a seguinte fotografia dos dados:

| Tabela | Quantidade de Registros | Significado / Status |
| :--- | :---: | :--- |
| **`silver.raw_jobs`** | 1.986 | Total de vagas brutas ingeridas das fontes (Adzuna, Gupy, Jooble, RemoteOK) |
| **`raw_jobs` com Data válida** | 1.986 | **100% das vagas agora possuem data correta!** (Antes era 0%) |
| **`silver.companies`** | 642 | Empresas únicas padronizadas e cacheadas em RAM |
| **`silver.locations`** | 171 | Localidades únicas padronizadas |
| **`silver.jobs` (Únicas)** | **942** | **Vagas ÚNICAS** após limpar todas as duplicatas. O número subiu de 867 para 942 porque agora o critério temporal de 3 dias funciona corretamente! |

### Classificação de Vagas por Área:
* **Business Intelligence (BI):** 112 vagas
* **Data Analytics:** 110 vagas
* **Data Engineering:** 44 vagas
* **Data Science:** 88 vagas
* **Machine Learning / MLOps:** 8 vagas
* **Não classificado (unknown):** 580 vagas

---

**Status Final:** Fase 3 concluída com absoluto sucesso. Os dados estão perfeitamente higienizados e modelados na camada Silver. O pipeline está pronto para plugar a camada Gold e iniciar a modelagem analítica com dbt e geração de dashboards! 🚀
