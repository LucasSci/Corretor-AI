#!/bin/bash
# Script para ingerir Linktrees - Mac/Linux

echo ""
echo "========================================"
echo "  BOT RIVA - Atualizador de Conhecimento"
echo "========================================"
echo ""

cd "$(dirname "$0")"

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado. Instale python3."
    exit 1
fi

# Ativa ambiente virtual
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "⚠️  Nenhum ambiente virtual encontrado"
fi

echo ""
echo "Escolha uma opção:"
echo ""
echo "1 - Ingerir TODOS os linktrees (COMPLETO)"
echo "2 - Interface interativa (menu)"
echo "3 - Apenas exibir estatísticas"
echo ""

read -p "Opção (1-3): " choice

case $choice in
    1)
        echo ""
        echo "Iniciando ingestão completa de linktrees..."
        echo ""
        python3 ingest_linktrees.py
        ;;
    2)
        echo ""
        echo "Abrindo menu interativo..."
        echo ""
        python3 ingest_linktrees_cli.py
        ;;
    3)
        echo ""
        python3 -c "from knowledge_manager import intelligence_core; print('\n'); stats = intelligence_core.get_bot_stats(); print(stats if stats else 'Nenhum dado')"
        ;;
    *)
        echo "Opção inválida!"
        exit 1
        ;;
esac

echo ""
