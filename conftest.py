# conftest.py
# Configuracao global do pytest para o projeto DataTrack.
#
# O pytest usa este arquivo para configurar o ambiente de teste ANTES
# de rodar qualquer test file. Aqui adicionamos o diretorio plugins/
# ao sys.path para que os imports como "from silver.db import ..."
# funcionem sem precisar instalar o pacote.

import sys
import os

# Adiciona plugins/ ao path de busca do Python
# Equivale a dizer: "procure modulos aqui tambem"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "plugins"))
