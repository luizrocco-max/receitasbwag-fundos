@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Instalacao (uma vez) - Conferencia de Receita BWAG

echo ==================================================
echo   INSTALACAO - rode isto apenas UMA VEZ
echo ==================================================
echo.
echo Procurando o Python...

set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
  python --version >nul 2>&1 && set "PY=python"
)

if not defined PY (
  echo.
  echo *** Python nao encontrado neste computador. ***
  echo.
  echo   1^) Baixe em: https://www.python.org/downloads/
  echo   2^) Na PRIMEIRA tela do instalador, marque "Add Python to PATH".
  echo   3^) Conclua a instalacao e rode este arquivo de novo.
  echo.
  echo Obs.: NAO instale pela Microsoft Store. Se ao digitar "python" abrir
  echo a Store, desligue em: Configuracoes ^> Aplicativos ^> Configuracoes
  echo avancadas de aplicativos ^> Aliases de execucao de aplicativo.
  echo.
  echo Aperte uma tecla para fechar.
  pause >nul
  exit /b 1
)

echo Python encontrado: %PY%
echo Instalando os componentes necessarios...
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt

if errorlevel 1 (
  echo.
  echo *** Falha ao instalar os componentes. Verifique sua internet. ***
  echo Aperte uma tecla para fechar.
  pause >nul
  exit /b 1
)

echo.
echo Tudo pronto! Agora e so usar o "Conferir_Receita.bat" todo mes.
echo.
echo Aperte uma tecla para fechar.
pause >nul
