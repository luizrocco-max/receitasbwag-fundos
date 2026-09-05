@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Dashboard de Receita - BWAG

echo ==================================================
echo    DASHBOARD DE RECEITA DOS FUNDOS - BWAG
echo ==================================================
echo.
echo Gera uma pagina (HTML) com a evolucao mensal e a
echo contribuicao por fundo, do inicio do ano ate o mes anterior.
echo.
set /p ANO="Digite o ano (ex.: 2026) ou so aperte Enter para o ano atual: "

set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
  python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo *** Python nao esta instalado. Rode o "Instalar_uma_vez.bat". ***
  echo Aperte uma tecla para fechar.
  pause >nul
  exit /b 1
)

set "ARQ=Dashboard_Receita.html"
if not "%ANO%"=="" set "ARQ=Dashboard_Receita_%ANO%.html"

echo.
echo Calculando todos os meses (a primeira vez pode levar alguns minutos)...
echo.
if "%ANO%"=="" (
  %PY% -m conferidor --dashboard --saida "%ARQ%"
) else (
  %PY% -m conferidor --dashboard --ano %ANO% --saida "%ARQ%"
)

echo.
echo ==================================================
echo  Terminou. O arquivo gerado foi: %ARQ%
echo  (Se aparecer algum erro, a mensagem esta acima.)
echo ==================================================
echo.
echo Aperte uma tecla para abrir o dashboard no navegador...
pause >nul
start "" "%ARQ%"
