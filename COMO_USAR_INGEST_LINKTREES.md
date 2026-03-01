# 🔗 Guia: Ingerir Linktrees e Sites da Riva Vendas

## 🎯 Objetivo

Todos os conteúdos dos linktrees e seus sites serão aprendidos pelo bot automaticamente, tornando-o especialista em todos os produtos e serviços presentes nesses canais.

## 📋 Linktrees Configuradas

1. **Riva Incorporadora** - https://linktr.ee/rivaincorporadorario
2. **Marine Barra Vendas** - https://linktr.ee/marinebarra.vendas
3. **Duet Barra Vendas** - https://linktr.ee/duetbarra.vendas

## 🚀 Como Executar

### Opção 1: Automático (Recomendado)

```bash
cd c:\Users\Lucas\AgenteCorretor
python ingest_linktrees.py
```

Isso irá:
- ✅ Ler cada linktree
- ✅ Extrair todos os links encontrados
- ✅ Visitar cada site (até 2 níveis de profundidade)
- ✅ Armazenar TUDO na base de conhecimento do bot
- ✅ Mostrar progresso em tempo real

**Tempo estimado:** 3-5 minutos (depende da internet)

### Opção 2: Ajuste Manualmente em Python

Se quiser customizar, edite `ingest_linktrees.py`:

```python
# Linha ~190 - Ajust max_depth (profundidade de crawl)
ingester = LinktreeIngester(max_depth=2, timeout=20)

# max_depth=1 → apenas linktree + primeiro nível de links
# max_depth=2 → linktree + links + subpáginas (RECOMENDADO)
# max_depth=3 → mais profundo (mais tempo, mais conteúdo)
```

### Opção 3: Adicionar Mais Linktrees

Edite a lista em `ingest_linktrees.py`, linha ~200:

```python
linktrees = [
    "https://linktr.ee/rivaincorporadorario",
    "https://linktr.ee/marinebarra.vendas",
    "https://linktr.ee/duetbarra.vendas",
    "https://linktr.ee/novo_linktree",  # ← Adicione aqui
]
```

## 📊 O Que Será Ingerido

### Riva Incorporadora (rivaincorporadorario)
Links típicos:
- 🌐 Site da empresa
- 📱 WhatsApp
- 📧 Email
- 🏢 Projetos e empreendimentos
- 📞 Contatos

### Marine Barra Vendas (marinebarra.vendas)
Links típicos:
- 🏘️ Informações do Marine Barra
- 💰 Tabela de preços
- 📋 Plantas e metragens
- 📷 Fotos do empreendimento
- 👥 Equipe de vendas

### Duet Barra Vendas (duetbarra.vendas)
Links típicos:
- 🏗️ Informações do Duet Barra
- 🛋️ Ambientes e acabamentos
- 💵 Tabelas de preços
- 📐 Plantas dos apartamentos
- 🎯 Destaques do projeto

## 📈 Resultado Esperado

### ANTES (sem ingestão de linktrees)
```
Cliente: "O que vocês oferecem?"
Bot: "Temos apartamentos em Barra da Tijuca com boas amenidades"
```

### DEPOIS (com ingestão de linktrees)
```
Cliente: "O que vocês oferecem?"
Bot: "Oferecemos 3 empreendimentos principais:
1. Apogeu Barra - De R$ 450 mil (studios) até R$ 2.5 milhões
2. Marine Barra - Totalmente integrado à natureza
3. Duet Barra - Design sofisticado com varanda gourmet
Todos em Barra da Tijuca com excelentes localizações"
```

## 🔄 Fluxo de Ingestão

```
Linktrees
    ↓
[ingest_linktrees.py]
    ├─ Extrai links do Linktree
    ├─ Para cada link:
    │   ├─ Acessa o site
    │   ├─ Extrai todo o conteúdo de texto
    │   ├─ Segue links internos (profundidade 2)
    │   └─ Armazena na base vetorial
    ↓
[knowledge_manager.py]
    ├─ Converte em embeddings
    ├─ Armazena com metadados
    ↓
[Bot pode buscar]
    ├─ Respostas mais precisas
    ├─ Informações atualizadas
    └─ Recomendações personalizadas 🎯
```

