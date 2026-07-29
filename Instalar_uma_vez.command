#!/bin/bash
# Mac: rode isto apenas UMA VEZ para preparar o computador.
cd "$(dirname "$0")"

echo "=================================================="
echo "  INSTALACAO - rode isto apenas UMA VEZ"
echo "=================================================="
echo
echo "Verificando o Python 3..."
if ! command -v python3 >/dev/null 2>&1; then
  echo
  echo "*** Python 3 nao encontrado. ***"
  echo "Baixe em https://www.python.org/downloads/ , instale e rode este arquivo de novo."
  echo
  read -p "Pressione ENTER para fechar."
  exit 1
fi

echo "Instalando os componentes necessarios..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
  echo
  echo "*** Falha ao instalar os componentes. ***"
  read -p "Pressione ENTER para fechar."
  exit 1
fi

echo
echo "Tudo pronto! Agora e so usar o 'Conferir_Receita.command' todo mes."
read -p "Pressione ENTER para fechar."
