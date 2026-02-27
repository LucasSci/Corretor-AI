import asyncio
import re
import json
import hashlib
import os
import io
import logging
from datetime import datetime

import httpx
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("CorretorAI")

class AsyncRetry:
    """Decorator para retry com exponential backoff em funções assíncronas."""
    def __init__(self, retries=3, delay=1, backoff=2, exceptions=(Exception,)):
        self.retries = retries
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions

    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            delay = self.delay
            for attempt in range(self.retries + 1):
                try:
                    return await func(*args, **kwargs)
                except self.exceptions as e:
                    if attempt == self.retries:
                        logger.error(f"❌ Falha final em {func.__name__} após {self.retries} tentativas: {e}")
                        raise e

                    logger.warning(f"⚠️ Tentativa {attempt + 1}/{self.retries} falhou em {func.__name__}: {e}. Retentando em {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= self.backoff
        return wrapper

class TextCleaner:
    """Utilitários para limpeza e normalização de texto e HTML."""

    @staticmethod
    def clean_text(texto):
        """Limpa quebras, espaços excessivos e caracteres de controle."""
        if not texto:
            return ""

        # Remove caracteres de controle invisíveis e zero-width spaces
        texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b\uFEFF]", "", texto)

        # Normaliza espaços
        texto = re.sub(r"[ \t]+", " ", texto)

        # Remove linhas em branco consecutivas excessivas (mais de 2)
        texto = re.sub(r"\n{3,}", "\n\n", texto)

        return texto.strip()

    @staticmethod
    def clean_html(html_content):
        """Extrai texto limpo de HTML, removendo ruídos (scripts, menus, etc)."""
        if not html_content:
            return ""

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove tags de infraestrutura e navegação
            tags_to_remove = [
                'script', 'style', 'header', 'footer', 'nav',
                'aside', 'form', 'iframe', 'noscript', 'meta', 'link'
            ]
            for tag in soup(tags_to_remove):
                tag.decompose()

            # Extrai texto com separador de espaço
            texto = soup.get_text(separator=' ', strip=True)

            return TextCleaner.clean_text(texto)
        except Exception as e:
            logger.error(f"Erro ao limpar HTML: {e}")
            return ""

class SmartChunker:
    """Fragmenta texto mantendo a coerência semântica e estrutural.

    Implementa divisão recursiva baseada em separadores lógicos (parágrafos,
    quebras de linha, frases, palavras) para garantir chunks balanceados.
    """
    def __init__(self, chunk_size=1000, overlap=200):
        self.chunk_size = chunk_size
        self.overlap = overlap
        # Separadores da maior para menor granulosidade
        self.separators = ["\n\n", "\n", ". ", "? ", "! ", " "]

    def split_text(self, text):
        """Retorna lista de chunks a partir do texto completo."""
        if not text:
            return []

        return self._recursive_split(text, self.separators)

    def _recursive_split(self, text, separators):
        """Função interna recursiva para divisão com overlap."""
        final_chunks = []

        if len(text) <= self.chunk_size:
            return [text]

        if not separators:
            chunks = []
            for i in range(0, len(text), self.chunk_size - self.overlap):
                chunks.append(text[i:i + self.chunk_size])
            return chunks

        separator = separators[0]
        next_separators = separators[1:]

        splits = text.split(separator)

        current_chunk = []
        current_length = 0

        for split in splits:
            split_len = len(split)

            if current_length + len(separator) + split_len > self.chunk_size:
                if current_chunk:
                    joined_chunk = separator.join(current_chunk)
                    final_chunks.append(joined_chunk)

                    overlap_chunk = []
                    overlap_len = 0
                    for item in reversed(current_chunk):
                        if overlap_len + len(item) + len(separator) <= self.overlap:
                            overlap_chunk.insert(0, item)
                            overlap_len += len(item) + len(separator)
                        else:
                            break
                    current_chunk = overlap_chunk
                    current_length = overlap_len

                if split_len > self.chunk_size:
                    sub_chunks = self._recursive_split(split, next_separators)
                    final_chunks.extend(sub_chunks)
                    continue

            current_chunk.append(split)
            current_length += len(separator) + split_len

        if current_chunk:
            final_chunks.append(separator.join(current_chunk))

        return final_chunks

