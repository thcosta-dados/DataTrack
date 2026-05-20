# 🎯 DataTrack: Pipeline de Ingestão e Análise de Vagas de Dados

[![Airflow](https://img.shields.io/badge/Apache%20Airflow-017CEE?style=for-the-badge&logo=Apache%20Airflow&logoColor=white)](https://airflow.apache.org/)
[![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=Playwright&logoColor=white)](https://playwright.dev/)

## 📖 Sobre o Projeto
O **DataTrack** é um projeto de Engenharia de Dados de ponta a ponta projetado para mapear, extrair e analisar vagas de trabalho no setor de dados (Data Engineering, Data Science, Data Analytics, etc.) em todo o Brasil e no exterior.

Utilizando a arquitetura **Medallion (Bronze, Silver, Gold)**, o projeto orquestra rotinas diárias de coleta e transformação de dados provenientes de múltiplas APIs e sistemas complexos de RH (Single Page Applications), consolidando tudo em um ambiente analítico limpo e acionável.

---

## 🏗️ Arquitetura e Tecnologias

- **Orquestração**: Apache Airflow
- **Containerização**: Docker & Docker Compose
- **Web Scraping Avançado**: Playwright (Headless Chromium)
- **Extração via API**: Python `requests`
- **Data Lake (Bronze Layer)**: MinIO (S3 Compatible)
- **Data Warehouse (Silver/Gold)**: PostgreSQL *(Em desenvolvimento)*
- **Transformação**: dbt (Data Build Tool) *(Em desenvolvimento)*

---

## 🚀 Progresso do Projeto

O desenvolvimento deste projeto foi dividido em fases metodológicas para simular entregas ágeis do mundo real. Você pode acompanhar a evolução técnica lendo os resumos oficiais de cada etapa:

* ✅ **[Fase 1: Configuração do Airflow e Ingestão da Adzuna (API)](docs/fase1_resumo.md)**
  * Setup da infraestrutura Docker.
  * Desenvolvimento da DAG diária no Airflow.
  * Ingestão de dados bruta no MinIO.

* ✅ **[Fase 2: Expansão da Bronze Layer e Scraping Avançado](docs/fase2_resumo.md)**
  * Scraping de SPA dinâmico da plataforma Gupy usando Playwright.
  * Integração das APIs Jooble e RemoteOK com tratamento defensivo e bypass de WAF.
  * Orquestração e execução assíncrona de 4 extratores em paralelo.

* ⏳ **Fase 3: Transformação e Camada Silver (Em breve)**
  * Limpeza, deduplicação (via `rapidfuzz`) e estruturação dos JSONs brutos no PostgreSQL.

* ⏳ **Fase 4: Camada Gold (Em breve)**
  * Modelagem Star Schema com dbt.

---

## ⚙️ Como Executar Localmente

### Pré-requisitos
* Docker e Docker Compose instalados.

### Passos
1. Clone o repositório:
   ```bash
   git clone https://github.com/thcosta-dados/DataTrack.git
   cd DataTrack
   ```

2. Crie seu arquivo `.env` baseado no exemplo (necessário adicionar suas chaves de API):
   ```bash
   cp .env.example .env
   ```

3. Suba a infraestrutura:
   ```bash
   docker-compose up -d --build
   ```

4. Acesse a interface do Apache Airflow em `http://localhost:8080` (Login Padrão: `admin` / `admin`).
