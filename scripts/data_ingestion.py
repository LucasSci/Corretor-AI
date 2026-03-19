"""
Sistema de ingestão de dados multi-fonte.
Permite adicionar conhecimento de PDFs, imóveis, websites, plantas, etc.
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path
from urllib.parse import urljoin
import PyPDF2
from bs4 import BeautifulSoup
import time

from knowledge_manager import intelligence_core


class DataIngestionPipeline:
    """Pipeline de ingestão de dados multi-fonte."""
    
    def __init__(self):
        self.intelligence_core = intelligence_core
    
    def _get_with_retries(self, url: str, timeout: int = 10, max_retries: int = 3) -> requests.Response:
        """Realiza um GET com retries para reduzir perda de páginas lentas."""
        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.get(url, timeout=timeout)
                return resp
            except (requests.Timeout, requests.ConnectionError) as e:
                last_exc = e
                print(f"    ⚠️ Tentativa {attempt}/{max_retries} falhou para {url}: {e}")
                time.sleep(1)
                continue
        raise last_exc
    
    # ============ PDFs ============
    def ingest_pdf(self, pdf_path: str, categoria: str = "documento", public: bool = True):
        """Ingere dados de um arquivo PDF.

        Args:
            public: se False, esse conteúdo não será usado em respostas a clientes.
        """
        print(f"📄 Lendo PDF: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            print(f"❌ Arquivo não encontrado: {pdf_path}")
            return
        
        documentos = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        documentos.append(text)
            
            if documentos:
                self.intelligence_core.add_training_data(
                    documents=documentos,
                    source=f"PDF: {os.path.basename(pdf_path)}",
                    category=categoria,
                    public=public
                )
                print(f"✅ PDF processado: {len(documentos)} página(s)")
        
        except Exception as e:
            print(f"❌ Erro ao processar PDF: {e}")
    
    def ingest_pdf_folder(self, folder_path: str, categoria: str = "documento"):
        """Ingere todos os PDFs de uma pasta."""
        print(f"📁 Processando PDFs da pasta: {folder_path}")
        
        pdf_files = list(Path(folder_path).glob("**/*.pdf"))
        print(f"📊 {len(pdf_files)} PDF(s) encontrado(s)")
        
        for pdf_file in pdf_files:
            self.ingest_pdf(str(pdf_file), categoria)
    
    # ============ Imóveis ============
    def ingest_property(self, property_data: Dict[str, Any], public: bool = True):
        """Ingere informações de um imóvel.

        Args:
            public: se False, não será exposto a clientes
        """
        documentos = []
        
        # Montar texto estruturado do imóvel
        nome = property_data.get("nome", "Imóvel")
        descricao = property_data.get("descricao", "")
        localizacao = property_data.get("localizacao", "")
        amenidades = property_data.get("amenidades", [])
        precos = property_data.get("precos", {})
        
        # Documento 1: Descrição geral
        doc_geral = f"""
