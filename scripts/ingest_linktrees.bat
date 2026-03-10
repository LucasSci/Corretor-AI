@echo off
REM Ferramenta para ingerir Linktrees - Script Batch
REM Use este arquivo para executar sem precisar de terminal

echo.
echo ========================================
echo  BOT RIVA - Atualizador de Conhecimento
echo ========================================
echo.

cd /d "%~dp0"

echo Iniciando ambiente Python...
call .venv\Scripts\activate.bat

echo.
echo Escolha uma opcao:
echo.
echo 1 - Ingerir TODOS os linktrees (COMPLETO)
echo 2 - Interface interativa (menu)
echo 3 - Apenas show stats
echo.

set /p choice="Opcao (1-3): "

if "%choice%"=="1" (
    echo.
    echo Iniciando ingestao completa de linktrees...
    echo.
    python ingest_linktrees.py
    pause
) else if "%choice%"=="2" (
    echo.
    echo Abrindo menu interativo...
    echo.
    python ingest_linktrees_cli.py
) else if "%choice%"=="3" (
    echo.
    python -c "from knowledge_manager import intelligence_core; print('\n'); stats = intelligence_core.get_bot_stats(); print(stats if stats else 'Nenhum dado')"
    pause
) else (
    echo Opcao invalida!
    pause
)
