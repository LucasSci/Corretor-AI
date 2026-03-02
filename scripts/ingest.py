import asyncio
import re
import io
import httpx
import fitz
import hashlib
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


# ============================================================================
# SEÇÃO 1: FUNÇÕES DE LIMPEZA E PROCESSAMENTO DE TEXTO
# ============================================================================

def limpar_texto(texto):
    """Limpa quebras e espaços excessivos."""
    if not texto:
        return ""
    # Remove múltiplos espaços/quebras e normalize
    s = re.sub(r"\s+", " ", texto)
    return s.strip()


def limpar_conteudo_html(html_content):
    """Extrai apenas o texto útil, removendo elementos de interface como menus, rodapés e scripts.
    
    Esta função é essencial para preparar dados limpos para uma base de conhecimento (Vector DB/RAG).
    Remove ruído que poderia comprometer a qualidade do embedding.
    """
    if not html_content:
        return ""
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove elementos que não contêm informações do imóvel
        # Scripts, estilos, headers, footers, navs, barras laterais, formulários e iframes são ruído
        for noise in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form', 'iframe', 'noscript']):
            noise.decompose()
        
        # Pega o texto, usa um separador para não colar palavras
        texto = soup.get_text(separator=' ', strip=True)
        
        # Limpeza de espaços duplos e quebras de linha excessivas
        texto_limpo = " ".join(texto.split())
        
        return texto_limpo
    except Exception as e:
        print(f"⚠ Erro ao limpar HTML: {str(e)}")
        return ""


def chunk_text(texto, chunk_size=1000, overlap=200):
    """Divide texto em pedaços com overlap para melhor contextualização."""
    if not texto:
        return []
    chunks = []
    start = 0
    L = len(texto)
    while start < L:
        end = start + chunk_size
        chunks.append(texto[start:end])
        if end >= L:
            break
        start = max(0, end - overlap)
    return chunks


# ============================================================================
# SEÇÃO 2: FUNÇÕES DE CLASSIFICAÇÃO E EXTRAÇÃO DE PDF
# ============================================================================

def classificar_link(url):
    """Classifica o tipo de link baseado na URL e extensão."""
    url_lower = url.lower()
    
    # Arquivos de Documento
    if any(ext in url_lower for ext in ['.pdf', '.docx', '.doc', '.pptx']):
        return "📄 Documento"
    
    # Arquivos de Imagem/Plantas
    if any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
        return "🖼️ Imagem/Planta"
    
    # Links de Armazenamento em Nuvem
    if any(cloud in url_lower for cloud in ['drive.google', 'dropbox', 'onedrive', 'sharepoint']):
        return "☁️ Drive/Nuvem"
    
    # Vídeos/Tours Virtuais
    if any(v in url_lower for v in ['youtube.com', 'youtu.be', 'vimeo.com', 'matterport.com', 'meutour360']):
        return "🎥 Vídeo/Tour"
    
    # Redes Sociais
    if any(social in url_lower for social in ['instagram.com', 'facebook.com', 'tiktok.com', 'linkedin.com']):
        return "📱 Rede Social"
    
    # Por padrão é página web/subsite
    return "🌐 Página Web"


async def extrair_texto_pdf(url):
    """Faz o download do PDF e extrai o texto sem salvar no disco."""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                with fitz.open(stream=io.BytesIO(response.content), filetype="pdf") as doc:
                    texto_completo = []
                    for pagina in doc:
                        texto_completo.append(pagina.get_text())

                    texto = "\n".join(texto_completo).strip()
                    return {
                        "status": "sucesso",
                        "conteudo": texto,
                        "total_caracteres": len(texto)
                    }
            return {"status": "erro", "erro": f"Status code: {response.status_code}"}
    except Exception as e:
        return {"status": "erro", "erro": str(e)}


# ============================================================================
# SEÇÃO 3: FUNÇÕES DE ARMAZENAMENTO EM JSONL (Base de Conhecimento)
# ============================================================================

