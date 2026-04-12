"""
Script para ingerir toda a informação dos Linktrees da Riva Vendas
Carrega automaticamente todos os sites presentes nos linktrees
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
from typing import Set, List, Dict
from data_ingestion import ingestion_pipeline
from knowledge_manager import intelligence_core
import json

class LinktreeIngester:
    """Ingere linktrees e todos os sites presentes neles"""
    
    def __init__(self, max_depth=2, timeout=20, max_retries=3):
        self.visited_urls: Set[str] = set()
        self.failed_urls: List[Dict] = []
        self.ingested_count = 0
        self.max_depth = max_depth
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _get_with_retries(self, url: str) -> requests.Response:
        """Tenta realizar uma requisição GET com retries para evitar perda de sites lentos."""
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)
                return response
            except (requests.Timeout, requests.ConnectionError) as e:
                last_exception = e
                print(f"    ⚠️ Tentativa {attempt}/{self.max_retries} falhou para {url}: {e}")
                time.sleep(1)  # pequena pausa antes de tentar novamente
                continue
        # se chegou aqui, todas as tentativas falharam
        raise last_exception
    
    def extract_links_from_linktree(self, linktree_url: str) -> List[str]:
        """Extrai todos os links do linktree"""
        print(f"\n📍 Analisando linktree: {linktree_url}")
        
        try:
            response = self._get_with_retries(linktree_url)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'html.parser')
            
            links = []
            
            # Procura por links em vários padrões comuns de linktree
            for link_elem in soup.find_all('a', href=True):
                href = link_elem.get('href', '').strip()
                
                # Ignora links vazios, anchors e linktree interno
                if not href or href.startswith('#') or 'linktr.ee' in href:
                    continue
                
                # Converte URLs relativas em absolutas
                full_url = urljoin(linktree_url, href)
                
                # Ignora URLs muito longas (provavelmente tracking/analytics)
                if len(full_url) < 500 and full_url not in links:
                    links.append(full_url)
            
            print(f"✅ Encontrados {len(links)} links no linktree")
            return links
        
        except Exception as e:
            print(f"❌ Erro ao processar linktree: {str(e)}")
            self.failed_urls.append({"url": linktree_url, "erro": str(e)})
            return []
    
    def should_visit_url(self, url: str, parent_domain: str = None) -> bool:
        """Verifica se deve visitar a URL"""
        if url in self.visited_urls:
            return False
        
        # Evita URLs muito longas (tracking/analytics)
        if len(url) > 500:
            return False
        
        # Evita certos domínios
        blocked_domains = [
            'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com',
            'youtube.com', 'tiktok.com', 'google.com', 'reddit.com'
        ]
        
        parsed = urlparse(url)
        for blocked in blocked_domains:
            if blocked in parsed.netloc:
                return False
        
        return True
    
    def scrape_page(self, url: str, depth: int = 0) -> Dict:
        """Scrapa uma página e retorna seu conteúdo"""
        if url in self.visited_urls or depth > self.max_depth:
            return None
        
        if not self.should_visit_url(url):
            return None
        
        self.visited_urls.add(url)
        
        print(f"  {'  ' * depth}🔗 [{depth}] Visitando: {url[:80]}...")
        
        try:
            response = self._get_with_retries(url)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"  {'  ' * depth}⚠️ Status {response.status_code}")
                self.failed_urls.append({"url": url, "erro": f"Status {response.status_code}"})
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove scripts e styles
            for script in soup(['script', 'style']):
                script.decompose()
            
            # Extrai texto
            text = soup.get_text(separator='\n', strip=True)
            
            # Limpa espaços vazios
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            content = '\n'.join(lines)
            
            # Limita tamanho
            if len(content) > 50000:
                content = content[:50000] + "\n[CONTEÚDO TRUNCADO]"
            
            # Extrai título
            title = soup.find('title')
            page_title = title.get_text() if title else "Sem título"
            
            print(f"  {'  ' * depth}✅ {len(content)} caracteres capturados")
            
            # Ingirir na base de conhecimento
            self.ingest_content(url, page_title, content)
            
            # Extrair links para visitar próxima iteração
            links_to_visit = []
            if depth < self.max_depth:
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '').strip()
                    if href and not href.startswith('#'):
                        full_url = urljoin(url, href)
                        if self.should_visit_url(full_url):
                            links_to_visit.append(full_url)
            
            return {
                "url": url,
                "titulo": page_title,
                "conteudo": content,
                "links": links_to_visit[:5]  # Limita a 5 links por página
            }
        
        except requests.Timeout:
            print(f"  {'  ' * depth}⏱️ Timeout")
            self.failed_urls.append({"url": url, "erro": "Timeout"})
            return None
        except Exception as e:
            print(f"  {'  ' * depth}❌ Erro: {str(e)[:50]}")
            self.failed_urls.append({"url": url, "erro": str(e)})
            return None
    
    def ingest_content(self, url: str, titulo: str, conteudo: str):
        """Ingirir conteúdo na base de conhecimento"""
        try:
            # Cria um documento bem estruturado
            doc = f"""
