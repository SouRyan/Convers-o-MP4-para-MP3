@echo off
chcp 65001 >nul
title Gerar executável - Conversor MP4 MP3

cd /d "%~dp0"

echo ========================================
echo   Gerando executável Conversor MP4 MP3
echo ========================================
echo.

REM Verificar se PyInstaller está instalado
python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo Instalando PyInstaller...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo Erro ao instalar PyInstaller.
        pause
        exit /b 1
    )
)

echo.
echo Executando PyInstaller...
pyinstaller --clean --noconfirm build.spec

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   Sucesso!
    echo   Executável em: dist\Conversor-MP4-MP3.exe
    echo ========================================
    echo.
    echo IMPORTANTE: O FFmpeg precisa estar instalado e no PATH
    echo para a conversão funcionar.
    echo.
) else (
    echo.
    echo Erro ao gerar o executável.
)

pause
