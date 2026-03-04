@echo off
chcp 65001 >nul
title Conversor MP4 para MP3

cd /d "%~dp0"

echo Iniciando Conversor MP4 para MP3...
echo.

python gui.py
if %errorlevel% neq 0 (
    echo.
    echo Erro: Python nao encontrado ou gui.py nao existe.
    echo Instale o Python e certifique-se de estar na pasta do projeto.
    pause
)
