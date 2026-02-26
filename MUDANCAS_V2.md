# ✨ Resumo das Mudanças - Integração v2.0

## What Changed (O que mudou)

### 📦 Antes (v1.0)
- 2 arquivos separados: `extract.py` + `ingest.py`
- Código duplicado entre os dois
- HTML bruto sendo armazenado sem limpeza
- Sem integração com bases vetoriais
- Foco apenas em download de PDFs

### 🚀 Agora (v2.0) 
- **1 arquivo único**: `ingest.py` consolidado e organizado
- **Código limpo** sem duplicação
- **HTML limpo** automaticamente antes de ser salvo
- **JSONL gerado** pronto para Vector Databases (RAG)
- **Função nova**: `limpar_conteudo_html()` remove ruído
- **Função nova**: `salvar_para_base_conhecimento()` integra JSONL
- **Melhor documentação** (README + guia de uso)

---

## 📊 Arquivo Consolidado: ingest.py

Está organizado em **6 seções lógicas**:

```
SEÇÃO 1: Limpeza e Processamento de Texto
  ├─ limpar_texto()
  ├─ limpar_conteudo_html()  ⭐ NOVO
  └─ chunk_text()

SEÇÃO 2: Classificação e Extração
  ├─ classificar_link()
  └─ extrair_texto_pdf()

SEÇÃO 3: Armazenamento JSONL
  └─ salvar_para_base_conhecimento()  ⭐ NOVO

SEÇÃO 4: Web Scraping
  ├─ slugify()
  ├─ extrair_conteudo_profundo()
  ├─ LimitadorConcorrencia
  └─ executar_automacao_completa()

SEÇÃO 5: Processamento de PDFs
  ├─ download_bytes()
  ├─ resolve_drive_links()
  ├─ dropbox_direct_url()
  └─ process_pdf()

SEÇÃO 6: Orquestração (main)
  └─ main()  ⭐ REFATORIZADO
```

---

## 🧠 Novas Funcionalidades

### 1️⃣ Limpeza de HTML (limpar_conteudo_html)

**Antes:**
```python
# Não tinha função para limpar
html_bruto = await page.content()
# Salva com menu, footer, script, etc.
```

**Agora:**
```python
html_bruto = await page.content()
html_limpo = limpar_conteudo_html(html_bruto)
# Remove <script>, <style>, <header>, <footer>, <nav>, etc.
# Deixa apenas texto relevante para embedding
```

**Por que?** 
- Menus e rodapés prejudicam a qualidade dos embeddings (RAG)
- Aumenta ruído em buscas semânticas
- Economia de espaço no Vector DB

---

### 2️⃣ Base de Conhecimento em JSONL (salvar_para_base_conhecimento)

**Antes:**
```python
# Salvava JSONL por site, em múltiplos arquivos
os.path.join(DATA_DIR, "extracted", site_slug, f"{nome}.jsonl")
# Resultado: ingest_summary.json desconexo
```

**Agora:**
```python
# Todas as entidades em 1 arquivo central
salvar_para_base_conhecimento(documento_final)
# Arquivo: data/base_conhecimento.jsonl
```

**Benefícios:**
- ✅ Um único arquivo para alimentar Vector DB
- ✅ Streaming (processa linha por linha)
- ✅ Pronto para ChromaDB/Pinecone/Weaviate
- ✅ Compatível com LangChain/LlamaIndex

---

## 📁 Estrutura de Dados Gerada

```
data/
├── base_conhecimento.jsonl          ⭐ NOVO - Central!
│   └── {"id": "doc#chunk0", "texto": "...", ...}
│   └── {"id": "doc#chunk1", "texto": "...", ...}
│   └── ... (milhões de linhas se necessário)
│
├── ingest_summary.json              (sem mudanças)
├── raw/                             (sem mudanças)
└── extracted/                       (mantém múltiplos JSONL por PDFs)
```

---

## 🔄 Fluxo Atualizado da main()