FONTE: {url}
TÍTULO: {titulo}
---
{conteudo}
"""
            # Adiciona ao intelligence_core (lista de documentos)
            intelligence_core.add_training_data(
                documents=[doc],
                source="linktree_scrape",
                category="website"
            )
            self.ingested_count += 1
        except Exception as e:
            print(f"  ❌ Erro ao ingerir: {str(e)}")
    
    def crawl_recursive(self, url: str, depth: int = 0):
        """Faz crawl recursivo de um site"""
        if depth > self.max_depth or url in self.visited_urls:
            return
        
        page_data = self.scrape_page(url, depth)
        
        if page_data and page_data.get('links'):
            # Pausa entre requisições
            time.sleep(0.5)
            
            # Visita links encontrados
            for link in page_data['links']:
                self.crawl_recursive(link, depth + 1)
    
    def ingest_linktree(self, linktree_url: str):
        """Processa um linktree e todos seus links"""
        print(f"\n{'='*80}")
        print(f"🚀 INICIANDO INGESTÃO: {linktree_url}")
        print(f"{'='*80}")
        
        # Extrai links do linktree
        links = self.extract_links_from_linktree(linktree_url)
        
        print(f"\n📂 Iniciando crawl de {len(links)} sites encontrados...")
        
        # Visita cada link encontrado
        for i, link in enumerate(links, 1):
            print(f"\n[{i}/{len(links)}]", end=" ")
            self.crawl_recursive(link, depth=0)
            time.sleep(1)  # Pausa entre diferentes sites
        
        print(f"\n{'='*80}")
        print(f"✅ Ingestão concluída!")
        print(f"{'='*80}")
    
    def print_summary(self):
        """Imprime resumo da ingestão"""
        print(f"\n📊 RESUMO DA INGESTÃO")
        print(f"{'='*80}")
        print(f"✅ Páginas ingeridas: {self.ingested_count}")
        print(f"🔗 URLs visitadas: {len(self.visited_urls)}")
        print(f"❌ URLs com erro: {len(self.failed_urls)}")
        print(f"{'='*80}")
        
        if self.failed_urls:
            print(f"\n⚠️ URLs com erro:")
            for fail in self.failed_urls[:10]:  # Mostra apenas as 10 primeiras
                print(f"  - {fail['url'][:70]}: {fail['erro']}")
            if len(self.failed_urls) > 10:
                print(f"  ... e mais {len(self.failed_urls) - 10} erros")
        
        print(f"\n💾 Todo o conteúdo foi armazenado em ./conhecimento_ia/")
        print(f"🤖 O bot agora conhece todos esses sites!")


def main():
    """Executa a ingestão dos 3 linktrees"""
    
    linktrees = [
        "https://linktr.ee/rivaincorporadorario",
        "https://linktr.ee/marinebarra.vendas",
        "https://linktr.ee/duetbarra.vendas"
    ]
    
    ingester = LinktreeIngester(max_depth=2, timeout=20, max_retries=3)
    
    print("\n" + "="*80)
    print("🎯 INGESTOR DE LINKTREES - RIVA VENDAS")
    print("="*80)
    print("\nEste script irá:")
    print("1. Ler cada linktree")
    print("2. Extrair todos os links")
    print("3. Visitar cada site (até 2 níveis de profundidade)")
    print("4. Armazenar todo conteúdo na base de conhecimento")
    print("\n⏳ Isso pode levar alguns minutos. (Cada site: ~1-2 segundos)")
    print("="*80)
    
    start_time = time.time()
    
    for linktree in linktrees:
        try:
            ingester.ingest_linktree(linktree)
            print(f"\n✅ {linktree} processado com sucesso!\n")
        except Exception as e:
            print(f"\n❌ Erro ao processar {linktree}: {str(e)}\n")
    
    elapsed = time.time() - start_time
    
    ingester.print_summary()
    
    print(f"\n⏱️ Tempo total: {elapsed:.1f} segundos ({elapsed/60:.1f} minutos)")
    print(f"\n🎉 Bot atualizado com todo o conhecimento dos linktrees!")
    print(f"\n💡 Próximo: Envie uma mensagem para testar as novas respostas!")


if __name__ == "__main__":
    main()