class PDFProcessor:
    """Extrai texto de PDFs com limpeza avançada e heurísticas."""

    @staticmethod
    def extract_text(pdf_bytes):
        """Extrai texto limpo de PDF (bytes) removendo headers/footers repetitivos."""
        if not pdf_bytes:
            return ""

        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages_text = []

            for page in doc:
                text = page.get_text("text")
                if text.strip():
                    pages_text.append(text)

            if not pages_text:
                return ""

            if len(pages_text) > 2:
                line_counts = {}
                for page_text in pages_text:
                    lines = set(l.strip() for l in page_text.split('\n') if l.strip())
                    for line in lines:
                        line_counts[line] = line_counts.get(line, 0) + 1

                threshold = 0.8 * len(pages_text)
                repetitive_lines = {line for line, count in line_counts.items() if count > threshold}

                cleaned_pages = []
                for page_text in pages_text:
                    cleaned_lines = []
                    for line in page_text.split('\n'):
                        if line.strip() not in repetitive_lines:
                            cleaned_lines.append(line)
                    cleaned_pages.append("\n".join(cleaned_lines))

                full_text = "\n\n".join(cleaned_pages)
            else:
                full_text = "\n\n".join(pages_text)

            return TextCleaner.clean_text(full_text)

        except Exception as e:
            logger.error(f"Erro ao processar PDF: {e}")
            return ""

    @staticmethod
    def _remove_headers_footers(pages_text, threshold=0.8):
        """Remove linhas que aparecem em mais de 80% das páginas (heurística)."""
        line_counts = {}
        total_pages = len(pages_text)

        for text in pages_text:
            lines = set(l.strip() for l in text.splitlines() if l.strip())
            for line in lines:
                line_counts[line] = line_counts.get(line, 0) + 1

        repetitive_lines = {
            line for line, count in line_counts.items()
            if count / total_pages >= threshold
        }

        cleaned_pages = []
        for text in pages_text:
            cleaned_lines = []
            for line in text.splitlines():
                if line.strip() not in repetitive_lines:
                    cleaned_lines.append(line)
            cleaned_pages.append("\n".join(cleaned_lines))

        return cleaned_pages


class LinkUtils:
    """Utilitários para manipulação e classificação de links."""

    @staticmethod
    def slugify(s):
        """Converte string em slug para usar em nomes de diretório."""
        s = s.lower()
        s = re.sub(r"[^a-z0-9]+", "_", s)
        s = re.sub(r"_+", "_", s)
        return s.strip("_")

    @staticmethod
    def classify_link(url):
        """Classifica o tipo de link baseado na URL e extensão."""
        url_lower = url.lower()
        if any(ext in url_lower for ext in ['.pdf', '.docx', '.doc', '.pptx']):
            return "📄 Documento"
        if any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
            return "🖼️ Imagem/Planta"
        if any(cloud in url_lower for cloud in ['drive.google', 'dropbox', 'onedrive', 'sharepoint']):
            return "☁️ Drive/Nuvem"
        if any(v in url_lower for v in ['youtube.com', 'youtu.be', 'vimeo.com', 'matterport.com', 'meutour360']):
            return "🎥 Vídeo/Tour"
        if any(social in url_lower for social in ['instagram.com', 'facebook.com', 'tiktok.com', 'linkedin.com']):
            return "📱 Rede Social"
        return "🌐 Página Web"

    @staticmethod
    def dropbox_direct_url(url):
        """Converte URL do Dropbox para download direto."""
        if 'dropbox.com' in url:
            if 'dl=0' in url:
                return url.replace('dl=0', 'dl=1')
            if 'dl=1' in url:
                return url
            return url + ('&dl=1' if '?' in url else '?dl=1')
        return url

    @staticmethod
    def _extract_drive_file_ids_from_html(html):
        """Extrai IDs de arquivos do Google Drive a partir do HTML."""
        ids = set()
        for m in re.finditer(r"/file/d/([a-zA-Z0-9_-]{10,})", html):
            ids.add(m.group(1))
        for m in re.finditer(r"[?&]id=([a-zA-Z0-9_-]{10,})", html):
            ids.add(m.group(1))
        return list(ids)

    @staticmethod
    def drive_file_direct_url(file_id):
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    @staticmethod
    async def resolve_drive_links(url, client):
        """Resolvem links do Google Drive (pastas ou arquivos) para URLs diretas."""
        urls = []
        if 'drive.google.com' in url:
            m = re.search(r"/file/d/([a-zA-Z0-9_-]{10,})", url)
            if m:
                urls.append(LinkUtils.drive_file_direct_url(m.group(1)))
                return urls
            m = re.search(r"[?&]id=([a-zA-Z0-9_-]{10,})", url)
            if m:
                urls.append(LinkUtils.drive_file_direct_url(m.group(1)))
                return urls
            if '/drive/folders/' in url or '/folders/' in url:
                try:
                    r = await client.get(url, follow_redirects=True, timeout=20)
                    r.raise_for_status()
                    ids = LinkUtils._extract_drive_file_ids_from_html(r.text)
                    for fid in ids:
                        urls.append(LinkUtils.drive_file_direct_url(fid))
                except Exception:
                    return []
        return urls


