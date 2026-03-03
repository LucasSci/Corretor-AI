import json
import os
import pytest

# Define o caminho do arquivo gerado pelo seu scraper
ARQUIVO_BASE = "data/base_conhecimento.jsonl"

def carregar_dados():
    """Carrega as linhas do JSONL para os testes."""
    if not os.path.exists(ARQUIVO_BASE):
        return []
    with open(ARQUIVO_BASE, 'r', encoding='utf-8') as f:
        # Lê cada linha e converte de volta para dicionário Python
        return [json.loads(line.strip()) for line in f if line.strip()]

# Carrega os dados uma vez para usar em todos os testes
dados_extraidos = carregar_dados()

# --- OS TESTES ---

def test_arquivo_existe_e_tem_dados():
    """Garante que o scraper realmente gerou um arquivo e que ele não está vazio."""
    assert os.path.exists(ARQUIVO_BASE), "❌ O arquivo JSONL não foi encontrado!"
    assert len(dados_extraidos) > 0, "❌ O arquivo existe, mas está vazio!"

@pytest.mark.parametrize("chunk", dados_extraidos)
def test_schema_dos_dados(chunk):
    """Verifica se a estrutura de chaves (Schema) está correta em TODAS as linhas."""
    # Suportar esquemas antigos e novos: aceitar `id` ou `id_chunk`, e garantir `texto` presente
    assert ("id" in chunk) or ("id_chunk" in chunk), f"❌ Nenhuma chave de id encontrada no chunk: {chunk}"
    assert "texto" in chunk, f"❌ Chave 'texto' ausente no chunk: {chunk.get('id') or chunk.get('id_chunk', 'Desconhecido')}"

@pytest.mark.parametrize("chunk", dados_extraidos)
def test_schema_dos_metadados(chunk):
    """Garante que a IA terá o contexto necessário (nome do empreendimento, url, etc)."""
    # O arquivo atual pode ter metadados no topo ou campos espalhados. Aceitamos pelo menos
    # um dos identificadores de origem: 'site_origem', 'source_url', 'site_slug' ou 'arquivo'.
    possiveis = [
        "site_origem",
        "source_url",
        "site_slug",
        "arquivo",
        "nome_empreendimento",
        "tipo_fonte",
        "url_origem",
    ]
    metadados = chunk.get("metadados", {})
    assert any(k in chunk for k in possiveis) or any(k in metadados for k in possiveis), f"❌ Nenhum metadado de origem encontrado no chunk: {chunk.get('id') or chunk.get('id_chunk', 'Desconhecido')}"

@pytest.mark.parametrize("chunk", dados_extraidos)
def test_qualidade_do_texto(chunk):
    """Verifica se o 'Smart Chunking' funcionou e se o texto é válido para a IA."""
    texto = chunk.get("texto", "")
    
    # O texto não pode ser nulo ou apenas espaços
    assert isinstance(texto, str) and texto.strip() != "", "❌ Texto vazio ou inválido encontrado."

    # Ajustar limites para tipos diferentes. Permitir chunks bem pequenos (labels)
    # e também páginas completas que podem ser maiores.
    min_len = 4
    max_len = 4000
    assert len(texto) >= min_len, f"❌ Chunk muito curto ({len(texto)} chars). Pode ser ruído."
    assert len(texto) < max_len, f"❌ Chunk gigantesco ({len(texto)} chars). O particionamento falhou!"

@pytest.mark.parametrize("chunk", dados_extraidos)
def test_validade_das_urls(chunk):
    """Garante que a URL de origem não está quebrada ou vazia."""
    url = chunk.get("source_url") or chunk.get("url_origem") or chunk.get("metadados", {}).get("url_origem", "")
    # Se não houver URL, consideramos válido quando há pelo menos um campo de origem (ex: 'arquivo' ou 'site_slug')
    if url:
        assert isinstance(url, str) and url.startswith("http"), f"❌ URL de origem inválida: {url}"
    else:
        assert any(k in chunk for k in ("arquivo", "site_slug", "site_origem")), f"❌ Nenhuma URL ou identificador de origem encontrado no chunk: {chunk.get('id') or chunk.get('id_chunk', 'Desconhecido')}"