```
┌─────────────────────────────────────┐
│ ETAPA 1: Extração de Imóveis        │
│   executar_automacao_completa()     │
│   → Retorna mapa com HTMLs brutos   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ ETAPA 2: Processamento & Limpeza    │
│   Para cada imóvel:                 │
│   1. limpar_conteudo_html()         │ ⭐ NOVO
│   2. salvar_para_base_conhecimento()│ ⭐ NOVO
│   3. process_pdf() para cada PDF    │
│   4. Chunks + escreve JSONL central │ ⭐ NOVO
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ ETAPA 3: Sumário e Finalização      │
│   → ingest_summary.json             │
│   → base_conhecimento.jsonl pronto  │ ⭐ NOVO
└─────────────────────────────────────┘
```

---

## 🎯 Como Usar

### Executar Tudo

```bash
python ingest.py
```

Isso faz:
1. ✅ Extrai dados do Linktree
2. ✅ Limpa HTML de cada página
3. ✅ Processa PDFs (Drive, Dropbox, diretos)
4. ✅ Gera chunks com overlap
5. ✅ Salva em JSONL central + sumário

### Consumir a Base

```python
# Ler o arquivo JSONL
import json
with open("data/base_conhecimento.jsonl") as f:
    for linha in f:
        doc = json.loads(linha)
        print(doc['id'], doc['site_origem'])
```

Ou com LangChain:
```python
from langchain.document_loaders import JSONLoader
docs = JSONLoader("data/base_conhecimento.jsonl", ...).load()
```

---

## ✅ Checklist do Projeto

- [x] Consolidar `extract.py` + `ingest.py` em um arquivo
- [x] Adicionar `limpar_conteudo_html()`
- [x] Adicionar `salvar_para_base_conhecimento()`
- [x] Integrar limpeza de HTML no fluxo
- [x] Gerar JSONL central
- [x] Atualizar README.MD
- [x] Criar guia de uso (USAR_BASE_CONHECIMENTO.md)
- [x] Adicionar BeautifulSoup ao requirements.txt
- [x] Testar sintaxe do código
- [ ] Executar `python ingest.py` em produção
- [ ] Indexar JSONL em ChromaDB/Pinecone
- [ ] Integrar com Gemini via n8n

---

## 🚀 Próximos Passos Recomendados

### Imediato (Esta semana)
1. Executar `python ingest.py`
2. Validar `data/base_conhecimento.jsonl`
3. Testar leitura com script Python

### Curto Prazo (Próximas 2 semanas)
1. Setup ChromaDB local
2. Indexar JSONL no ChromaDB
3. Testar buscas semânticas

### Médio Prazo (Próximo mês)
1. Integrar com LangChain + Gemini
2. Configurar webhooks no n8n
3. Teste A/B com bot real

---

## 📞 Dúvidas Frequentes

**P: Por que JSONL e não CSV/Excel?**
A: JSONL permite streaming (linha por linha) sem carregar tudo na RAM. Ideal para milhões de registros.

**P: Posso usar a base com ChatGPT direto?**
A: Não recomendado. Use com ChromaDB/Pinecone primeiro (vetorização), depois conecte ao ChatGPT via n8n.

**P: Preciso deletar arquivo antigo (extract.py)?**
A: Sim! Agora tudo está em `ingest.py`. Se quiser manter backup, renomeie.

**P: Como faço atualizações incrementais?**
A: Use `salvar_para_base_conhecimento()` diretamente. O arquivo é append-only.

---

## 📚 Leia Também

- [README.md](README.MD) - Documentação completa
- [USAR_BASE_CONHECIMENTO.md](USAR_BASE_CONHECIMENTO.md) - Guia técnico de integração
- [requirements.txt](requirements.txt) - Dependências Python

---

**Status:** ✅ Implementação Completa  
**Data:** 2026-02-26  
**Versão:** 2.0 (Consolidação + JSONL)
