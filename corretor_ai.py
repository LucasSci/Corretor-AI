#!/usr/bin/env python3
"""
CorretorIA - Aplicação Unificada
Contém:
- Ingestão de dados (Linktree -> JSONL)
- Processamento de PDFs
- Validação da base de conhecimento
- Serviços de Agente e Catálogo
- API Web (FastAPI)
- CLI para execução

Como usar:
  python corretor_ai.py server      # Inicia o servidor web
  python corretor_ai.py ingest      # Executa ingestão de dados
  python corretor_ai.py validate    # Valida a base de dados
  python corretor_ai.py examples    # Roda exemplos de uso
  python corretor_ai.py init-db     # Inicializa o banco de dados SQL
  python corretor_ai.py extract     # Apenas extrai e visualiza links (modo dry-run)
"""

import os
import sys
import json
import csv
import re
import io
import asyncio
import hashlib
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Dict, Set, Union

# Bibliotecas Externas
# Certifique-se de instalar: pip install fastapi uvicorn sqlalchemy pydantic-settings playwright httpx pymupdf beautifulsoup4 aiosqlite greenlet
import httpx
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi import FastAPI
import uvicorn
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy import String, Text, DateTime, func, select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# ============================================================================
# 1. CONFIGURAÇÃO (app/core/config.py)
# ============================================================================

class Settings(BaseSettings):
    APP_NAME: str = "CorretorIA"
    DB_URL: str = "sqlite+aiosqlite:///./corretor.db"

    OPENAI_API_KEY: str | None = None
    MODEL_NAME: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )

settings = Settings()

# ============================================================================
# 2. BANCO DE DADOS (app/db/models.py, app/db/session.py, app/db/init_db.py)
# ============================================================================

class Base(DeclarativeBase):
    pass

class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    contact_id: Mapped[str] = mapped_column(String(80), index=True)
    stage: Mapped[str] = mapped_column(String(40), default="novo")
    profile_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

# Engine e Session
engine = create_async_engine(settings.DB_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    """Inicializa as tabelas do banco de dados."""
    print(f"Inicializando banco de dados em {settings.DB_URL}...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Banco de dados inicializado.")

# ============================================================================
# 3. SERVIÇOS: CATÁLOGO (app/services/catalog.py)
# ============================================================================

CATALOG_DATA_PATH = Path("data/catalog.csv")

def load_catalog() -> list[dict[str, Any]]:
    if not CATALOG_DATA_PATH.exists():
        return []
    with CATALOG_DATA_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]

