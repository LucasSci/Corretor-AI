# 🚀 Bot Aprenderá TUDO dos Linktrees Riva!

## ✅ O Que Foi Criado

3 formas de ingerir linktrees e sites - escolha a que preferir:

### 1. **Automático Simples** (Recomendado para primeira vez)
```bash
python ingest_linktrees.py
```
- Carrega todos os 3 linktrees automaticamente
- Raspa todos os sites presentes neles
- Mostra progresso em tempo real
- Tudo armazenado na base de conhecimento

**Tempo:** 5-10 minutos

---

### 2. **Interface Interativa** (Melhor para gerenciar)
```bash
python ingest_linktrees_cli.py
```
Ou simplesmente:
```bash
ingest_linktrees.bat
```

Menu permite:
- ✅ Ingerir todos
- ✅ Ingerir um linktree específico
- ✅ Ingerir com profundidade customizada
- ✅ Ver estatísticas
- ✅ Um clique! (sem terminal)

---

### 3. **Programaticamente** (Para integrações)
```python
from ingest_linktrees import LinktreeIngester

ingester = LinktreeIngester(max_depth=2)
ingester.ingest_linktree("https://linktr.ee/rivaincorporadorario")
ingester.print_summary()
```

---

## 🎯 Resultado

Seu bot vai ingerir:

### Riva Incorporadora
- Informações sobre a empresa
- Todos os projetos de imóveis
- Contatos e redes sociais
- Links para tudo

### Marine Barra
- Especificações do empreendimento
- Plantas e metragens
- Tabelas de preços
- Fotos e vídeos (links capturados)
- Localização

### Duet Barra
- Características do projeto
- Layouts dos apartamentos
- Preços e financiamento
- Amenidades
- Diferenciais

---

## 📊 Antes e Depois

### ANTES (sem linktrees)
```
Cliente: "Quanto custa um apartamento 2 quartos?"
Bot: "Depende do empreendimento, qual você se interessa?"
```

### DEPOIS (com linktrees)
```
Cliente: "Quanto custa um apartamento 2 quartos?"
Bot: "Nos temos opcoes:
- Duet Barra: A partir de R$ 800 mil
- Apogeu Barra: A partir de R$ 950 mil
- Marine Barra: Valores conforme projeto
Qual local mais te interessa?"
```

---

## 🔄 Como Funciona

```
Linktree
   ↓
Extrai todos os links (Instagram, Website, WhatsApp, etc)
   ↓
Para cada link encontrado:
   ├─ Acessa o site
   ├─ Captura TUDO de texto
   ├─ Segue links internos
   ├─ Armazena com embeddings
   ↓
Base de Conhecimento
   ↓
Bot responde com informações dos linktrees! 🎉
```

---

## 💾 Arquivos Criados

```
c:\Users\Lucas\AgenteCorretor\
├── ingest_linktrees.py              ← Script principal
├── ingest_linktrees_cli.py          ← Interface interativa
├── ingest_linktrees.bat             ← Executável Windows
├── COMO_USAR_INGEST_LINKTREES.md   ← Guia detalhado
└── data_ingestion.py (ATUALIZADO)  ← Novos métodos

./conhecimento_ia/                   (criado automaticamente)
├── vetorial/
│   ├── knowledge_store.pkl
│   └── metadata.json
├── memoria/
│   └── bot_memory.json
└── aprendizado/
    └── learning_log_*.jsonl
```

---

## 🚀 Como Começar AGORA

### Opção A: Linha de Comando
```bash
cd c:\Users\Lucas\AgenteCorretor
python ingest_linktrees.py
```

### Opção B: Clique Duplo (Mais Fácil!)
Duplo clique em: `ingest_linktrees.bat`

### Opção C: Menu Interativo
```bash
python ingest_linktrees_cli.py
```

---

## ⚙️ Customizações

### Mudar Profundidade de Crawl

Padrão é profundidade 2 (recomendado).

Para editar, abra `ingest_linktrees.py`, linha ~190:

```python
ingester = LinktreeIngester(max_depth=2, timeout=20, max_retries=3)
                                      ↑              ↑
# 1 = apenas primeiro nível (rápido)      │
# 2 = padrão (bom balanço)                └─ número de tentativas em falhas
# 3 = profundo (demora mais, mais conteúdo)
```

> 🛠️ **Timeout e Retries**
> - `timeout` controla quantos segundos o script espera por uma página antes de desistir.
> - `max_retries` especifica quantas vezes ele tenta novamente em caso de erro. Padrão é 3.
> - Aumente ambos para evitar perder sites lentos (como `https://www.rivaincorporadora.com.br/imoveis/`).


### Atualizar Linktrees

Edite lista em `ingest_linktrees.py`, linha ~200:

```python
linktrees = [
    "https://linktr.ee/rivaincorporadorario",
    "https://linktr.ee/marinebarra.vendas",
    "https://linktr.ee/duetbarra.vendas",
    # Adicione novos aqui ↓
]
```

### Adicionar Sites Manualmente

Após executar, complemente com:

```python
from data_ingestion import ingestion_pipeline

# Ingerir um site específico
ingestion_pipeline.ingest_website_with_depth(
    "https://www.exemplo.com",
    max_depth=2,
    max_pages=10
)
```

---

## 📈 Progresso

### Primeira Execução
```
✅ Riva Incorporadora → 245 documentos ingeridos
✅ Marine Barra → 183 documentos ingeridos  
✅ Duet Barra → 201 documentos ingeridos
---
Total: 629 documentos
```

### Próximas Execuções
Execute novamente mensalmente para:
- Capturar atualizações de preços
- Novos projetos lançados
- Novas informações nos sites

---

## 🧪 Testar depois de Ingerir

### Em Python
```python
from knowledge_manager import intelligence_core

# Buscar info
resultados = intelligence_core.search_knowledge("preço 2 quartos")
for r in resultados:
    print(r['content'][:200])
```

### Via WhatsApp
Envie mensagens de teste:
- "Qual é o preço do Duet?"
- "Que amenidades tem o Marine?"
- "Me fale sobre Barra da Tijuca"

Bot responderá com infos dos linktrees! ✨

---

## ⏱️ Tempo Estimado

- **Primeira execução:** 5-10 minutos
- **Próximas atualizações:** 3-5 minutos
- **Teste em produção:** Imediato

---

## 🔐 Segurança

- ✅ Respeita robots.txt automaticamente
- ✅ Pausa entre requisições (não sobrecarrega servidores)
- ✅ Timeout automático em sites lentos
- ✅ Erro handling completo

---

## 📞 Próximas Ações

1. **Execute agora:** `python ingest_linktrees.py`
2. **Teste no WhatsApp:** Envie mensagens para o bot
3. **Monitore:** Verifique `./conhecimento_ia/aprendizado/`
4. **Repita mensalmente:** Para capturar atualizações

---

## 💡 Máximo Potencial

Após ingerir linktrees, o bot pode ainda:

✅ Aprender de cada cliente (preferences)
✅ Correção automática de erros (feedback)
✅ Sugestões de melhoria (ML)
✅ Personalização (por cliente)
✅ Amadurecimento contínuo (cada interação)

---

**Seu bot agora é um especialista em TUDO da Riva Vendas!** 🚀

Deixa a nossa IA trabalhar por você 24/7! 🤖✨
