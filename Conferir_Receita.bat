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

if exist "informado.csv" (
  echo Comparando com os valores de informado.csv ...
  python -m conferidor --mes %MES% --informado "informado.csv" --saida "Relatorio_%MES%.xlsx"
) else (
  echo Arquivo informado.csv nao encontrado - gerando so o calculo BWAG.
  python -m conferidor --mes %MES% --saida "Relatorio_%MES%.xlsx"
)

if errorlevel 1 (
  echo.
  echo *** Ocorreu um erro. ***
  echo  - Verifique se o Python esta instalado (rode "Instalar_uma_vez.bat").
  echo  - Verifique se digitou o mes no formato AAAA-MM.
  echo.
  pause
  exit /b 1
)

echo.
echo Pronto! Abrindo o relatorio...
start "" "Relatorio_%MES%.xlsx"
