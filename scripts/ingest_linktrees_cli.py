#!/usr/bin/env python
"""
🚀 Ferramenta Simples de Ingestão de Linktrees
Interface interativa para atualizar conhecimento do bot
"""

import os
import sys
from ingest_linktrees import LinktreeIngester
import time
from datetime import datetime


def clear_screen():
    """Limpa a tela do console"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Imprime cabeçalho"""
    print("\n" + "="*80)
    print("🤖 ATUALIZADOR DE CONHECIMENTO - BOT RIVA VENDAS")
    print("="*80 + "\n")


def menu_principal():
    """Menu principal"""
    clear_screen()
    print_header()
    
    print("Escolha uma opção:\n")
    print("1️⃣  Ingerir TODOS os linktrees (completo)")
    print("2️⃣  Ingerir apenas um linktree")
    print("3️⃣  Ingerir com profundidade customizada")
    print("4️⃣  Visualizar estatísticas")
    print("5️⃣  Sair\n")
    
    choice = input("Qual opção? (1-5): ").strip()
    return choice


def opcao_1_ingerir_todos():
    """Ingerir todos os linktrees"""
    clear_screen()
    print_header()
    
    print("📥 INGERINDO TODOS OS LINKTREES")
    print("-" * 80)
    print("\nIsso irá raspar:")
    print("  1. https://linktr.ee/rivaincorporadorario")
    print("  2. https://linktr.ee/marinebarra.vendas")
    print("  3. https://linktr.ee/duetbarra.vendas")
    print("\nTempo estimado: 5-10 minutos\n")
    
    confirma = input("Deseja continuar? (s/n): ").strip().lower()
    
    if confirma != 's':
        print("❌ Operação cancelada")
        time.sleep(2)
        return
    
    linktrees = [
        "https://linktr.ee/rivaincorporadorario",
        "https://linktr.ee/marinebarra.vendas",
        "https://linktr.ee/duetbarra.vendas"
    ]
    
    ingester = LinktreeIngester(max_depth=2, timeout=20, max_retries=3)
    
    print("\n" + "="*80)
    print(f"🚀 INICIADO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    for linktree in linktrees:
        try:
            ingester.ingest_linktree(linktree)
        except Exception as e:
            print(f"\n❌ Erro: {str(e)}\n")
    
    ingester.print_summary()
    
    print(f"\n✅ CONCLUÍDO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n💾 Arquivos salvos em: ./conhecimento_ia/")
    print("🤖 Bot agora conhece todos esses sites!\n")


def opcao_2_ingerir_um():
    """Ingerir um linktree específico"""
    clear_screen()
    print_header()
    
    print("Qual linktree deseja ingerir?\n")
    print("1️⃣  Riva Incorporadora")
    print("   https://linktr.ee/rivaincorporadorario")
    print("\n2️⃣  Marine Barra Vendas")
    print("   https://linktr.ee/marinebarra.vendas")
    print("\n3️⃣  Duet Barra Vendas")
    print("   https://linktr.ee/duetbarra.vendas")
    print("\n4️⃣  URL customizada")
    print("\n5️⃣  Voltar\n")
    
    choice = input("Escolha (1-5): ").strip()
    
    urls = {
        '1': "https://linktr.ee/rivaincorporadorario",
        '2': "https://linktr.ee/marinebarra.vendas",
        '3': "https://linktr.ee/duetbarra.vendas",
    }
    
    if choice == '4':
        url = input("Digite a URL: ").strip()
    elif choice in urls:
        url = urls[choice]
    else:
        print("❌ Opção inválida")
        time.sleep(2)
        return
    
    print(f"\n✅ Processando: {url}")
    confirma = input("Continuar? (s/n): ").strip().lower()
    
    if confirma != 's':
        print("❌ Operação cancelada")
        time.sleep(2)
        return
    
    ingester = LinktreeIngester(max_depth=2, timeout=10)
    
    print("\n" + "="*80)
    print(f"🚀 INICIADO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    try:
        ingester.ingest_linktree(url)
        ingester.print_summary()
        print(f"\n✅ CONCLUÍDO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}\n")
    
    input("Pressione Enter para voltar...")


def opcao_3_customizado():
    """Ingestão com profundidade customizada"""
    clear_screen()
    print_header()
    
    print("⚙️ INGESTÃO CUSTOMIZADA\n")
    
    url = input("URL a ingerir (ou Enter para usar Riva Incorporadora): ").strip()
    if not url:
        url = "https://linktr.ee/rivaincorporadorario"
    
    print(f"\nProfundidade (recomendado: 2):")
    print("  1 = apenas first level")
    print("  2 = profundidade padrão (recomendado)")
    print("  3 = muito profundo (pode demorar muito)")
    
    try:
        depth = int(input("\nProfundidade: ").strip() or "2")
    except:
        depth = 2
    
    try:
        timeout = int(input("Timeout por página em segundos (padrão: 20): ").strip() or "20")
    except:
        timeout = 10
    
    try:
        max_retries = int(input("Número de tentativas em caso de falha (padrão: 3): ").strip() or "3")
    except:
        max_retries = 3
    
    print(f"\n✅ Configuração:")
    print(f"   URL: {url}")
    print(f"   Profundidade: {depth}")
    print(f"   Timeout: {timeout}s")
    print(f"   Retries: {max_retries}")
    
    confirma = input("\nContinuar? (s/n): ").strip().lower()
    
    if confirma != 's':
        print("❌ Cancelado")
        time.sleep(2)
        return
    
    ingester = LinktreeIngester(max_depth=depth, timeout=timeout, max_retries=max_retries)
    
    print("\n" + "="*80)
    print(f"🚀 INICIADO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    try:
        ingester.ingest_linktree(url)
        ingester.print_summary()
        print(f"\n✅ CONCLUÍDO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}\n")
    
    input("Pressione Enter para voltar...")


def opcao_4_stats():
    """Visualizar estatísticas"""
    clear_screen()
    print_header()
    
    print("📊 ESTATÍSTICAS DO BOT\n")
    
    try:
        from knowledge_manager import intelligence_core
        
        stats = intelligence_core.get_bot_stats()
        
        if stats:
            print("Conhecimento Acumulado:")
            print("-" * 80)
            
            if 'total_documentos' in stats:
                print(f"📚 Total de documentos: {stats['total_documentos']}")
            
            if 'total_interacoes' in stats:
                print(f"💬 Total de interações: {stats['total_interacoes']}")
            
            if 'clientes_conhecidos' in stats:
                print(f"👥 Clientes conhecidos: {stats['clientes_conhecidos']}")
            
            if 'especialidades' in stats:
                print(f"🎯 Especialidades identificadas: {stats['especialidades']}")
            
            print("\n✅ Estatísticas carregadas com sucesso!")
        else:
            print("⚠️ Nenhuma estatística disponível ainda")
            print("Execute a ingestão de linktrees para popular dados")
    
    except ImportError:
        print("❌ Erro ao carregar conhecimento")
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
    
    print("\n")
    input("Pressione Enter para voltar...")


def main():
    """Loop principal"""
    while True:
        choice = menu_principal()
        
        if choice == '1':
            opcao_1_ingerir_todos()
        elif choice == '2':
            opcao_2_ingerir_um()
        elif choice == '3':
            opcao_3_customizado()
        elif choice == '4':
            opcao_4_stats()
        elif choice == '5':
            print("\n👋 Até logo!")
            sys.exit(0)
        else:
            print("❌ Opção inválida")
            time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operação interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}")
        input("Pressione Enter para sair...")
        sys.exit(1)