## 🛠️ Troubleshooting

### "Erro de timeout"
O site demorou para responder. Isso é normal em páginas pesadas ou mal hospedadas. O script tentará novamente automaticamente até 3 vezes por padrão, então você quase nunca perderá um site útil.

Se precisar, você pode ajustar tanto o `timeout` quanto o número de tentativas usando os parâmetros do ingester:
```python
# timeout em segundos, max_retries controla quantas tentativas
ingester = LinktreeIngester(max_depth=2, timeout=15, max_retries=5)
```

### "Poucas páginas ingeridas"
Aumente `max_depth` em `LinktreeIngester()` ou aumente `max_pages`.

### "Bot não encontrou o conteúdo"
1. Verifique se `ingest_linktrees.py` foi executado sem erros
2. Procure em `./conhecimento_ia/aprendizado/` por arquivos de log
3. Tente buscar manualmente: `intelligence_core.search_knowledge("termo")`

### "Muitos erros de conexão"
Pode ser problema de internet ou os sites bloqueando bots.
Tente novamente mais tarde; em geral o retry automático resolve. Se ainda ocorrer, aumente `timeout` e/ou `max_retries`:
```python
ingester = LinktreeIngester(max_depth=2, timeout=15, max_retries=5)
```

## 💡 Pro Tips

### 1. Atualizações Periódicas
Execute novamente mensalmente para capturar novas informações:
```bash
python ingest_linktrees.py
```

### 2. Ingerir Conteúdo Adicional
Após rodar o script principal, você pode ingerir manualmente:
```python
from data_ingestion import ingestion_pipeline

# Um PDF com documentação interna
ingestion_pipeline.ingest_pdf('./documentos/manual_vendas.pdf')

# Um site específico
ingestion_pipeline.ingest_website_with_depth(
    'https://exemplo.com',
    max_depth=3,
    max_pages=20
)
```

### 3. Monitorar Progresso
Verifique em tempo real:
```python
from knowledge_manager import intelligence_core

# Quantos documentos estão na base?
stats = intelligence_core.get_bot_stats()
print(stats)
```

### 4. Testar Busca
Após ingestão, teste se o conhecimento foi absorvido:
```python
from knowledge_manager import intelligence_core

resultados = intelligence_core.search_knowledge(
    "preço apartamento 2 quartos",
    top_k=5
)

for resultado in resultados:
    print(f"Score: {resultado['confidence']}")
    print(resultado['content'][:200])
    print("---")
```

## 📁 Estrutura de Arquivos Criados

Após executar `ingest_linktrees.py`:

```
./conhecimento_ia/
├── vetorial/
│   ├── knowledge_store.pkl        (embeddings dos conteúdos)
│   └── metadata.json              (informações dos documentos)
├── memoria/
│   └── bot_memory.json            (perfis de clientes)
└── aprendizado/
    ├── learning_log_20260228.jsonl (interações do dia)
    └── ...
```

## ✅ Checklist

- [ ] Executei `python ingest_linktrees.py`
- [ ] Script rodou sem muitos erros
- [ ] Vejo "✅ Bot atualizado com todo o conhecimento dos linktrees!"
- [ ] Enviei uma mensagem de teste no WhatsApp
- [ ] Bot respondeu com informações dos linktrees
- [ ] Arquivos foram criados em `./conhecimento_ia/`

## 🎉 Pronto!

Seu bot agora é um especialista em TUDO que existe nesses 3 linktrees!

A cada dias que passar, conforme clientes façam perguntas, o bot aprenderá ainda mais e ficará cada vez mais inteligente. 🚀

---

**Próximos passos recomendados:**
1. Ingerir linktrees agora mesmo com `python ingest_linktrees.py`
2. Testar respostas com mensagens de WhatsApp real
3. Monitorar aprendizado via `learning_system.get_improvement_suggestions()`
4. Re-executar ingestão mensalmente para capturar atualizações