def salvar_para_base_conhecimento(dados_imovel, arquivo="data/base_conhecimento.jsonl"):
    """Salva os dados extraídos no formato JSON Lines (JSONL).
    
    Cada linha é um objeto JSON independente, permitindo:
    - Processamento streaming sem carregar o arquivo inteiro na memória
    - Integração direta com Vector Databases (Pinecone, ChromaDB, etc.)
    - Pronto para uso em sistemas de RAG (Retrieval-Augmented Generation)
    
    Args:
        dados_imovel: Dicionário com os dados do imóvel
        arquivo: Caminho do arquivo JSONL (append mode)
    """
    os.makedirs(os.path.dirname(arquivo) or ".", exist_ok=True)
    try:
        with open(arquivo, 'a', encoding='utf-8') as f:
            linha = json.dumps(dados_imovel, ensure_ascii=False)
            f.write(linha + '\n')
    except Exception as e:
        print(f"⚠ Erro ao salvar documento JSONL: {str(e)}")


# ============================================================================
# SEÇÃO 4: FUNÇÕES DE EXTRAÇÃO (WEB SCRAPING)
# ============================================================================

def slugify(s):
    """Converte string em slug para usar em nomes de diretório."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


async def extrair_conteudo_profundo(browser_context, nome, url_pai):
    """Acessa um link específico (imóvel) e extrai os links internos dele.
    
    Retorna lista de links com tipos classificados e conteúdo pré-processado.
    """
    page = await browser_context.new_page()
    links_internos = []
    html_conteudo = ""
    
    try:
        print(f"--- Explorando: {nome} ---")
        # Timeout mais curto para não travar
        await page.goto(url_pai, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1500)
        
        # Captura o HTML da página para limpeza
        html_conteudo = await page.content()

        # Captura todos os links da página de destino
        elementos = await page.query_selector_all('a')
        
        for el in elementos:
            try:
                texto = await el.inner_text()
                href = await el.get_attribute("href")
                
                if href and href.startswith('http'):
                    # Filtramos para evitar redes sociais e focar em dados do imóvel
                    if not any(x in href.lower() for x in ['facebook', 'instagram', 'twitter', 'whatsapp', 'utm_', 'linkedin']):
                        # Classificação de link
                        tipo = classificar_link(href)
                        
                        entry = {
                            "texto": texto.strip() or "Sem título",
                            "url": href,
                            "tipo": tipo
                        }

                        # Se for um PDF, tenta extrair o texto e gerar chunks/metadados
                        if tipo == "📄 Documento" and href.lower().endswith('.pdf'):
                            try:
                                dados_pdf = await extrair_texto_pdf(href)
                                if dados_pdf.get('status') == 'sucesso':
                                    conteudo = limpar_texto(dados_pdf.get('conteudo', ''))
                                    chunks = chunk_text(conteudo, chunk_size=1000, overlap=200)
                                    arquivo = href.split('/')[-1].split('?')[0]
                                    entry['conteudo_extraido'] = conteudo[:1000]
                                    entry['chunks'] = chunks
                                    entry['metadados'] = {
                                        'site_origem': nome,
                                        'arquivo': arquivo,
                                        'total_caracteres': dados_pdf.get('total_caracteres', 0)
                                    }
                                else:
                                    entry['conteudo_extraido'] = ''
                                    entry['chunks'] = []
                                    entry['metadados'] = {'site_origem': nome, 'arquivo': href.split('/')[-1].split('?')[0], 'erro': dados_pdf.get('erro')}
                            except Exception as e:
                                entry['conteudo_extraido'] = ''
                                entry['chunks'] = []
                                entry['metadados'] = {'site_origem': nome, 'arquivo': href.split('/')[-1].split('?')[0], 'erro': str(e)}

                        links_internos.append(entry)
            except:
                continue
                
    except asyncio.TimeoutError:
        print(f"⏱ Timeout ao acessar {nome}")
    except Exception as e:
        print(f"⚠ Erro ao acessar {nome}: {str(e)[:50]}")
    finally:
        await page.close()
    
    return links_internos, html_conteudo


class LimitadorConcorrencia:
    """Limita o número de requisições simultâneas para evitar sobrecarga."""
    def __init__(self, max_concurrent=3):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def executar(self, funcao, *args):
        async with self.semaphore:
            return await funcao(*args)


async def executar_automacao_completa():
    """Extrai toda a estrutura de dados dos imóveis no Linktree."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )

        # 1. PEGAR OS LINKS DO LINKTREE
        page = await context.new_page()
        await page.goto("https://linktr.ee/rivaincorporadorario", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        
        # Pega todos os links e filtra os relevantes
        all_links = await page.query_selector_all('a')
        excluded_patterns = ['#', 'javascript:', 'mailto:', 'tel:', 'utm_source', 'utm_medium', 'signup_intent', 'discover/trending', 'privacy', '/s/about']
        
        links_iniciais = []
        for elemento in all_links:
            titulo = await elemento.inner_text()
            url = await elemento.get_attribute("href")
            
            # Filtra links vazios
            if not url or not titulo.strip():
                continue
                
            # Exclui links internos relativos
            if url.startswith('/'):
                continue
                
            # Exclui padrões não desejados
            skip = False
            for pattern in excluded_patterns:
                if pattern in url.lower():
                    skip = True
                    break
            
            if not skip:
                links_iniciais.append({
                    "titulo": titulo.strip(),
                    "url": url
                })
        
        await page.close()

        # 2. PERCORRER CADA LINK ENCONTRADO (Nível 2)
        print(f"Encontrados {len(links_iniciais)} links totais no Linktree\n")
        
        # Filtra apenas links de imóveis
        links_imoveis = [link for link in links_iniciais if 'vendas' in link['url'] or 'imovei' in link['titulo'].lower()]
        
        print(f"Explorando {len(links_imoveis)} imóveis/projetos...\n")
        
        mapa_final = {}
        limitador = LimitadorConcorrencia(max_concurrent=3)
        
        tarefas = []
        for item in links_imoveis:
            tarefas.append(
                limitador.executar(extrair_conteudo_profundo, context, item['titulo'], item['url'])
            )
        
        # Aguarda todas as tarefas com limite de concorrência
        resultados = await asyncio.gather(*tarefas, return_exceptions=True)
        
        for i, (item, resultado) in enumerate(zip(links_imoveis, resultados)):
            if isinstance(resultado, Exception):
                mapa_final[item['titulo']] = {
                    "url_principal": item['url'],
                    "links_internos": [],
                    "erro": str(resultado),
                    "html_limpo": ""
                }
            else:
                links_internos, html_conteudo = resultado
                mapa_final[item['titulo']] = {
                    "url_principal": item['url'],
                    "links_internos": links_internos,
                    "html_limpo": limpar_conteudo_html(html_conteudo)
                }

        await browser.close()
        
        # EXIBIÇÃO DO RESULTADO
        for site, dados in mapa_final.items():
            print(f"\n{'='*70}")
            print(f"📍 {site}")
            print(f"{'='*70}")
            print(f"URL Principal: {dados['url_principal']}")
            print(f"Total de sublinks: {len(dados['links_internos'])}\n")
            
            # Agrupa por tipo de link
            links_por_tipo = {}
            for sub in dados['links_internos']:
                tipo = sub['tipo']
                if tipo not in links_por_tipo:
                    links_por_tipo[tipo] = []
                links_por_tipo[tipo].append(sub)
            
            # Exibe agrupado por tipo
            for tipo, links in sorted(links_por_tipo.items()):
                print(f"\n{tipo} ({len(links)} links):")
                for link in links[:5]:
                    print(f"  ├─ {link['texto']}")
                    print(f"  │  └─ {link['url'][:80]}...")
                if len(links) > 5:
                    print(f"  └─ ... e mais {len(links) - 5} links deste tipo")
        
        return mapa_final


# ============================================================================
# SEÇÃO 5: FUNÇÕES DE PROCESSAMENTO E INGESTÃO DE PDFs
# ============================================================================

DATA_DIR = "data"


async def download_bytes(client: httpx.AsyncClient, url: str, timeout: int = 30):
    """Faz download de arquivo em bytes."""
    r = await client.get(url, follow_redirects=True, timeout=timeout)
    r.raise_for_status()
    return r.content


def _extract_drive_file_ids_from_html(html: str):
    """Extrai IDs de arquivos do Google Drive a partir do HTML."""
    ids = set()
    for m in re.finditer(r"/file/d/([a-zA-Z0-9_-]{10,})", html):
        ids.add(m.group(1))
    for m in re.finditer(r"[?&]id=([a-zA-Z0-9_-]{10,})", html):
        ids.add(m.group(1))
    return list(ids)


def drive_file_direct_url(file_id: str):
    """Converte ID do Google Drive para URL de download direto."""
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def dropbox_direct_url(url: str):
    """Converte URL do Dropbox para download direto."""
    if 'dropbox.com' in url:
        if 'dl=0' in url:
            return url.replace('dl=0', 'dl=1')
        if 'dl=1' in url:
            return url
        if '?' in url:
            return url + '&dl=1'
        return url + '?dl=1'
    return url


async def resolve_drive_links(url: str, client: httpx.AsyncClient):
    """Resolvem links do Google Drive (pastas ou arquivos) para URLs diretas."""
    urls = []
    if 'drive.google.com' in url:
        m = re.search(r"/file/d/([a-zA-Z0-9_-]{10,})", url)
        if m:
            urls.append(drive_file_direct_url(m.group(1)))
            return urls
        m = re.search(r"[?&]id=([a-zA-Z0-9_-]{10,})", url)
        if m:
            urls.append(drive_file_direct_url(m.group(1)))
            return urls
        if '/drive/folders/' in url or '/folders/' in url:
            try:
                r = await client.get(url, follow_redirects=True, timeout=20)
                r.raise_for_status()
                ids = _extract_drive_file_ids_from_html(r.text)
                for fid in ids:
                    urls.append(drive_file_direct_url(fid))
            except Exception:
                return []
    return urls


async def process_pdf(item, site_slug, site_nome, client: httpx.AsyncClient):
    """Processa um PDF: faz download, extrai texto, limpa, faz chunks e salva em JSONL.
    
    Também salva uma cópia bruta do arquivo para referência.
    O arquivo é salvo em formato JSONL pronto para Vector DB/RAG.
    """
    url = item["url"]
    nome = url.split("/")[-1].split("?")[0] or f"file_{hashlib.sha1(url.encode()).hexdigest()}.pdf"
    raw_dir = os.path.join(DATA_DIR, "raw", site_slug)
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, nome)

    result = {
        "source_url": url,
        "site_origem": site_nome,
        "site_slug": site_slug,
        "arquivo": nome,
        "raw_path": raw_path,
        "status": "unknown"
    }

    try:
        content = await download_bytes(client, url)
        with open(raw_path, "wb") as fh:
            fh.write(content)
        sha = hashlib.sha256(content).hexdigest()
        result["sha256"] = sha
        result["bytes"] = len(content)

        # Extrair texto com PyMuPDF
        texto_pages = []
        with fitz.open(stream=io.BytesIO(content), filetype="pdf") as doc:
            for p in doc:
                texto_pages.append(p.get_text())
        texto = "\n".join(texto_pages).strip()
        texto_clean = limpar_texto(texto)
        chunks = chunk_text(texto_clean, chunk_size=1000, overlap=200)

        # Salvar JSONL (Base de Conhecimento)
        extracted_dir = os.path.join(DATA_DIR, "extracted", site_slug)
        os.makedirs(extracted_dir, exist_ok=True)
        jsonl_path = os.path.join(extracted_dir, f"{nome}.jsonl")
        
        with open(jsonl_path, "w", encoding="utf-8") as fh:
            for idx, c in enumerate(chunks):
                item_json = {
                    "id": f"{nome}#chunk{idx}",
                    "source_url": url,
                    "site_origem": site_nome,
                    "site_slug": site_slug,
                    "arquivo": nome,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "texto": c,
                    "crawl_date": datetime.utcnow().isoformat(),
                    "sha256": sha
                }
                fh.write(json.dumps(item_json, ensure_ascii=False) + "\n")
                
                # Também salva na base de conhecimento central
                salvar_para_base_conhecimento(item_json)

        result["jsonl"] = jsonl_path
        result["total_chunks"] = len(chunks)
        result["status"] = "sucesso"
    except Exception as e:
        result["status"] = "erro"
        result["erro"] = str(e)
    return result


