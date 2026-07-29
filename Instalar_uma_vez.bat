@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Instalacao (uma vez) - Conferencia de Receita BWAG

echo ==================================================
echo   INSTALACAO - rode isto apenas UMA VEZ
echo ==================================================
echo.
echo Verificando o Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo *** Python nao encontrado. ***
  echo 1) Baixe em https://www.python.org/downloads/
  echo 2) Na primeira tela do instalador, marque "Add Python to PATH".
  echo 3) Depois rode este arquivo de novo.
  echo.
  pause
  exit /b 1
)

echo Instalando os componentes necessarios...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo *** Falha ao instalar os componentes. ***
  pause
  exit /b 1
)

echo.
echo Tudo pronto! Agora e so usar o "Conferir_Receita.bat" todo mes.
pause
