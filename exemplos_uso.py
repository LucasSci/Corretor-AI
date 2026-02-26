#!/usr/bin/env python3
"""
📚 Exemplos Práticos de Uso da Base de Conhecimento
Demonstra como consumir dados do arquivo JSONL
"""

import json
import os


# ============================================================================
# EXEMPLO 1: Leitura Simples
# ============================================================================

def exemplo_1_leitura_simples():
    """Lê o arquivo JSONL e mostra os primeiros documentos."""
    print("\n" + "="*70)
    print("EXEMPLO 1: Leitura Simples do JSONL")
    print("="*70 + "\n")
    
    arquivo = "data/base_conhecimento.jsonl"
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        print("Execute primeiro: python ingest.py")
        return
    
    print(f"Mostrando primeiros 3 documentos:\n")
    
    with open(arquivo, 'r', encoding='utf-8') as f:
        for i, linha in enumerate(f):
            if i >= 3:
                break
            
            doc = json.loads(linha)
            print(f"🏠 Documento #{i+1}")
            print(f"   ID: {doc['id']}")
            print(f"   Site: {doc['site_origem']}")
            print(f"   Arquivo: {doc['arquivo']}")
            print(f"   Texto (primeiros 150 chars):")
            print(f"   {doc['texto'][:150]}...")
            print()


# ============================================================================
# EXEMPLO 2: Filtrar por Site
# ============================================================================

def exemplo_2_filtrar_por_site(site_slug="apogeu_barra_linktree"):
    """Filtra documentos de um site específico."""
    print("\n" + "="*70)
    print(f"EXEMPLO 2: Filtrar por Site ({site_slug})")
    print("="*70 + "\n")
    
    arquivo = "data/base_conhecimento.jsonl"
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return
    
    # Contar documentos
    documentos = []
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            doc = json.loads(linha)
            if doc.get('site_slug') == site_slug:
                documentos.append(doc)
    
    print(f"✅ Encontrados {len(documentos)} documentos do site '{site_slug}'\n")
    
    # Mostrar alguns
    for doc in documentos[:2]:
        print(f"📄 {doc['arquivo']} (Chunk #{doc.get('chunk_index', 0)})")
        print(f"   {doc['texto'][:120]}...\n")


# ============================================================================
# EXEMPLO 3: Busca por Palavra-chave
# ============================================================================

def exemplo_3_buscar_palavra_chave(palavra="área"):
    """Busca simples por substring."""
    print("\n" + "="*70)
    print(f"EXEMPLO 3: Buscar por Palavra-chave ('{palavra}')")
    print("="*70 + "\n")
    
    arquivo = "data/base_conhecimento.jsonl"
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return
    
    # Buscar
    resultados = []
    palavra_lower = palavra.lower()
    
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            doc = json.loads(linha)
            if palavra_lower in doc.get('texto', '').lower():
                resultados.append(doc)
    
    print(f"✅ Encontrados {len(resultados)} documentos com '{palavra}'\n")
    
    # Mostrar primeiros 3
    for i, doc in enumerate(resultados[:3], 1):
        print(f"{i}. 🏢 {doc['site_origem']} ({doc['arquivo']})")
        
        # Highlight da palavra no texto
        texto = doc['texto']
        indice = texto.lower().find(palavra_lower)
        if indice != -1:
            inicio = max(0, indice - 50)
            fim = min(len(texto), indice + len(palavra) + 50)
            contexto = texto[inicio:fim]
            # Destaca a palavra
            contexto = contexto.replace(palavra, f">>> {palavra.upper()} <<<")
            print(f"   ...{contexto}...")
        print()


# ============================================================================
# EXEMPLO 4: Estatísticas
# ============================================================================

def exemplo_4_estatisticas():
    """Gera estatísticas sobre a base de conhecimento."""
    print("\n" + "="*70)
    print("EXEMPLO 4: Estatísticas da Base")
    print("="*70 + "\n")
    
    arquivo = "data/base_conhecimento.jsonl"
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return
    
    # Coletar stats
    stats = {
        'total_docs': 0,
        'total_chars': 0,
        'sites': {},
        'arquivos': set(),
        'tipos': {}
    }
    
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            doc = json.loads(linha)
            
            stats['total_docs'] += 1
            stats['total_chars'] += len(doc.get('texto', ''))
            
            site = doc.get('site_origem', 'Unknown')
            if site not in stats['sites']:
                stats['sites'][site] = 0
            stats['sites'][site] += 1
            
            stats['arquivos'].add(doc.get('arquivo', ''))
            
            tipo = doc.get('type', 'chunk')
            if tipo not in stats['tipos']:
                stats['tipos'][tipo] = 0
            stats['tipos'][tipo] += 1
    
    # Exibir stats
    print(f"📊 ESTATÍSTICAS GERAIS")
    print(f"   Total de documentos: {stats['total_docs']:,}")
    print(f"   Total de caracteres: {stats['total_chars']:,}")
    print(f"   Média por documento: {stats['total_chars'] // max(1, stats['total_docs']):,} chars")
    print(f"   Arquivos únicos: {len(stats['arquivos'])}")
    
    print(f"\n🏢 POR SITE")
    for site, count in sorted(stats['sites'].items(), key=lambda x: x[1], reverse=True):
        pct = (count / stats['total_docs'] * 100) if stats['total_docs'] > 0 else 0
        print(f"   • {site}: {count:,} documentos ({pct:.1f}%)")
    
    print(f"\n🏷️  TIPOS DE DOCUMENTO")
    for tipo, count in sorted(stats['tipos'].items(), key=lambda x: x[1], reverse=True):
        print(f"   • {tipo}: {count:,}")