def match_properties(
    bairro: str | None,
    renda: float | None,
    entrada: float | None,
    fgts: bool | None,
    mcmv: bool | None,
    tipo: str | None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    items = load_catalog()

    def to_float(x: str) -> float:
        try:
            return float(x)
        except Exception:
            return 0.0

    results = []
    for it in items:
        if bairro and it["bairro"].strip().lower() != bairro.strip().lower():
            continue
        if tipo and it["tipo"].strip().lower() != tipo.strip().lower():
            continue

        renda_min = to_float(it.get("renda_min", "0"))
        entrada_min = to_float(it.get("entrada_min", "0"))
        preco = to_float(it.get("preco", "0"))

        if renda is not None and renda < renda_min:
            continue
        if entrada is not None and entrada < entrada_min:
            continue

        fgts_aceita = (it.get("fgts_aceita", "nao").lower() == "sim")
        if fgts is True and not fgts_aceita:
            continue

        is_mcmv = (it.get("mcmv", "nao").lower() == "sim")
        if mcmv is True and not is_mcmv:
            continue

        # score simples (quanto mais “perto” do mínimo, mais relevante)
        score = 0.0
        if renda is not None:
            score += max(0.0, renda - renda_min)
        if entrada is not None:
            score += max(0.0, entrada - entrada_min)

        results.append((score, {**it, "preco": preco}))

    results.sort(key=lambda x: x[0])  # mais justo primeiro
    return [r[1] for r in results[:limit]]

# ============================================================================
# 4. SERVIÇOS: LEADS (app/services/lead_service.py)
# ============================================================================

DEFAULT_PROFILE = {
    "nome": None,
    "bairro": None,
    "tipo": None,
    "renda": None,
    "entrada": None,
    "fgts": None,
    "mcmv": None,
    "restricao_nome": None,
    "urgencia": None,
    "imoveis_sugeridos": [],
}

async def get_or_create_lead(contact_id: str) -> Lead:
    async with SessionLocal() as session:
        res = await session.execute(select(Lead).where(Lead.contact_id == contact_id))
        lead = res.scalar_one_or_none()
        if lead:
            return lead

        lead = Lead(contact_id=contact_id, stage="novo", profile_json=json.dumps(DEFAULT_PROFILE))
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        return lead

def _merge_profile(old: dict, new: dict) -> dict:
    merged = {**old}
    for k, v in new.items():
        if v is not None:
            merged[k] = v
    return merged

async def update_profile(contact_id: str, patch: dict) -> Lead:
    lead = await get_or_create_lead(contact_id)
    old = json.loads(lead.profile_json or "{}")
    merged = _merge_profile(old, patch)

    async with SessionLocal() as session:
        await session.execute(
            update(Lead)
            .where(Lead.contact_id == contact_id)
            .values(profile_json=json.dumps(merged))
        )
        await session.commit()

    lead.profile_json = json.dumps(merged)
    return lead

async def set_stage(contact_id: str, stage: str) -> Lead:
    lead = await get_or_create_lead(contact_id)
    async with SessionLocal() as session:
        await session.execute(
            update(Lead).where(Lead.contact_id == contact_id).values(stage=stage)
        )
        await session.commit()
    lead.stage = stage
    return lead

# ============================================================================
# 5. SERVIÇOS: AGENTE (app/services/agent.py)
# ============================================================================

def _parse_money(text: str) -> float | None:
    # parse simples: pega números e interpreta "3000", "3.000", "3k"
    t = text.lower().replace("r$", "").replace(".", "").replace(",", ".").strip()
    if "k" in t:
        try:
            return float(t.replace("k", "")) * 1000
        except Exception:
            return None
    nums = "".join(ch for ch in t if (ch.isdigit() or ch == "."))
    try:
        return float(nums) if nums else None
    except Exception:
        return None

def _contains_yes(text: str) -> bool | None:
    t = text.lower()
    if any(x in t for x in ["sim", "tenho", "possuo", "yes", "s"]):
        return True
    if any(x in t for x in ["não", "nao", "negativo", "n"]):
        return False
    return None

async def handle_message(contact_id: str, text: str) -> dict:
    lead = await get_or_create_lead(contact_id)
    profile = json.loads(lead.profile_json or "{}")

    t = text.strip().lower()

    # Capturas rápidas por palavras-chave (MVP)
    patch = {}

    if profile.get("renda") is None and (any(x in t for x in ["renda", "salário", "salario", "ganho", "recebo"]) or t.isdigit()):
        val = _parse_money(text)
        if val:
            patch["renda"] = val

    if profile.get("entrada") is None and any(x in t for x in ["entrada", "dou", "tenho", "guardei", "juntei"]):
        val = _parse_money(text)
        if val:
            patch["entrada"] = val

    if profile.get("fgts") is None and "fgts" in t:
        patch["fgts"] = _contains_yes(text)

    if profile.get("mcmv") is None and any(x in t for x in ["mcmv", "minha casa", "casa verde", "subsídio", "subsidio"]):
        patch["mcmv"] = True

    if profile.get("tipo") is None and any(x in t for x in ["apartamento", "apto"]):
        patch["tipo"] = "Apartamento"
    if profile.get("tipo") is None and "casa" in t:
        patch["tipo"] = "Casa"

    # bairros (bem básico, depois vira lista/IA)
    if profile.get("bairro") is None:
        for b in ["campo grande", "jacarepaguá", "jacarepagua", "recreio"]:
            if b in t:
                patch["bairro"] = "Jacarepaguá" if "jacare" in b else b.title()

    if patch:
        lead = await update_profile(contact_id, patch)
        profile = json.loads(lead.profile_json or "{}")

    # Máquina de estados simples (consultor por etapas)
    await set_stage(contact_id, "qualificando")

    if profile.get("bairro") is None:
        return {"reply": "Perfeito. Pra eu te indicar só o que faz sentido, qual bairro ou região você quer (e se aceita regiões próximas)?"}

    if profile.get("tipo") is None:
        return {"reply": "Show. Você prefere **apartamento** ou **casa**?"}

    if profile.get("renda") is None:
        return {"reply": "Boa. Qual sua **renda mensal aproximada** (pode ser uma faixa, tipo 3.5k, 5k)?"}

    if profile.get("entrada") is None:
        return {"reply": "E de **entrada**, quanto você consegue colocar agora (mesmo que estimado)?"}

    if profile.get("fgts") is None:
        return {"reply": "Você tem **FGTS** pra usar na compra? (sim/não)"}

    if profile.get("restricao_nome") is None:
        return {"reply": "Última pra eu fechar o cenário: hoje você tem alguma **restrição no nome** (SPC/Serasa)? (sim/não)"}

    # Se chegou aqui, o lead já está “quase pronto” no MVP
    await set_stage(contact_id, "ofertando")

    props = match_properties(
        bairro=profile.get("bairro"),
        renda=profile.get("renda"),
        entrada=profile.get("entrada"),
        fgts=profile.get("fgts"),
        mcmv=profile.get("mcmv"),
        tipo=profile.get("tipo"),
        limit=3,
    )

    if not props:
        return {"reply": "Com o seu perfil, eu não encontrei uma opção perfeita no catálogo de teste ainda. Quer que eu amplie para bairros próximos ou ajuste o tipo (casa/apto)?"}

    lines = []
    for p in props:
        lines.append(f"• **{p['nome']}** ({p['bairro']}) | {p['tipo']} | R$ {int(float(p['preco'])):,}".replace(",", "."))

    return {
        "reply": (
            "Fechou. Pelo que você me passou, essas opções tendem a encaixar bem:\n\n"
            + "\n".join(lines)
            + "\n\nSe você me confirmar **qual dessas te chamou mais atenção (1, 2 ou 3)**, eu já preparo o próximo passo pra visita/simulação com o corretor."
        )
    }

# ============================================================================
# 6. INGESTÃO E PROCESSAMENTO DE DADOS (ingest.py)
# ============================================================================

DATA_DIR = "data"

def limpar_texto(texto):
    """Limpa quebras e espaços excessivos."""
    if not texto:
        return ""
    # Remove múltiplos espaços/quebras e normalize
    s = re.sub(r"\s+", " ", texto)
    return s.strip()

def limpar_conteudo_html(html_content):
    """Extrai apenas o texto útil, removendo elementos de interface."""
    if not html_content:
        return ""

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        for noise in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form', 'iframe', 'noscript']):
            noise.decompose()
        texto = soup.get_text(separator=' ', strip=True)
        texto_limpo = " ".join(texto.split())
        return texto_limpo
    except Exception as e:
        print(f"⚠ Erro ao limpar HTML: {str(e)}")
        return ""

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

def classificar_link(url):
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

def salvar_para_base_conhecimento(dados_imovel, arquivo="data/base_conhecimento.jsonl"):
    os.makedirs(os.path.dirname(arquivo) or ".", exist_ok=True)
    try:
        with open(arquivo, 'a', encoding='utf-8') as f:
            linha = json.dumps(dados_imovel, ensure_ascii=False)
            f.write(linha + '\n')
    except Exception as e:
        print(f"⚠ Erro ao salvar documento JSONL: {str(e)}")

def slugify(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")

async def extrair_conteudo_profundo(browser_context, nome, url_pai):
    page = await browser_context.new_page()
    links_internos = []
    html_conteudo = ""

    try:
        print(f"--- Explorando: {nome} ---")
        await page.goto(url_pai, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1500)
        html_conteudo = await page.content()
        elementos = await page.query_selector_all('a')

        for el in elementos:
            try:
                texto = await el.inner_text()
                href = await el.get_attribute("href")
                if href and href.startswith('http'):
                    if not any(x in href.lower() for x in ['facebook', 'instagram', 'twitter', 'whatsapp', 'utm_', 'linkedin']):
                        tipo = classificar_link(href)
                        entry = {"texto": texto.strip() or "Sem título", "url": href, "tipo": tipo}

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
                                    entry['metadados'] = {'site_origem': nome, 'erro': dados_pdf.get('erro')}
                            except Exception as e:
                                entry['metadados'] = {'site_origem': nome, 'erro': str(e)}
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
    def __init__(self, max_concurrent=3):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    async def executar(self, funcao, *args):
        async with self.semaphore:
            return await funcao(*args)

async def executar_automacao_completa(apenas_extracao=False):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto("https://linktr.ee/rivaincorporadorario", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        all_links = await page.query_selector_all('a')
        excluded_patterns = ['#', 'javascript:', 'mailto:', 'tel:', 'utm_source', 'utm_medium', 'signup_intent', 'discover/trending', 'privacy', '/s/about']
        links_iniciais = []
        for elemento in all_links:
            titulo = await elemento.inner_text()
            url = await elemento.get_attribute("href")
            if not url or not titulo.strip() or url.startswith('/'): continue
            skip = False
            for pattern in excluded_patterns:
                if pattern in url.lower(): skip = True; break
            if not skip:
                links_iniciais.append({"titulo": titulo.strip(), "url": url})
        await page.close()

        print(f"Encontrados {len(links_iniciais)} links totais no Linktree")
        links_imoveis = [link for link in links_iniciais if 'vendas' in link['url'] or 'imovei' in link['titulo'].lower()]
        print(f"Explorando {len(links_imoveis)} imóveis/projetos...\n")

        mapa_final = {}
        limitador = LimitadorConcorrencia(max_concurrent=3)
        tarefas = []
        for item in links_imoveis:
            tarefas.append(limitador.executar(extrair_conteudo_profundo, context, item['titulo'], item['url']))

        resultados = await asyncio.gather(*tarefas, return_exceptions=True)

        for i, (item, resultado) in enumerate(zip(links_imoveis, resultados)):
            if isinstance(resultado, Exception):
                mapa_final[item['titulo']] = {"url_principal": item['url'], "links_internos": [], "erro": str(resultado), "html_limpo": ""}
            else:
                links_internos, html_conteudo = resultado
                mapa_final[item['titulo']] = {
                    "url_principal": item['url'],
                    "links_internos": links_internos,
                    "html_limpo": limpar_conteudo_html(html_conteudo) if not apenas_extracao else ""
                }

        await browser.close()

        # Exibição
        for site, dados in mapa_final.items():
            print(f"\n📍 {site} ({dados['url_principal']})")
            print(f"Total de sublinks: {len(dados['links_internos'])}")
            if apenas_extracao:
                 links_por_tipo = {}
                 for sub in dados['links_internos']:
                     tipo = sub['tipo']
                     if tipo not in links_por_tipo: links_por_tipo[tipo] = []
                     links_por_tipo[tipo].append(sub)
                 for tipo, links in sorted(links_por_tipo.items()):
                     print(f"  {tipo}: {len(links)} links")

        return mapa_final

async def download_bytes(client: httpx.AsyncClient, url: str, timeout: int = 30):
    r = await client.get(url, follow_redirects=True, timeout=timeout)
    r.raise_for_status()
    return r.content

def _extract_drive_file_ids_from_html(html: str):
    ids = set()
    for m in re.finditer(r"/file/d/([a-zA-Z0-9_-]{10,})", html): ids.add(m.group(1))
    for m in re.finditer(r"[?&]id=([a-zA-Z0-9_-]{10,})", html): ids.add(m.group(1))
    return list(ids)

def drive_file_direct_url(file_id: str):
    return f"https://drive.google.com/uc?export=download&id={file_id}"

def dropbox_direct_url(url: str):
    if 'dropbox.com' in url:
        if 'dl=0' in url: return url.replace('dl=0', 'dl=1')
        if 'dl=1' in url: return url
        return url + '&dl=1' if '?' in url else url + '?dl=1'
    return url

async def resolve_drive_links(url: str, client: httpx.AsyncClient):
    urls = []
    if 'drive.google.com' in url:
        m = re.search(r"/file/d/([a-zA-Z0-9_-]{10,})", url)
        if m: return [drive_file_direct_url(m.group(1))]
        m = re.search(r"[?&]id=([a-zA-Z0-9_-]{10,})", url)
        if m: return [drive_file_direct_url(m.group(1))]
        if '/drive/folders/' in url or '/folders/' in url:
            try:
                r = await client.get(url, follow_redirects=True, timeout=20)
                r.raise_for_status()
                ids = _extract_drive_file_ids_from_html(r.text)
                return [drive_file_direct_url(fid) for fid in ids]
            except Exception: return []
    return urls

async def process_pdf(item, site_slug, site_nome, client: httpx.AsyncClient):
    url = item["url"]
    nome = url.split("/")[-1].split("?")[0] or f"file_{hashlib.sha1(url.encode()).hexdigest()}.pdf"
    raw_dir = os.path.join(DATA_DIR, "raw", site_slug)
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, nome)

    result = {"source_url": url, "site_origem": site_nome, "arquivo": nome, "status": "unknown"}
    try:
        content = await download_bytes(client, url)
        with open(raw_path, "wb") as fh: fh.write(content)
        sha = hashlib.sha256(content).hexdigest()

        texto_pages = []
        with fitz.open(stream=io.BytesIO(content), filetype="pdf") as doc:
            for p in doc: texto_pages.append(p.get_text())
        texto_clean = limpar_texto("\n".join(texto_pages).strip())
        chunks = chunk_text(texto_clean, chunk_size=1000, overlap=200)

        extracted_dir = os.path.join(DATA_DIR, "extracted", site_slug)
        os.makedirs(extracted_dir, exist_ok=True)
        jsonl_path = os.path.join(extracted_dir, f"{nome}.jsonl")

        with open(jsonl_path, "w", encoding="utf-8") as fh:
            for idx, c in enumerate(chunks):
                item_json = {
                    "id": f"{nome}#chunk{idx}", "source_url": url, "site_origem": site_nome,
                    "site_slug": site_slug, "arquivo": nome, "chunk_index": idx,
                    "total_chunks": len(chunks), "texto": c, "crawl_date": datetime.utcnow().isoformat(), "sha256": sha
                }
                fh.write(json.dumps(item_json, ensure_ascii=False) + "\n")
                salvar_para_base_conhecimento(item_json)

        result["status"] = "sucesso"
    except Exception as e:
        result["status"] = "erro"; result["erro"] = str(e)
    return result

async def run_ingestion():
    print("\n" + "="*80 + "\n 🏢 SISTEMA DE INGESTÃO DE DADOS - RIVA INCORPORADORA\n" + "="*80)
    print("📊 ETAPA 1: Extração de dados dos imóveis...\n")
    mapa = await executar_automacao_completa(apenas_extracao=False)

    print("\n📊 ETAPA 2: Processando documentos e criando base de conhecimento...\n")
    tasks = []
    async with httpx.AsyncClient() as client:
        for site, dados in mapa.items():
            site_slug = slugify(site)
            if dados.get('html_limpo'):
                salvar_para_base_conhecimento({
                    "id": f"{site_slug}_pagina_principal", "source_url": dados['url_principal'],
                    "site_origem": site, "site_slug": site_slug, "type": "página_principal",
                    "texto": dados['html_limpo'], "crawl_date": datetime.utcnow().isoformat()
                })

            for sub in dados.get("links_internos", []):
                tipo = sub.get("tipo", "")
                url = sub.get("url", "")
                if 'dropbox.com' in url:
                    direct = dropbox_direct_url(url)
                    if direct.lower().endswith('.pdf'):
                        tasks.append(process_pdf({'url': direct}, site_slug, site, client))
                elif 'drive.google.com' in url:
                    resolved = await resolve_drive_links(url, client)
                    for pdf_url in resolved:
                        tasks.append(process_pdf({'url': pdf_url}, site_slug, site, client))
                elif (tipo == "📄 Documento" and url.lower().endswith('.pdf')):
                    tasks.append(process_pdf(sub, site_slug, site, client))

        results = []
        CONC = 4
        for i in range(0, len(tasks), CONC):
            batch = tasks[i:i+CONC]
            results.extend(await asyncio.gather(*batch))

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "ingest_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    print("✅ Ingest finished!")

async def run_extraction():
    print("\n🔍 MODO EXTRAÇÃO (Dry-Run)\n")
    await executar_automacao_completa(apenas_extracao=True)

# ============================================================================
# 7. VALIDAÇÃO (validar_base.py)
# ============================================================================

def validar_base_conhecimento():
    print("\n🚀 VALIDAÇÃO DA BASE DE CONHECIMENTO\n")
    arquivo = "data/base_conhecimento.jsonl"
    if not os.path.exists(arquivo):
        print(f"❌ Arquivo não encontrado: {arquivo}"); return

    total_linhas = 0; erros = 0; total_chars = 0
    sites = set()
    with open(arquivo, 'r', encoding='utf-8') as f:
        for i, linha in enumerate(f, 1):
            try:
                doc = json.loads(linha)
                total_linhas += 1
                total_chars += len(doc.get('texto', ''))
                sites.add(doc.get('site_origem', 'Unknown'))
            except Exception as e:
                erros += 1

    print(f"✅ Arquivo válido!\n📄 Docs: {total_linhas}\n📊 Chars: {total_chars}\n🏢 Sites: {len(sites)}")
    if erros > 0: print(f"⚠️ {erros} linhas com erro.")

# ============================================================================
# 8. EXEMPLOS (exemplos_uso.py)
# ============================================================================

def run_examples():
    print("\n📚 EXEMPLOS DE USO\n")
    arquivo = "data/base_conhecimento.jsonl"
    if not os.path.exists(arquivo): print("Base não encontrada."); return

    print("--- Exemplo 1: Primeiros 2 documentos ---")
    with open(arquivo, 'r', encoding='utf-8') as f:
        for i, linha in enumerate(f):
            if i >= 2: break
            doc = json.loads(linha)
            print(f"[{i+1}] {doc.get('site_origem')} - {doc.get('arquivo')}")

    print("\n--- Exemplo 2: Busca por 'área' ---")
    palavra = "área"
    count = 0
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            if palavra in linha.lower(): count += 1
    print(f"Documentos contendo '{palavra}': {count}")

# ============================================================================
# 9. APLICAÇÃO WEB (app/main.py)
# ============================================================================

app = FastAPI(title="CorretorIA - MVP")

class MessageIn(BaseModel):
    contact_id: str
    text: str

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/")
async def root():
    return {"name": "CorretorIA", "status": "running", "docs": "/docs"}

@app.post("/chat")
async def chat(payload: MessageIn):
    result = await handle_message(payload.contact_id, payload.text)
    return {"contact_id": payload.contact_id, **result}

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)

# ============================================================================
# 10. CLI (ENTRY POINT)
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CorretorIA - Ferramenta Unificada")
    parser.add_argument("command", choices=["server", "ingest", "extract", "validate", "examples", "init-db"], help="Comando a executar")

    args = parser.parse_args()

    if args.command == "server":
        run_server()
    elif args.command == "ingest":
        asyncio.run(run_ingestion())
    elif args.command == "extract":
        asyncio.run(run_extraction())
    elif args.command == "validate":
        validar_base_conhecimento()
    elif args.command == "examples":
        run_examples()
    elif args.command == "init-db":
        asyncio.run(init_db())
