@echo off
chcp 65001 >nul
title Conversor MP4 para MP3

cd /d "%~dp0"

if exist "dist\Conversor-MP4-MP3.exe" (
    start "" "dist\Conversor-MP4-MP3.exe"
) else (
    echo Executável não encontrado.
    echo Execute primeiro: build.bat
    echo.
    pause
)
