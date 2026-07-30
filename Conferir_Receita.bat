@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Conferencia de Receita dos Fundos - BWAG

echo ==================================================
echo    CONFERENCIA DE RECEITA DOS FUNDOS - BWAG
echo ==================================================
echo.
echo Dica: antes de rodar, abra o arquivo "informado.csv",
echo cole os valores que o BTG/Bradesco enviaram e salve.
echo.

set /p MES="Digite o mes de competencia (formato AAAA-MM), ex.: 2026-07 : "
echo.

set "INFORMADO="
if exist "informado.csv" set "INFORMADO=--informado informado.csv"

echo Calculando, aguarde...
echo.
python -m conferidor --mes %MES% %INFORMADO% --saida "Relatorio_%MES%.xlsx"

echo.
echo ==================================================
echo  Terminou. Confira a tabela acima.
echo  (Se aparecer algum erro, a mensagem esta acima.)
echo ==================================================
echo.
echo Aperte uma tecla para abrir o relatorio em Excel...
pause >nul
start "" "Relatorio_%MES%.xlsx"
