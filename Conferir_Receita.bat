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

REM Procura um Python que funcione: primeiro o "py" (evita o atalho da Store), depois "python".
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
  python --version >nul 2>&1 && set "PY=python"
)

if not defined PY (
  echo *** Python nao esta instalado neste computador. ***
  echo.
  echo   1^) Rode o "Instalar_uma_vez.bat" que esta nesta pasta,
  echo      OU baixe em: https://www.python.org/downloads/
  echo   2^) Na PRIMEIRA tela do instalador, marque "Add Python to PATH".
  echo   3^) Feche esta janela e rode de novo.
  echo.
  echo Aperte uma tecla para fechar.
  pause >nul
  exit /b 1
)

set "INFORMADO="
if exist "informado.csv" set "INFORMADO=--informado informado.csv"

echo Calculando, aguarde...
echo.
%PY% -m conferidor --mes %MES% %INFORMADO% --saida "Relatorio_%MES%.xlsx"

echo.
echo ==================================================
echo  Terminou. Confira a tabela acima.
echo  (Se aparecer algum erro, a mensagem esta acima.)
echo ==================================================
echo.
echo Aperte uma tecla para abrir o relatorio em Excel...
pause >nul
start "" "Relatorio_%MES%.xlsx"