IMÓVEL: {nome}
LOCALIZAÇÃO: {localizacao}
DESCRIÇÃO: {descricao}
        """.strip()
        
        # Documento 2: Amenidades
        if amenidades:
            doc_amenidades = f"AMENIDADES do {nome}: {', '.join(amenidades)}"
            documentos.append(doc_amenidades)
        
        # Documento 3: Preços
        if precos:
            doc_precos = f"PREÇOS {nome}: " + ", ".join([
                f"{tipo}: R$ {valor}" for tipo, valor in precos.items()
            ])
            documentos.append(doc_precos)
        
        documentos.insert(0, doc_geral)
        
        self.intelligence_core.add_training_data(
            documents=documentos,
            source=f"Imóvel: {nome}",
            category="imovel",
            public=public
        )
        
        print(f"✅ Imóvel '{nome}' adicionado ao conhecimento")
    
    def ingest_properties_batch(self, properties_list: List[Dict[str, Any]]):
        """Ingere múltiplos imóveis."""
        print(f"🏢 Adicionando {len(properties_list)} imóvel(eis)...")
        for prop in properties_list:
            self.ingest_property(prop)
    
    # ============ Websites ============
    def ingest_website(self, url: str, max_pages: int = 5, public: bool = True):
        """Ingere conteúdo de um website.

        Args:
            public: se False, o conteúdo não será usado em respostas ao cliente
        """
        print(f"🌐 Explorando website: {url}")
        
        visited = set()
        to_visit = [url]
        documentos = []
        
        while to_visit and len(visited) < max_pages:
            current_url = to_visit.pop(0)
            
            if current_url in visited:
                continue
            
            visited.add(current_url)
            
            try:
                response = self._get_with_retries(current_url, timeout=10, max_retries=3)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remover scripts e styles
                for script in soup(['script', 'style']):
                    script.decompose()
                
                text = soup.get_text(separator='\n', strip=True)
                
                if text:
                    documentos.append(text[:2000])  # Limitar tamanho
                
                # Encontrar links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('/'):
                        href = urljoin(url, href)
                    
                    # Apenas links do mesmo domínio
                    if href.startswith(url) and href not in visited:
                        to_visit.append(href)
                
                print(f"  ✓ {current_url} (página {len(visited)})")
            
            except Exception as e:
                print(f"  ✗ Erro ao acessar {current_url}: {e}")
        
        if documentos:
            self.intelligence_core.add_training_data(
                documents=documentos,
                source=f"Website: {url}",
                category="website",
                public=public
            )
    def ingest_text_file(self, file_path: str, categoria: str = "documento"):
        """Ingere arquivo de texto."""
        print(f"📝 Lendo arquivo: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"❌ Arquivo não encontrado: {file_path}")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Dividir em chunks se muito grande
            chunk_size = 1000
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
            
            if chunks:
                self.intelligence_core.add_training_data(
                    documents=chunks,
                    source=f"Arquivo: {os.path.basename(file_path)}",
                    category=categoria
                )
                print(f"✅ Arquivo processado: {len(chunks)} seção(ões)")
        
        except Exception as e:
            print(f"❌ Erro ao processar arquivo: {e}")
    
    def ingest_text_folder(self, folder_path: str, categoria: str = "documento"):
        """Ingere todos os arquivos de texto de uma pasta."""
        print(f"📁 Processando arquivos da pasta: {folder_path}")
        
        text_files = list(Path(folder_path).glob("**/*.txt")) + \
                     list(Path(folder_path).glob("**/*.md"))
        
        print(f"📊 {len(text_files)} arquivo(s) encontrado(s)")
        
        for text_file in text_files:
            self.ingest_text_file(str(text_file), categoria)
    
    # ============ JSON/CSV ============
    def ingest_json_file(self, json_path: str, categoria: str = "dados"):
        """Ingere dados estruturados de JSON."""
        print(f"📋 Lendo JSON: {json_path}")
        
        if not os.path.exists(json_path):
            print(f"❌ Arquivo não encontrado: {json_path}")
            return
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Converter para strings legíveis
            documentos = []
            if isinstance(data, dict):
                for key, value in data.items():
                    documentos.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
            elif isinstance(data, list):
                for item in data:
                    documentos.append(json.dumps(item, ensure_ascii=False))
            
            if documentos:
                self.intelligence_core.add_training_data(
                    documents=documentos,
                    source=f"JSON: {os.path.basename(json_path)}",
                    category=categoria
                )
                print(f"✅ JSON processado: {len(documentos)} item(ens)")
        
        except Exception as e:
            print(f"❌ Erro ao processar JSON: {e}")
    
    # ============ Conhecimento Direto ============
    def add_custom_knowledge(self, knowledge_text: str, categoria: str = "custom", public: bool = True):
        """Adiciona conhecimento customizado diretamente.

        Args:
            public: se False, não será exposto ao cliente
        """
        documentos = [knowledge_text]
        
        self.intelligence_core.add_training_data(
            documents=documentos,
            source="Input direto",
            category=categoria,
            public=public
        )
        
        print(f"✅ Conhecimento adicionado: {categoria}")    
    def ingest_multiple_websites(self, urls: List[str], max_pages_per_site: int = 3, public: bool = True):
        """Ingere múltiplos websites de uma vez."""
        print(f"\n🌐 Ingerindo {len(urls)} website(s)...")
        total_conteudo = 0
        
        for i, url in enumerate(urls, 1):
            print(f"  [{i}/{len(urls)}] {url[:60]}...", end=" ")
            try:
                self.ingest_website(url, max_pages=max_pages_per_site, public=public)
                print("✅")
                total_conteudo += 1
            except Exception as e:
                print(f"❌ {str(e)[:30]}")
        
        print(f"\n✅ {total_conteudo}/{len(urls)} websites ingeridos com sucesso!")
    
    def ingest_website_with_depth(self, url: str, max_depth: int = 2, max_pages: int = 10, public: bool = True):
        """
        Ingere website com controle de profundidade.
        
        Args:
            url: URL inicial
            max_depth: Profundidade máxima para crawl (0=página inicial, 1=links diretos, etc)
            max_pages: Quantidade máxima de páginas a raspar
        """
        print(f"\n🌐 Explorando website com profundidade {max_depth}: {url}")
        
        visited = set()
        to_visit = [(url, 0)]  # (url, depth)
        documentos = []
        
        while to_visit and len(visited) < max_pages:
            current_url, depth = to_visit.pop(0)
            
            if current_url in visited or depth > max_depth:
                continue
            
            visited.add(current_url)
            
            try:
                print(f"  {'  ' * depth}↳ [{depth}] {current_url[:70]}...", end="")
                response = self._get_with_retries(current_url, timeout=10, max_retries=3)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remover scripts e estilos
                for script in soup(['script', 'style']):
                    script.decompose()
                
                text = soup.get_text(separator='\n', strip=True)
                
                if text:
                    documentos.append(text[:5000])  # Limitar tamanho por página
                    print(f" ✅ ({len(text)} chars)")
                else:
                    print(" (vazio)")
                
                # Encontrar links para próxima iteração
                if depth < max_depth:
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if href.startswith('/'):
                            href = urljoin(url, href)
                        
                        # Apenas links do mesmo domínio
                        if href.startswith(url.rstrip('/')) and href not in visited:
                            if len(to_visit) < max_pages * 2:  # Evita crescimento infinito
                                to_visit.append((href, depth + 1))
            
            except Exception as e:
                print(f" ❌ {str(e)[:40]}")
        
        if documentos:
            print(f"\n📝 Adicionando {len(documentos)} página(s) à base de conhecimento...")
            self.intelligence_core.add_training_data(
                documents=documentos,
                source=f"Website: {url}",
                category="website"
            )
            print(f"✅ Website processado com sucesso! ({len(visited)} páginas)")
        else:
            print(f"⚠️ Nenhum conteúdo capturado")

# Instância global
ingestion_pipeline = DataIngestionPipeline()


if __name__ == "__main__":
    print("🔄 Sistema de Ingestão de Dados Inicializado\n")
    
    # Exemplo: Ingerir imóveis
    exemplos_imoveis = [
        {
            "nome": "Apogeu Barra",
            "localizacao": "Barra da Tijuca, Rio de Janeiro",
            "descricao": "Empreendimento de luxo com acabamento premium",
            "amenidades": ["2 Piscinas", "Spa", "Academia", "Playground", "Salão de Festas"],
            "precos": {
                "Studio": "450000",
                "1 Quarto": "650000",
                "2 Quartos": "950000"
            }
        },
        {
            "nome": "Duet Barra",
            "localizacao": "Barra da Tijuca, Rio de Janeiro",
            "descricao": "Apartamentos modernos com varanda gourmet",
            "amenidades": ["Piscina", "Quadra de Esportes", "Coworking"],
            "precos": {
                "2 Quartos": "800000",
                "3 Quartos": "1200000"
            }
        }
    ]
    
    ingestion_pipeline.ingest_properties_batch(exemplos_imoveis)
    
    # Exemplo: Adicionar conhecimento direto
    ingestion_pipeline.add_custom_knowledge(
        "Os imóveis de luxo em Barra da Tijuca são ideais para clientes que buscam conforto, "
        "segurança e acesso a amenidades de primeira linha. A região oferece proximidade com "
        "shopping centers, restaurantes e praias.",
        categoria="dicas_venda"
    )
