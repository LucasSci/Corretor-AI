
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

#### 6.1 Visibilidade de Conhecimento

Todas as rotinas de ingestão (e o método `add_training_data` da classe
`IntelligenceCore`) aceitam um parâmetro booleano `public` que indica se o
conteúdo deve estar disponível em respostas ao **cliente**. O valor padrão é
`True`, mas ao marcar `public=False` você garante que o trecho será armazenado
no vetor interno e nos logs de aprendizado, porém **não aparecerá** quando a
busca for realizada com `client_visible=True` (comportamento usado pelo
bot durante um atendimento). Essa medida evita que documentos internos,
como manuais de equipe ou rascunhos, sejam acidentalmente expostos.


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

### 7.1 Configurando o Bot do WhatsApp

O arquivo `app_whatsapp.py` contém o endpoint que recebe mensagens via webhook (originadas pela Evolution API ou outra similar).

Variáveis de ambiente úteis:

```bash
# URL base da API (ex: http://localhost:8080 ou https://eu-api.evolution.com.br)
export WHATSAPP_API_URL="http://localhost:8080"

# Token ou chave API (pode ser "Bearer <token>" ou chave simples)
export WHATSAPP_API_TOKEN="lucas_senha_123"

# Número do WhatsApp associado ao bot (DDI+DDD+celular, sem sufixo). Usado
# apenas para depuração/auto-teste.
export WHATSAPP_BOT_NUMBER="551975907217"  # seu número real (para auto‑teste)

# (Opcional) número substituto quando o pacote vier com @lid; útil ao
# desenvolver com a interface interna da Evolution.
export WHATSAPP_TEST_NUMBER="55219XXXXXXXX@s.whatsapp.net"

# (Opcional) número de teste para converter @lid
export WHATSAPP_TEST_NUMBER="55219XXXXXXXX@s.whatsapp.net"
```

**Como iniciar o servidor de desenvolvimento:**

```powershell
# dentro da virtualenv
python -m uvicorn app_whatsapp:app --reload --port 8000
```

Isso expõe `/webhook` localmente. A API da Evolution deve ser configurada com esse endereço no campo de Webhook.

**Simulando mensagens localmente:**

Um pequeno script `simulate_webhook.py` gera payloads fictícios e os envia para o servidor. Execute:

```powershell
python simulate_webhook.py
```

Os logs no terminal mostrarão a mensagem recebida e qualquer tentativa de resposta. Você pode adaptar o JSON para cobrir outros formatos (Meta, Z-API, etc.).

Quando o webhook processa corretamente, a IA é acionada via `bot_corretor.gerar_resposta_whatsapp` e a resposta retorna pela mesma API.

---

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

### 8.3 Fallback local (motor_busca.py)

O arquivo `motor_busca.py` contém uma implementação que tenta usar `ChromaDB` quando disponível, mas também inclui um *fallback* local que permite rodar buscas sem dependências externas adicionais.

- Com `chromadb` disponível: o script usa `chromadb.Client` e persiste usando DuckDB+Parquet em `./banco_vetorial_riva`.
- Sem `chromadb` ou em caso de incompatibilidade (por exemplo, problemas de versão do `pydantic`), o script gera embeddings localmente com `sentence-transformers` e salva um armazenamento local persistente em `./banco_vetorial_riva/local_store.pkl`.

Comandos úteis:
```powershell
# ativar venv
& .\.venv\Scripts\Activate.ps1

# instalar dependências principais
pip install sentence-transformers
pip install chromadb              # opcional — só se quiser usar ChromaDB

# se houver erro relacionado ao pydantic (compatibilidade), instale uma versão compatível
pip install "pydantic<2"
```

Observações:
- O fallback local é suficiente para desenvolvimento e testes offline.
- Se você planeja indexar grandes volumes ou usar features avançadas, recomenda-se configurar `ChromaDB` ou um serviço gerenciado como Pinecone/Weaviate.


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