class IngestionPipeline:
    """Pipeline principal de ingestão de dados imobiliários."""

    def __init__(self):
        self.semaphore = asyncio.Semaphore(3)  # Limite de 3 conexões simultâneas
        self.chunker = SmartChunker(chunk_size=1000, overlap=200)
        self.pdf_processor = PDFProcessor()
        self.base_knowledge_file = "data/base_conhecimento.jsonl"

        # Garante diretório de saída
        os.makedirs("data", exist_ok=True)

    def save_chunk(self, chunk_data):
        """Salva um chunk estruturado no JSONL."""
        try:
            with open(self.base_knowledge_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(chunk_data, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Erro ao salvar chunk: {e}")

    @AsyncRetry(retries=3, delay=2)
    async def download_pdf(self, client, url):
        response = await client.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()
        return response.content

    async def process_pdf_link(self, client, url, property_name, property_url):
        """Processa um link de PDF encontrado."""
        try:
            pdf_bytes = await self.download_pdf(client, url)

            # Extração e Limpeza
            clean_text = self.pdf_processor.extract_text(pdf_bytes)
            if not clean_text:
                return

            # Chunking Inteligente
            chunks = self.chunker.split_text(clean_text)

            file_name = url.split("/")[-1].split("?")[0]

            # Salvamento Estruturado
            for idx, chunk_text in enumerate(chunks):
                chunk_id = hashlib.sha256(f"{url}_{idx}".encode()).hexdigest()

                metadata = {
                    "id_chunk": chunk_id,
                    "texto": chunk_text,
                    "metadados": {
                        "nome_empreendimento": property_name,
                        "tipo_fonte": "pdf",
                        "url_origem": property_url,
                        "url_arquivo": url,
                        "titulo_documento": file_name,
                        "data_extracao": datetime.utcnow().strftime("%Y-%m-%d"),
                        "chunk_index": idx,
                        "total_chunks": len(chunks)
                    }
                }
                self.save_chunk(metadata)

            logger.info(f"✅ PDF processado: {file_name} ({len(chunks)} chunks)")

        except Exception as e:
            logger.error(f"Erro ao processar PDF {url}: {e}")

    async def process_property(self, browser_context, client, name, url):
        """Processa a página de um imóvel e seus sublinks."""
        async with self.semaphore:
            logger.info(f"🏗️ Processando imóvel: {name}")
            page = await browser_context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)

                # 1. Extração do Conteúdo da Página HTML
                html_content = await page.content()
                clean_html_text = TextCleaner.clean_html(html_content)

                if clean_html_text:
                    chunks = self.chunker.split_text(clean_html_text)
                    for idx, chunk_text in enumerate(chunks):
                        chunk_id = hashlib.sha256(f"{url}_html_{idx}".encode()).hexdigest()
                        metadata = {
                            "id_chunk": chunk_id,
                            "texto": chunk_text,
                            "metadados": {
                                "nome_empreendimento": name,
                                "tipo_fonte": "pagina_web",
                                "url_origem": url,
                                "titulo_documento": "Página Principal",
                                "data_extracao": datetime.utcnow().strftime("%Y-%m-%d")
                            }
                        }
                        self.save_chunk(metadata)

                # 2. Descoberta e Processamento de Links (PDFs)
                links = await page.query_selector_all('a')
                tasks = []

                for link in links:
                    href = await link.get_attribute('href')
                    if not href or not href.startswith('http'):
                        continue

                    # Filtra redes sociais e irrelevantes
                    if any(x in href for x in ['facebook', 'instagram', 'linkedin', 'whatsapp']):
                        continue

                    link_type = LinkUtils.classify_link(href)

                    # Processamento de PDFs Diretos
                    if link_type == "📄 Documento" and href.lower().endswith('.pdf'):
                        tasks.append(self.process_pdf_link(client, href, name, url))

                    # Processamento de Dropbox
                    elif 'dropbox.com' in href:
                        direct_url = LinkUtils.dropbox_direct_url(href)
                        if direct_url.lower().endswith('.pdf'):
                            tasks.append(self.process_pdf_link(client, direct_url, name, url))

                    # Processamento de Google Drive
                    elif link_type == "☁️ Drive/Nuvem" and 'drive.google.com' in href:
                        drive_links = await LinkUtils.resolve_drive_links(href, client)
                        for d_link in drive_links:
                            tasks.append(self.process_pdf_link(client, d_link, name, url))

                if tasks:
                    await asyncio.gather(*tasks)

            except Exception as e:
                logger.error(f"Erro ao processar página {name}: {e}")
            finally:
                await page.close()

    async def run(self):
        """Executa o crawler principal."""
        logger.info("🚀 Iniciando Pipeline de Ingestão...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

            # Acessa Linktree Principal
            page = await context.new_page()
            await page.goto("https://linktr.ee/rivaincorporadorario", wait_until="networkidle")

            # Coleta links de imóveis
            all_links = await page.query_selector_all('a')
            property_links = []

            for link in all_links:
                href = await link.get_attribute('href')
                text = await link.inner_text()

                if href and ('vendas' in href or 'imovei' in text.lower()):
                    if href.startswith('http'):
                        property_links.append({'name': text.strip(), 'url': href})

            await page.close()
            logger.info(f"Encontrados {len(property_links)} imóveis para processar.")

            # Dispara processamento concorrente
            async with httpx.AsyncClient(timeout=30) as client:
                tasks = [
                    self.process_property(context, client, prop['name'], prop['url'])
                    for prop in property_links
                ]
                await asyncio.gather(*tasks)

            await browser.close()

        logger.info(f"✅ Pipeline Finalizado! Dados salvos em {self.base_knowledge_file}")

if __name__ == "__main__":
    asyncio.run(IngestionPipeline().run())
