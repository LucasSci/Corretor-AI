
---

## 🏢 Documentação do Projeto: Agente Imobiliário IA (Lead Specialist)

### 1. Visão Geral

O objetivo deste projeto é revolucionar o atendimento de leads imobiliários, eliminando o atraso na resposta e a sobrecarga do corretor humano. O sistema utilizará Inteligência Artificial para realizar a triagem, apresentação de produtos e agendamento de visitas de forma autônoma.

### 2. Objetivos Principais

* **Qualificação em Tempo Real:** Filtrar curiosos de compradores reais através de perguntas estratégicas de perfil.
* **Especialista em Produto:** Consultar uma base de dados técnica para responder dúvidas sobre metragens, valores e plantas sem erros.
* **Conversão Direta:** Realizar agendamentos no calendário do corretor.
* **Transbordo Inteligente:** Permitir que o corretor humano assuma o chat a qualquer momento via dashboard centralizado.

### 3. Arquitetura da Solução (Stack Técnica)

| Camada | Tecnologia | Função |
| --- | --- | --- |
| **Interface** | WhatsApp (via Evolution API) | Recepção e envio de mensagens. |
| **Orquestrador** | n8n | Lógica de fluxos e integração de APIs. |
| **IA Principal** | Gemini 1.5 Pro | Processamento de linguagem natural e tomada de decisão. |
| **Base de Dados** | RAG (Retrieval-Augmented Generation) com JSONL | Consulta a PDFs e tabelas de preços. |
| **Dashboard** | Chatwoot | Interface para intervenção humana e gestão de leads. |

---

## 📊 Sistema de Ingestão de Dados (NOVO - v2.0)

### 4. Visão Geral da Ingestão

O arquivo `ingest.py` é um **orquestrador completo** que realiza as seguintes tarefas:

1. **Extração de Dados:** Navega pelo Linktree da RIVA e descobre todos os imóveis
2. **Web Scraping Profundo:** Percorre cada imóvel e coleta links (PDFs, Drives, Dropbox, etc.)
3. **Limpeza de HTML:** Remove menus, rodapés, scripts e outros ruídos que comprometem a qualidade dos dados
4. **Processamento de PDFs:** Download, extração de texto, limpeza de formatação
5. **Chunking Inteligente:** Divide documentos em pedaços com overlap para melhor contextualização
6. **Armazenamento JSONL:** Salva dados em formato pronto para Vector Databases (RAG)

### 5. Estrutura de Arquivos Gerados

```
data/
├── base_conhecimento.jsonl          # 🧠 Base de conhecimento CENTRAL (todas as entidades)
├── ingest_summary.json              # 📋 Sumário do processamento
├── raw/                             # 📁 Cópias brutas dos PDFs (backup)
│   └── {site_slug}/
│       └── *.pdf
├── extracted/                       # 📁 Dados extraídos em JSONL
│   └── {site_slug}/
│       └── *.jsonl
└── ingest_summary.json              # Relatório final
```

### 6. Novas Funções Integradas

#### 6.1 Limpeza de HTML
```python
limpar_conteudo_html(html_content)
```
- Remove `<script>`, `<style>`, `<header>`, `<footer>`, `<nav>`, `<form>`, etc.
- Extrai apenas texto relevante para embedding em Vector DB
- Normaliza espaços em branco

#### 6.2 Base de Conhecimento (JSONL)
```python
salvar_para_base_conhecimento(dados_imovel, arquivo="data/base_conhecimento.jsonl")
```
- Salva cada entidade como uma linha JSON independente
- Permite processamento **streaming** sem carregar arquivo inteiro na memória
- Pronto para `ChromaDB`, `Pinecone`, `Weaviate`, etc.
- Formato ideal para **LangChain** e **LlamaIndex**

### 7. Como Usar

#### 7.1 Execução do Sistema Completo

```bash
python ingest.py
```

Isso irá:
1. Acessar o Linktree
2. Extrair dados de todos os imóveis
3. Processar PDFs (Google Drive, Dropbox e URLs diretas)
4. Gerar base de conhecimento em JSONL
5. Salvar sumário em JSON

#### 7.2 Estrutura de Dados JSONL

Cada linha do arquivo `data/base_conhecimento.jsonl` segue este padrão:

```json
{
  "id": "documento#chunk0",
  "source_url": "https://...",
  "site_origem": "Empreendimento X",
  "site_slug": "empreendimento_x",
  "arquivo": "documento.pdf",
  "chunk_index": 0,
  "total_chunks": 15,
  "texto": "Conteúdo limpo do documento...",
  "crawl_date": "2026-02-26T10:30:00",
  "sha256": "abcd1234..."
}
```

### 8. Integração com IA/RAG

Uma vez que o arquivo JSONL estiver pronto, você pode:

#### 8.1 Usar com LangChain
```python
from langchain.document_loaders import JSONLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Pinecone

# Carregar JSONL
loader = JSONLoader("data/base_conhecimento.jsonl", ...)
docs = loader.load()

# Embeder e salvar em Pinecone
embeddings = OpenAIEmbeddings()
vectorstore = Pinecone.from_documents(docs, embeddings, index_name="riva-imobiliario")
```

#### 8.2 Usar com ChromaDB (Local)
```python
import chromadb
from langchain.vectorstores import Chroma

# Conectar ao ChromaDB
client = chromadb.Client()
collection = client.get_or_create_collection(name="riva_imoveis")

# Indexar documents
vectorstore = Chroma.from_documents(docs, embeddings, client=client)
```

### 9. Regras de Negócio e Segurança

* **Privacidade:** O sistema está em conformidade com a LGPD no tratamento de dados dos leads.
* **Limites de Alucinação:** A IA é proibida de inventar preços. Se a informação não estiver na base, deve transferir para o humano.
* **Persistência:** Toda conversa gera um relatório de resumo enviado para o CRM ao final do atendimento.
* **Qualidade de Dados:** Apenas o texto relevante (sem menus/rodapés) alimenta a base de conhecimento.

### 10. Fluxo de Experiência do Usuário (UX)

1. **Entrada:** O lead clica em um anúncio e cai no WhatsApp.
2. **Boas-vindas e Filtro:** O bot inicia a conversa e identifica o interesse (ex: "Busca moradia ou investimento?").
3. **Consulta Técnica:** O cliente pergunta detalhes técnicos; o bot busca na base de conhecimento JSONL e responde.
4. **Gatilho de Transbordo:** Se o bot detectar uma intenção de compra clara ou o cliente pedir um humano, o corretor é notificado no Chatwoot.
5. **Conversão:** Agendamento de visita via link ou CRM.

---

## 🚀 Próximos Passos

1. **Implementar Vector Store:** Configure `ChromaDB` ou `Pinecone` para indexar base_conhecimento.jsonl
2. **Integrar com LLM:** Use LangChain para conectar o bot ao Gemini com RAG
3. **Webhooks no n8n:** Configure fluxos que consultam a base JSONL
4. **Teste de Qualidade:** Valide a qualidade da extração antes de usar em produção

