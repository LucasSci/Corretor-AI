import asyncio
import re
import io
import httpx
import fitz
from playwright.async_api import async_playwright

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
    
    # Redes Sociais (caso tenha escapado do filtro)
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


def limpar_texto(texto):
    """Limpa quebras e espaços excessivos."""
    if not texto:
        return ""
    # Remove múltiplos espaços/quebras e normalize
    s = re.sub(r"\s+", " ", texto)
    return s.strip()


def chunk_text(texto, chunk_size=1000, overlap=200):
    """Divide texto em pedaços com overlap."""
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

async def extrair_conteudo_profundo(browser_context, nome, url_pai):
    """Acessa um link específico e extrai os links internos dele."""
    page = await browser_context.new_page()
    links_internos = []
    
    try:
        print(f"--- Explorando: {nome} ---")
        # Timeout mais curto para não travar
        await page.goto(url_pai, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1500)

        # Captura todos os links da página de destino
        elementos = await page.query_selector_all('a')
        
        for el in elementos:
            try:
                texto = await el.inner_text()
                href = await el.get_attribute("href")
                
                if href and href.startswith('http'):
                    # Filtramos para evitar redes sociais e focar em dados do imóvel
                    if not any(x in href.lower() for x in ['facebook', 'instagram', 'twitter', 'whatsapp', 'utm_', 'linkedin']):
                        # --- NOVA LÓGICA DE CLASSIFICAÇÃO ---
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
    
    return links_internos

# Limita o número de requisições simultâneas
class LimitadorConcorrencia:
    def __init__(self, max_concurrent=3):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def executar(self, funcao, *args):
        async with self.semaphore:
            return await funcao(*args)

async def executar_automacao_completa():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Criamos um contexto único para aproveitar cookies/cache se necessário
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )

        # 1. PEGAR OS LINKS DO LINKTREE (Seu código base)
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

        # 2. PERCORRER CADA LINK ENCONTRADO (Nível 2) - Apenas imóveis
        print(f"Encontrados {len(links_iniciais)} links totais no Linktree\n")
        
        # Filtra apenas links de imóveis (com .vendas ou que parecem ser de projetos)
        links_imoveis = [link for link in links_iniciais if 'vendas' in link['url'] or 'imovei' in link['titulo'].lower()]
        
        print(f"Explorando {len(links_imoveis)} imóveis/projetos...\n")
        
        mapa_final = {}
        limitador = LimitadorConcorrencia(max_concurrent=3)  # Máximo 3 requisições simultâneas
        
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
                    "erro": str(resultado)
                }
            else:
                mapa_final[item['titulo']] = {
                    "url_principal": item['url'],
                    "links_internos": resultado
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
                for link in links[:5]:  # Mostra até 5 de cada tipo
                    print(f"  ├─ {link['texto']}")
                    print(f"  │  └─ {link['url'][:80]}...")
                if len(links) > 5:
                    print(f"  └─ ... e mais {len(links) - 5} links deste tipo")
            # Retorna o mapa para uso por outros scripts (ingestão)
        return mapa_final
if __name__ == "__main__":
    asyncio.run(executar_automacao_completa())
