#!/usr/bin/env python3
"""
📊 Script de Validação e Testes
Valida se a base de conhecimento foi gerada corretamente
"""

import json
import os
from pathlib import Path


def validar_estrutura_dados():
    """Valida se os arquivos esperados foram criados."""
    print("\n" + "="*70)
    print("🔍 VALIDAÇÃO 1: Estrutura de Diretórios")
    print("="*70)
    
    esperados = [
        "data/base_conhecimento.jsonl",
        "data/ingest_summary.json",
        "data/raw",
        "data/extracted"
    ]
    
    todos_existem = True
    for caminho in esperados:
        existe = os.path.exists(caminho)
        status = "✅" if existe else "❌"
        print(f"{status} {caminho}")
        if not existe:
            todos_existem = False
    
    return todos_existem


def validar_jsonl():
    """Valida se o arquivo JSONL está bem formado."""
    print("\n" + "="*70)
    print("🔍 VALIDAÇÃO 2: Integridade do JSONL")
    print("="*70)
    
    arquivo = "data/base_conhecimento.jsonl"
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return False
    
    total_linhas = 0
    erros = 0
    total_chars = 0
    sites_unicos = set()
    tipos_unicos = set()
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            for num_linha, linha in enumerate(f, 1):
                try:
                    doc = json.loads(linha)
                    total_linhas += 1
                    total_chars += len(doc.get('texto', ''))
                    sites_unicos.add(doc.get('site_origem', 'Unknown'))
                    tipos_unicos.add(doc.get('type', 'chunk'))
                except json.JSONDecodeError as e:
                    erros += 1
                    if erros <= 5:
                        print(f"   ❌ Erro JSON na linha {num_linha}: {str(e)[:50]}")
        
        print(f"\n✅ Arquivo válido!")
        print(f"   📄 Total de documentos: {total_linhas:,}")
        print(f"   📊 Total de caracteres: {total_chars:,}")
        print(f"   🏢 Empreendimentos: {len(sites_unicos)}")
        print(f"   🏷️  Tipos únicos: {len(tipos_unicos)}")
        
        if erros > 0:
            print(f"\n⚠️  {erros} linhas com erro JSON")
            return False
        
        return total_linhas > 0
        
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        return False


def analisar_conteudo():
    """Analisa o conteúdo da base de conhecimento."""
    print("\n" + "="*70)
    print("🔍 VALIDAÇÃO 3: Análise de Conteúdo")
    print("="*70)
    
    arquivo = "data/base_conhecimento.jsonl"
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return False
    
    stats = {
        'por_site': {},
        'tamanho_medio_texto': 0,
        'chunks_por_site': {},
        'urls_unicas': set(),
        'arquivos_unicos': set()
    }
    
    total_linhas = 0
    
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            doc = json.loads(linha)
            total_linhas += 1
            
            site = doc.get('site_origem', 'Unknown')
            if site not in stats['por_site']:
                stats['por_site'][site] = 0
            stats['por_site'][site] += 1
            
            stats['tamanho_medio_texto'] += len(doc.get('texto', ''))
            stats['urls_unicas'].add(doc.get('source_url', ''))
            stats['arquivos_unicos'].add(doc.get('arquivo', ''))
    
    if total_linhas > 0:
        stats['tamanho_medio_texto'] //= total_linhas
    
    print(f"\n📊 Estatísticas Gerais:")
    print(f"   Total de documentos: {total_linhas:,}")
    print(f"   Tamanho médio de texto: {stats['tamanho_medio_texto']:,} chars")
    print(f"   URLs únicas: {len(stats['urls_unicas'])}")
    print(f"   Arquivos únicos: {len(stats['arquivos_unicos'])}")
    
    print(f"\n🏢 Distribuição por Site:")
    for site, count in sorted(stats['por_site'].items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_linhas * 100) if total_linhas > 0 else 0
        print(f"   ├─ {site}: {count:,} docs ({pct:.1f}%)")
    
    print(f"\n✅ Análise concluída!")
    return True


def amostrar_documentos(n=3):
    """Mostra amostra de documentos da base."""
    print("\n" + "="*70)
    print("🔍 VALIDAÇÃO 4: Amostra de Documentos")
    print("="*70)
    
    arquivo = "data/base_conhecimento.jsonl"
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return False
    
    print(f"\nMostrando {n} primeiros documentos:\n")
    
    with open(arquivo, 'r', encoding='utf-8') as f:
        for i, linha in enumerate(f):
            if i >= n:
                break
            
            doc = json.loads(linha)
            print(f"📌 Documento {i+1}")
            print(f"   ID: {doc.get('id')}")
            print(f"   Site: {doc.get('site_origem')}")
            print(f"   Arquivo: {doc.get('arquivo')}")
            print(f"   Tipo: {doc.get('type', 'chunk')}")
            print(f"   Tamanho: {len(doc.get('texto', '')):,} caracteres")
            
            # Mostra preview do texto
            texto = doc.get('texto', '')[:200]
            if len(doc.get('texto', '')) > 200:
                texto += "..."
            print(f"   Preview: {texto}")
            print()
    
    return True


