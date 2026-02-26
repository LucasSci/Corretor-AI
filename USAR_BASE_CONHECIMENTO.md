# 🧠 Guia: Como Usar a Base de Conhecimento (JSONL)

## 1. O que é base_conhecimento.jsonl?

Um arquivo **JSONL** (JSON Lines) contém múltiplos objetos JSON, um por linha. É o formato padrão ouro para:
- **Streaming em larga escala** (processar linha por linha sem carregar tudo na memória)
- **Vector Databases** (Pinecone, Weaviate, ChromaDB, Milvus)
- **RAG Pipelines** (Retrieval-Augmented Generation com LLMs)
- **LangChain & LlamaIndex** (frameworks de IA modernos)

## 2. Estrutura de uma Linha (Entidade)

```json
{
  "id": "documento.pdf#chunk0",
  "source_url": "https://drive.google.com/...",
  "site_origem": "Empreendimento Apogeu Barra",
  "site_slug": "apogeu_barra_linktree",
  "arquivo": "documento.pdf",
  "chunk_index": 0,
  "total_chunks": 15,
  "texto": "A altura máxima do edifício é de 45 metros conforme projeto arquitetônico...",
  "crawl_date": "2026-02-26T10:30:45.123456",
  "sha256": "a1b2c3d4e5f6..."
}
```

### Campos Explicados

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | string | Identificador único (arquivo + chunk) |
| `source_url` | string | URL original do documento |
| `site_origem` | string | Nome do empreendimento |
| `site_slug` | string | Versão normalizada para URLs/IDs |
| `arquivo` | string | Nome do arquivo PDF/documento |
| `chunk_index` | int | Índice do pedaço (0, 1, 2...) |
| `total_chunks` | int | Total de pedaços deste documento |
| `texto` | string | **Conteúdo limpo** (pronto para embedding) |
| `crawl_date` | ISO 8601 | Timestamp quando foi extraído |
| `sha256` | string | Hash para detectar duplicatas |

---

## 3. Como Ler o Arquivo

### 3.1 Leitura Básica (Python)

```python
import json

def ler_base_conhecimento(arquivo="data/base_conhecimento.jsonl"):
    """Lê o arquivo JSONL linha por linha."""
    linhas_lidas = 0
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            if linha.strip():  # Ignora linhas vazias
                documento = json.loads(linha)
                linhas_lidas += 1
                print(f"[{linhas_lidas}] {documento['id']}: {documento['texto'][:80]}...")

ler_base_conhecimento()
```

### 3.2 Filtrar por Site

```python
def obter_documentos_por_site(site_slug, arquivo="data/base_conhecimento.jsonl"):
    """Retorna todos os chunks de um empreendimento específico."""
    documentos = []
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            doc = json.loads(linha)
            if doc['site_slug'] == site_slug:
                documentos.append(doc)
    return documentos

# Exemplo
docs_apogeu = obter_documentos_por_site("apogeu_barra_linktree")
print(f"Encontrados {len(docs_apogeu)} chunks do Apogeu Barra")
```

### 3.3 Busca por Palavra-chave

```python
def buscar_texto(palavra_chave, arquivo="data/base_conhecimento.jsonl"):
    """Busca simples por substring (sem índice, mais lento mas funciona)."""
    resultados = []
    palavra_chave = palavra_chave.lower()
    
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            doc = json.loads(linha)
            if palavra_chave in doc['texto'].lower():
                resultados.append(doc)
    
    return resultados

# Exemplo
docs = buscar_texto("área total")
for doc in docs[:5]:
    print(f"\n🏢 {doc['site_origem']} ({doc['arquivo']})")
    print(f"   {doc['texto'][:150]}...")
```

---

## 4. Integração com Vector Database (ChromaDB)

### 4.1 Instalação

```bash
pip install chromadb langchain langchain-openai
```

### 4.2 Código de Integração

