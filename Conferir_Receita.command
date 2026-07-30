#!/bin/bash
# Atalho para Mac: duplo-clique para rodar a conferencia.
cd "$(dirname "$0")"

echo "=================================================="
echo "   CONFERENCIA DE RECEITA DOS FUNDOS - BWAG"
echo "=================================================="
echo
echo "Dica: antes de rodar, abra o arquivo 'informado.csv',"
echo "cole os valores que o BTG/Bradesco enviaram e salve."
echo
read -p "Digite o mes de competencia (formato AAAA-MM), ex.: 2026-07 : " MES
echo

if [ -f "informado.csv" ]; then
  echo "Comparando com os valores de informado.csv ..."
  python3 -m conferidor --mes "$MES" --informado "informado.csv" --saida "Relatorio_$MES.xlsx"
else
  echo "Arquivo informado.csv nao encontrado - gerando so o calculo BWAG."
  python3 -m conferidor --mes "$MES" --saida "Relatorio_$MES.xlsx"
fi

if [ $? -ne 0 ]; then
  echo
  echo "*** Ocorreu um erro. ***"
  echo " - Verifique se o Python 3 esta instalado (rode 'Instalar_uma_vez.command')."
  echo " - Verifique se digitou o mes no formato AAAA-MM."
  echo
  read -p "Pressione ENTER para fechar."
  exit 1
fi

echo
echo "Pronto! O relatorio foi gerado e aberto: Relatorio_$MES.xlsx"
open "Relatorio_$MES.xlsx"
echo
read -p "Confira a tabela acima. Pressione ENTER para fechar esta janela."