# ============================================================================
# SEÇÃO 6: FUNÇÃO PRINCIPAL (ORQUESTRADOR)
# ============================================================================

async def main():
    """Função principal que orquestra toda a ingestão de dados."""
    
    print("\n" + "="*80)
    print(" 🏢 SISTEMA DE INGESTÃO DE DADOS - RIVA INCORPORADORA")
    print("="*80 + "\n")
    
    # 1) Executa extração para obter mapa_final
    print("📊 ETAPA 1: Extração de dados dos imóveis...\n")
    mapa = await executar_automacao_completa()

    # 2) Processa documentos e cria base de conhecimento
    print("\n📊 ETAPA 2: Processando documentos e criando base de conhecimento...\n")
    
    tasks = []
    async with httpx.AsyncClient() as client:
        for site, dados in mapa.items():
            site_slug = slugify(site)
            
            # Salva o conteúdo HTML limpo também na base de conhecimento
            if dados.get('html_limpo'):
                doc_html = {
                    "id": f"{site_slug}_pagina_principal",
                    "source_url": dados['url_principal'],
                    "site_origem": site,
                    "site_slug": site_slug,
                    "type": "página_principal",
                    "texto": dados['html_limpo'],
                    "crawl_date": datetime.utcnow().isoformat()
                }
                salvar_para_base_conhecimento(doc_html)
            
            for sub in dados.get("links_internos", []):
                tipo = sub.get("tipo", "")
                url = sub.get("url", "")

                # Dropbox: converte para direct
                if 'dropbox.com' in url:
                    direct = dropbox_direct_url(url)
                    if direct.lower().endswith('.pdf'):
                        tasks.append(process_pdf({'url': direct, 'metadados': sub.get('metadados', {})}, site_slug, site, client))
                    continue

                # Google Drive links and folders
                if 'drive.google.com' in url:
                    resolved = await resolve_drive_links(url, client)
                    for pdf_url in resolved:
                        tasks.append(process_pdf({'url': pdf_url, 'metadados': sub.get('metadados', {})}, site_slug, site, client))
                    continue

                # PDFs directos
                if (tipo == "📄 Documento" and url.lower().endswith('.pdf')):
                    tasks.append(process_pdf(sub, site_slug, site, client))

        # Limita concorrência com gather em blocos
        results = []
        CONC = 4
        for i in range(0, len(tasks), CONC):
            batch = tasks[i:i+CONC]
            res = await asyncio.gather(*batch)
            results.extend(res)

    # 3) Salva summary
    print("\n📊 ETAPA 3: Finalizando e salvando sumário...\n")
    os.makedirs(DATA_DIR, exist_ok=True)
    summary_path = os.path.join(DATA_DIR, "ingest_summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    
    # Informa consumidor sobre a base de conhecimento
    base_conhecimento_path = os.path.join(DATA_DIR, "base_conhecimento.jsonl")
    print(f"✅ Ingest finished!")
    print(f"   📋 Summary: {summary_path}")
    print(f"   🧠 Base de Conhecimento (JSONL): {base_conhecimento_path}")
    print(f"   💾 Total de linhas processadas: {len(results)}")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