```python
import json
import chromadb
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.docstore.document import Document

# 1. Carregar JSONL
def carregar_jsonl_como_documents(arquivo):
    """Converte JSONL para formato LangChain Document."""
    docs = []
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            entrada = json.loads(linha)
            doc = Document(
                page_content=entrada['texto'],
                metadata={
                    'id': entrada['id'],
                    'source': entrada['source_url'],
                    'site': entrada['site_origem'],
                    'arquivo': entrada['arquivo'],
                    'chunk_index': entrada['chunk_index']
                }
            )
            docs.append(doc)
    return docs

# 2. Inicializar ChromaDB
client = chromadb.Client()
collection = client.get_or_create_collection(
    name="riva_imoveis",
    metadata={"hnsw:space": "cosine"}
)

# 3. Carregar documentos
documents = carregar_jsonl_como_documents("data/base_conhecimento.jsonl")
print(f"✅ Carregados {len(documents)} documentos")

# 4. Embeddings (usar OpenAI ou HuggingFace)
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

# 5. Adicionar ao ChromaDB
for i, doc in enumerate(documents):
    embedding = embeddings.embed_query(doc.page_content)
    collection.add(
        ids=[doc.metadata['id']],
        embeddings=[embedding],
        metadatas=[doc.metadata],
        documents=[doc.page_content]
    )
    if (i + 1) % 100 == 0:
        print(f"   → Indexados {i + 1}/{len(documents)} documentos")

print("✅ Base indexada com sucesso!")
```

### 4.3 Busca Vetorial

```python
def buscar_na_base(pergunta, collection, embeddings, top_k=5):
    """Busca semântica na base de conhecimento."""
    # Embedar a pergunta
    embedding_pergunta = embeddings.embed_query(pergunta)
    
    # Buscar no ChromaDB
    resultados = collection.query(
        query_embeddings=[embedding_pergunta],
        n_results=top_k
    )
    
    return resultados

# Exemplo
pergunta = "Qual é a altura máxima do edifício?"
resultados = buscar_na_base(pergunta, collection, embeddings)

print(f"📍 Encontrados {len(resultados['documents'][0])} resultados:\n")
for i, (doc, metadata) in enumerate(zip(
    resultados['documents'][0], 
    resultados['metadatas'][0]
)):
    print(f"{i+1}. 📄 {metadata['arquivo']} ({metadata['site']})")
    print(f"   {doc[:150]}...\n")
```

---

## 5. Integração com LLM (Gemini + RAG)

### 5.1 Setup

```bash
pip install google-generativeai langchain-google-genai
```

### 5.2 Chat com RAG

```python
import google.generativeai as genai
from langchain.chains import RetrievalQA
from langchain.llms import GoogleGenerativeAI
from langchain.vectorstores import Chroma

# Configurar API
genai.configure(api_key="sua_chave_aqui")

# Inicializar LLM
llm = GoogleGenerativeAI(model="gemini-pro", temperature=0.3)

# Criar cadeia RAG
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
    return_source_documents=True
)

# Fazer pergunta
pergunta = "Qual é a planta do apartamento de 2 quartos no Apogeu Barra?"
resultado = qa_chain({"query": pergunta})

print("🤖 Resposta do Bot:")
print(resultado['result'])

print("\n📚 Fontes usadas:")
for doc in resultado['source_documents']:
    print(f"  - {doc.metadata['arquivo']} ({doc.metadata['site']})")
```

---

## 6. Uso com n8n (Webhooks)

### 6.1 Webhook Custom para Buscar na Base

```javascript
// n8n - HTTP Request Node
// Método: POST
// URL: http://seu-servidor:8000/buscar_base

const consulta = $json['query'];
const top_k = 5;

// Faz busca GET para seu serviço Python
const resposta = await fetch(`http://localhost:5000/search?q=${consulta}&k=${top_k}`);
const dados = await resposta.json();

return {
    json: dados
};
```

### 6.2 Server Python para Suportar n8n

```python
from flask import Flask, request, jsonify
import json
import chromadb
from langchain.embeddings import OpenAIEmbeddings

app = Flask(__name__)

# Inicializar ChromaDB (executar uma vez)
client = chromadb.Client()
collection = client.get_or_create_collection("riva_imoveis")
embeddings = OpenAIEmbeddings()