def validar_summary():
    """Valida o arquivo de sumário."""
    print("\n" + "="*70)
    print("🔍 VALIDAÇÃO 5: Arquivo de Sumário")
    print("="*70)
    
    arquivo = "data/ingest_summary.json"
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return False
    
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        if isinstance(summary, list):
            total = len(summary)
            sucesso = sum(1 for item in summary if item.get('status') == 'sucesso')
            erros = sum(1 for item in summary if item.get('status') == 'erro')
            
            print(f"\n✅ Sumário válido!")
            print(f"   Total de PDFs: {total}")
            print(f"   ✅ Sucesso: {sucesso}")
            print(f"   ❌ Erros: {erros}")
            
            if erros > 0:
                print(f"\n⚠️  Erros encontrados:")
                for item in summary:
                    if item.get('status') == 'erro':
                        print(f"   • {item.get('arquivo')}: {item.get('erro')[:60]}")
            
            return True
        else:
            print(f"❌ Formato inesperado do sumário")
            return False
            
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao decodificar JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def teste_leitura_programatica():
    """Testa se é possível ler o arquivo programaticamente."""
    print("\n" + "="*70)
    print("🔍 VALIDAÇÃO 6: Leitura Programática")
    print("="*70)
    
    arquivo = "data/base_conhecimento.jsonl"
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return False
    
    try:
        # Teste 1: Ler todas as linhas
        print("\n🧪 Teste 1: Lendo todas as linhas...")
        linhas = 0
        with open(arquivo, 'r', encoding='utf-8') as f:
            for linha in f:
                json.loads(linha)
                linhas += 1
        print(f"   ✅ {linhas:,} linhas lidas com sucesso")
        
        # Teste 2: Filtrar por site
        print("\n🧪 Teste 2: Filtrando por site...")
        sites_encontrados = {}
        with open(arquivo, 'r', encoding='utf-8') as f:
            for linha in f:
                doc = json.loads(linha)
                site = doc.get('site_origem')
                if site:
                    if site not in sites_encontrados:
                        sites_encontrados[site] = 0
                    sites_encontrados[site] += 1
        
        print(f"   ✅ {len(sites_encontrados)} sites únicos encontrados")
        for site, count in list(sites_encontrados.items())[:3]:
            print(f"      • {site}: {count} documentos")
        
        # Teste 3: Buscar palavra-chave
        print("\n🧪 Teste 3: Busca por palavra-chave...")
        palavra = "área"
        encontrados = 0
        with open(arquivo, 'r', encoding='utf-8') as f:
            for linha in f:
                doc = json.loads(linha)
                if palavra.lower() in doc.get('texto', '').lower():
                    encontrados += 1
        print(f"   ✅ {encontrados} documentos contêm '{palavra}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def relatorio_final(resultados):
    """Gera relatório final de validação."""
    print("\n" + "="*70)
    print("📋 RELATÓRIO FINAL")
    print("="*70)
    
    total_testes = len(resultados)
    testes_passados = sum(resultados.values())
    taxa_sucesso = (testes_passados / total_testes * 100) if total_testes > 0 else 0
    
    print(f"\n✅ Testes passados: {testes_passados}/{total_testes}")
    print(f"📊 Taxa de sucesso: {taxa_sucesso:.1f}%")
    
    if taxa_sucesso == 100:
        print(f"\n🎉 Todas as validações passaram! Base pronta para usar.")
        print(f"   Próximo step: Indexar em ChromaDB/Pinecone")
    else:
        print(f"\n⚠️  Some validações falharam. Revisar logs acima.")
    
    print("\n" + "="*70 + "\n")


def main():
    """Executa todas as validações."""
    print("\n" + "🚀 "*35)
    print("   VALIDAÇÃO DA BASE DE CONHECIMENTO")
    print("🚀 "*35)
    
    resultados = {}
    
    # Executar testes
    resultados['Estrutura'] = validar_estrutura_dados()
    resultados['JSONL'] = validar_jsonl()
    resultados['Conteúdo'] = analisar_conteudo()
    resultados['Amostra'] = amostrar_documentos(3)
    resultados['Sumário'] = validar_summary()
    resultados['Leitura'] = teste_leitura_programatica()
    
    # Relatório final
    relatorio_final(resultados)


if __name__ == "__main__":
    main()
