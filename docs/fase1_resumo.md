# Resumo da Fase 1 — Fundacao e Ingestao via API

## Status: Concluida em 20/05/2026

## O que foi construido nesta fase

### Infraestrutura base (Docker Compose)
- `docker-compose.yml` orquestrando 5 servicos: PostgreSQL 15, MinIO, Airflow Webserver, Airflow Scheduler, Airflow Init
- `Dockerfile` customizado com dependencias (boto3, requests) embutidas na imagem — eliminou o `_PIP_ADDITIONAL_REQUIREMENTS` que reinstalava tudo a cada restart
- `.env` com variaveis sensiveis (credenciais, chaves de API) protegido pelo `.gitignore`
- `.env.example` como template para novos devs

### Seguranca
- FERNET_KEY gerada e configurada para criptografar credenciais armazenadas no banco do Airflow
- airflow-init corrigido para herdar variaveis de ambiente do bloco common (DB connection, FERNET_KEY)

### Extrator Adzuna (Camada Bronze)
- `plugins/adzuna_extractor.py` com 3 funcoes:
  - `extract_adzuna_jobs()` — funcao principal chamada pela DAG
  - `_fetch_all_pages()` — paginacao automatica (teto de 5 paginas por termo)
  - `_upload_to_minio()` — upload para o Data Lake (MinIO)
- Filtro temporal: `max_days_old=7` (somente vagas da ultima semana)
- 8 termos de busca cobrindo toda a area de dados (engineering, analytics, science, BI, ML)
- Particionamento por data: `adzuna/YYYY-MM-DD/raw_jobs.json`
- Consumo de API: 40 calls/dia no pior caso (free tier: 250/dia)

### Orquestracao com Airflow
- DAG `datatrack_daily_pipeline` com schedule `0 7 * * *` (diario as 7h)
- Task 1 (`extract_adzuna`): executa o extrator
- Task 2 (`validate_bronze`): valida via XCom se a extracao gerou arquivo valido

### Organizacao do projeto
- Estrutura de pastas consolidada (eliminou duplicatas entre DataTrack/ e DataTrack/DataTrack/)
- `.git` movido para raiz do workspace
- Makefile com targets: build, up, down, restart, clean

### Decisoes tecnicas tomadas
| Decisao | Escolha | Por que |
|---------|---------|---------|
| Filtro temporal | 7 dias | Equilibrio entre cobertura do usuario final e eficiencia de API |
| Paginacao | Max 5 paginas/termo | Captura todas as vagas sem estourar cota do free tier |
| Dockerfile | Imagem customizada | Container sobe em segundos, funciona sem internet |
| FERNET_KEY | Chave real no .env | Credenciais criptografadas no banco do Airflow |

## Historico acumulado
- **Fase 1**: Infraestrutura Docker + extrator Adzuna com paginacao e filtro de 7 dias + DAG basica com validacao Bronze

## Stack utilizada ate agora
| Tecnologia | Fase introduzida | Uso |
|------------|-----------------|-----|
| Docker Compose | Fase 1 | Orquestracao dos containers locais |
| Apache Airflow 2.8.1 | Fase 1 | Agendamento e orquestracao de tasks |
| PostgreSQL 15 | Fase 1 | Backend do Airflow |
| MinIO | Fase 1 | Data Lake local (equivalente ao S3) |
| Python (boto3, requests) | Fase 1 | Extracao e upload de dados |

## Proxima fase: Fase 2 — Multiplas Fontes
- Construir robo de Web Scraping com Playwright para extrair vagas da Gupy (fonte sem API)
- Adicionar extractors do Jooble e RemoteOK
- Paralelizar os 4 extractors na DAG
- Implementar validate_bronze que valida todas as fontes
- Referencia: secao 17 (Roadmap, Fase 2) do datatrack_referencia_main.md

## Filtragens planejadas para fases futuras (Silver/Gold)
- Area (5 categorias), Senioridade, Modalidade (remoto/hibrido/presencial)
- Localizacao, Skills, Empresa, Fonte
- Recencia (24h / 3 dias / 7 dias) — filtro temporal para usuario final
- Porte da empresa (grande/media/pequena) — derivado do volume de postagens

## Como rodar o projeto no estado atual
1. Crie o `.env` na raiz usando `.env.example` como base (preencha as chaves da Adzuna)
2. Construa e inicie: `docker-compose up -d --build`
3. Acesse o Airflow: `http://localhost:8080` (admin/admin)
4. Despause e execute a DAG `datatrack_daily_pipeline`
5. Acesse o MinIO: `http://localhost:9001` (admin/adminpassword) para verificar o JSON