# ============================================================================
# EXEMPLO 5: Converter para CSV
# ============================================================================

def exemplo_5_exportar_csv():
    """Exporta JSONL para CSV (útil para análise em Excel)."""
    print("\n" + "="*70)
    print("EXEMPLO 5: Exportar para CSV")
    print("="*70 + "\n")
    
    import csv
    
    arquivo_jsonl = "data/base_conhecimento.jsonl"
    arquivo_csv = "data/base_conhecimento.csv"
    
    if not os.path.exists(arquivo_jsonl):
        print(f"❌ Arquivo não encontrado: {arquivo_jsonl}")
        return
    
    print(f"Exportando para {arquivo_csv}...")
    
    # Ler JSONL e escrever CSV
    linhas_exportadas = 0
    with open(arquivo_jsonl, 'r', encoding='utf-8') as f_in, \
         open(arquivo_csv, 'w', encoding='utf-8', newline='') as f_out:
        
        writer = None
        for linha in f_in:
            doc = json.loads(linha)
            
            # Truncar texto para não ficar gigante no CSV
            doc['texto'] = doc.get('texto', '')[:200] + "..."
            
            if writer is None:
                writer = csv.DictWriter(f_out, fieldnames=doc.keys())
                writer.writeheader()
            
            writer.writerow(doc)
            linhas_exportadas += 1
    
    print(f"✅ {linhas_exportadas} linhas exportadas para {arquivo_csv}")
    print(f"   Abra em Excel ou Google Sheets para análise")


# ============================================================================
# EXEMPLO 6: Deduplicação
# ============================================================================

def exemplo_6_remover_duplicatas():
    """Remove documentos duplicados (baseado em SHA256)."""
    print("\n" + "="*70)
    print("EXEMPLO 6: Remover Duplicatas")
    print("="*70 + "\n")
    
    arquivo = "data/base_conhecimento.jsonl"
    arquivo_dedup = "data/base_conhecimento_dedup.jsonl"
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return
    
    print("Procurando e removendo duplicatas...")
    
    shas_vistas = set()
    linhas_unicas = 0
    linhas_duplicadas = 0
    
    with open(arquivo, 'r', encoding='utf-8') as f_in, \
         open(arquivo_dedup, 'w', encoding='utf-8') as f_out:
        
        for linha in f_in:
            doc = json.loads(linha)
            sha = doc.get('sha256', 'unknown')
            
            if sha not in shas_vistas:
                shas_vistas.add(sha)
                f_out.write(json.dumps(doc, ensure_ascii=False) + '\n')
                linhas_unicas += 1
            else:
                linhas_duplicadas += 1
    
    print(f"✅ Processamento concluído!")
    print(f"   Linhas únicas: {linhas_unicas}")
    print(f"   Duplicatas removidas: {linhas_duplicadas}")
    print(f"   Arquivo: {arquivo_dedup}")


# ============================================================================
# EXEMPLO 7: Listar todos os Sites
# ============================================================================

def exemplo_7_listar_sites():
    """Lista todos os sites/empreendimentos na base."""
    print("\n" + "="*70)
    print("EXEMPLO 7: Listar Todos os Sites")
    print("="*70 + "\n")
    
    arquivo = "data/base_conhecimento.jsonl"
    
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}")
        return
    
    sites = set()
    site_slugs = set()
    
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            doc = json.loads(linha)
            sites.add(doc.get('site_origem'))
            site_slugs.add(doc.get('site_slug'))
    
    print(f"🏢 Total de {len(sites)} empreendimentos/sites:\n")
    
    for i, site in enumerate(sorted(sites), 1):
        print(f"   {i}. {site}")


# ============================================================================
# MENU PRINCIPAL
# ============================================================================

def menu():
    """Menu interativo."""
    opcoes = {
        '1': ('Leitura Simples', exemplo_1_leitura_simples),
        '2': ('Filtrar por Site', exemplo_2_filtrar_por_site),
        '3': ('Buscar por Palavra', exemplo_3_buscar_palavra_chave),
        '4': ('Estatísticas', exemplo_4_estatisticas),
        '5': ('Exportar para CSV', exemplo_5_exportar_csv),
        '6': ('Remover Duplicatas', exemplo_6_remover_duplicatas),
        '7': ('Listar Sites', exemplo_7_listar_sites),
        '0': ('Sair', None)
    }
    
    while True:
        print("\n" + "="*70)
        print("📚 EXEMPLOS DE USO - BASE DE CONHECIMENTO")
        print("="*70)
        
        for key, (desc, _) in opcoes.items():
            if key != '0':
                print(f"   {key} - {desc}")
        print(f"   {' ' if len(opcoes) < 10 else ''}0 - Sair")
        
        escolha = input("\nEscolha uma opção (0-7): ").strip()
        
        if escolha == '0':
            print("\nAté logo! 👋\n")
            break
        
        if escolha in opcoes:
            desc, funcao = opcoes[escolha]
            if funcao:
                try:
                    funcao()
                except Exception as e:
                    print(f"\n❌ Erro: {e}")
            else:
                break
        else:
            print("\n❌ Opção inválida! Tente novamente.")


def main():
    """Executa todos os exemplos (modo automático) ou abre menu."""
    
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        # Modo automático: executar todos os exemplos
        print("\n🚀 Executando todos os exemplos...\n")
        exemplo_1_leitura_simples()
        exemplo_2_filtrar_por_site("apogeu_barra_linktree")
        exemplo_3_buscar_palavra_chave("área")
        exemplo_4_estatisticas()
        exemplo_7_listar_sites()
    else:
        # Modo interativo
        menu()


if __name__ == "__main__":
    main()