@app.route('/search', methods=['GET'])
def search():
    q = request.args.get('q', '')
    k = request.args.get('k', 5, type=int)
    
    if not q:
        return jsonify({"erro": "Query vazia"}), 400
    
    # Buscar
    embedding = embeddings.embed_query(q)
    resultados = collection.query(
        query_embeddings=[embedding],
        n_results=k
    )
    
    # Formatar resposta
    resposta = {
        "query": q,
        "resultados": [
            {
                "texto": doc[:200],
                "site": meta['site'],
                "arquivo": meta['arquivo']
            }
            for doc, meta in zip(
                resultados['documents'][0],
                resultados['metadatas'][0]
            )
        ]
    }
    
    return jsonify(resposta)

if __name__ == '__main__':
    app.run(port=5000)
```

---

## 7. Monitoramento e Manutenção

### 7.1 Validar Integridade

```python
def validar_base(arquivo="data/base_conhecimento.jsonl"):
    """Verifica a saúde do arquivo JSONL."""
    total_linhas = 0
    erros = 0
    total_caracteres = 0
    sites_unicos = set()
    
    with open(arquivo, 'r', encoding='utf-8') as f:
        for num_linha, linha in enumerate(f, 1):
            try:
                doc = json.loads(linha)
                total_linhas += 1
                total_caracteres += len(doc.get('texto', ''))
                sites_unicos.add(doc.get('site_slug'))
            except json.JSONDecodeError:
                erros += 1
                print(f"❌ Erro na linha {num_linha}")
    
    print(f"""
    📊 Relatório da Base de Conhecimento
    ====================================
    ✅ Total de documentos: {total_linhas}
    ❌ Erros: {erros}
    📄 Total de caracteres: {total_caracteres:,.0f}
    🏢 Empreendimentos únicos: {len(sites_unicos)}
    """)
    
    return total_linhas, erros

validar_base()
```

### 7.2 Atualizar a Base (Modo Incremental)

```python
def adicionar_novo_documento(novo_doc, arquivo="data/base_conhecimento.jsonl"):
    """Adiciona um novo documento à base (sem duplicar)."""
    doc_id = novo_doc['id']
    
    # Verificar se já existe
    ids_existentes = set()
    with open(arquivo, 'r', encoding='utf-8') as f:
        for linha in f:
            doc = json.loads(linha)
            ids_existentes.add(doc['id'])
    
    if doc_id in ids_existentes:
        print(f"⚠️ Documento {doc_id} já existe!")
        return False
    
    # Adicionar novo
    with open(arquivo, 'a', encoding='utf-8') as f:
        f.write(json.dumps(novo_doc, ensure_ascii=False) + '\n')
    
    print(f"✅ Documento {doc_id} adicionado!")
    return True
```

---

## 8. Dicas Avançadas

### 8.1 Deduplicação

```python
def remover_duplicatas(arquivo_entrada, arquivo_saida):
    """Remove chunks duplicados baseado em SHA256."""
    shas_vistas = set()
    
    with open(arquivo_entrada, 'r') as entrada, \
         open(arquivo_saida, 'w') as saida:
        for linha in entrada:
            doc = json.loads(linha)
            sha = doc.get('sha256')
            
            if sha not in shas_vistas:
                shas_vistas.add(sha)
                saida.write(json.dumps(doc, ensure_ascii=False) + '\n')
    
    print(f"✅ Duplicatas removidas! {len(shas_vistas)} documentos únicos.")
```

### 8.2 Exportar para Otros Formatos

```python
def exportar_para_csv(arquivo_jsonl, arquivo_csv):
    """Converte JSONL para CSV (útil para análise em Excel)."""
    import csv
    
    with open(arquivo_jsonl, 'r') as f_in, \
         open(arquivo_csv, 'w', encoding='utf-8', newline='') as f_out:
        
        writer = None
        for linha in f_in:
            doc = json.loads(linha)
            
            if writer is None:
                writer = csv.DictWriter(f_out, fieldnames=doc.keys())
                writer.writeheader()
            
            writer.writerow(doc)
    
    print(f"✅ Exportado para {arquivo_csv}")
```

---

## 9. Próximos Passos

✅ **Feito:**
- [ ] Executar `python ingest.py`
- [ ] Gerar `data/base_conhecimento.jsonl`

⏭️ **Próximo:**
- [ ] Configurar ChromaDB com embeddings
- [ ] Testar buscas semânticas
- [ ] Integrar com Gemini via n8n
- [ ] Lançar chat bot em produção

---

**Dúvidas?** Consulte a documentação principal em `README.MD`
