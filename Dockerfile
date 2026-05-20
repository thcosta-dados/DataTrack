FROM apache/airflow:2.8.1

# 1. Trocar para o usuario root para poder instalar dependencias de sistema (pacotes apt)
USER root

# Atualizar lista de pacotes e instalar bibliotecas requeridas pelo Chromium (usado no Playwright)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. Voltar para o usuario padrao do Airflow para instalar os pacotes Python
USER airflow

# Instalar dependencias Python do projeto
# (O playwright precisa ser instalado antes de baixarmos o binario do navegador)
RUN pip install --no-cache-dir boto3 requests playwright beautifulsoup4

# Baixar apenas o Chromium (navegador que sera usado pelo Playwright) para economizar espaco
RUN playwright install chromium
