# 🧠 Sistema de Inteligência Contínua - Documentação

## Visão Geral

O bot agora possui um **sistema de aprendizado contínuo e escalável** que acumula conhecimento como um verdadeiro expertise em imóveis de Barra da Tijuca. Cada interação, cada documento lido, cada imóvel conhecido, alimenta a inteligência do bot.

## Arquitetura

```
┌─────────────────────────────────────────────────────┐
│              Conhecimento Acumulado                  │
├──────────────────┬──────────────────┬───────────────┤
│  KnowledgeStore  │  MemorySystem    │ LearningLog   │
│  (Vetorial)      │  (Perfis)        │  (Histórico)  │
└──────────────────┴──────────────────┴───────────────┘
           ↑              ↑              ↑
           └──────────────┼──────────────┘
                    ↓
        ┌───────────────────────┐
        │  IntelligenceCore     │
        │  (Núcleo Central)     │
        └───────────────────────┘
           ↑               ↓
    ┌──────────────────────────────┐
    │  DataIngestionPipeline       │
    │  - PDFs                      │
    │  - Imóveis                   │
    │  - Websites                  │
    │  - JSON/CSV                  │
    │  - Conhecimento direto       │
    └──────────────────────────────┘
           ↓
    ┌──────────────────────────────┐
    │  ContinuousLearningSystem    │
    │  - Aprende com interações    │
    │  - Registra feedback         │
    │  - Corrige erros             │
    │  - Perfila clientes          │
    └──────────────────────────────┘
```

## Componentes

### 1. **KnowledgeStore** - Armazenamento Vetorial
Armazena toda a base de conhecimento de forma inteligente usando embeddings.

**Localização:** `./conhecimento_ia/vetorial/`

**Funcionalidades:**
- Armazer documentos com embeddings (representações vetoriais)
- Busca semântica rápida e precisa
- Versionamento automático
- Estatísticas de uso

**Dados armazenados:**
```
- knowledge_store.pkl → Dados vetoriais (binário)
- metadata.json → Metadados (JSON)
```

### 2. **MemorySystem** - Memória Persistente
Mantém histórico de clientes, preferências e aprendizados.

**Localização:** `./conhecimento_ia/memoria/bot_memory.json`

**Estrutura de memória:**
```json
{
  "clientes_conhecidos": {
    "5521987654321": {
      "preferencias": {
        "tipo_imovel": "apartamento",
        "budget": "alto",
        "localizacao_preferida": "Barra da Tijuca"
      },
      "total_interacoes": 5,
      "primeira_interacao": "2026-02-28T10:30:00"
    }
  },
  "produtos_aprendidos": {},
  "padroes_conversa": [],
  "erros_corrigidos": [],
  "especialidades": []
}
```

### 3. **LearningLogger** - Log de Aprendizado
Registra cada interação, feedback e novo conhecimento adquirido.

**Localização:** `./conhecimento_ia/aprendizado/learning_log_YYYYMMDD.jsonl`

**Entradas de log:**
```json
{"timestamp": "...", "tipo": "interacao", "cliente": "...", "pergunta": "...", "resposta": "..."}
{"timestamp": "...", "tipo": "feedback", "satisfacao": 5, "feedback": "..."}
{"timestamp": "...", "tipo": "novo_conhecimento", "source": "...", "documentos": 5}
```

### 4. **DataIngestionPipeline** - Ingestão Multi-fonte
Permite adicionar conhecimento de múltiplas fontes.

**Fontes suportadas:**
- 📄 **PDFs** - Documentação de produtos
- 🏢 **Imóveis** - Dados estruturados
- 🌐 **Websites** - Web scraping
- 📝 **Arquivos de texto** - Conhecimento em TXT/MD
- 📋 **JSON/CSV** - Dados estruturados
- ⌨️ **Conhecimento direto** - Input manual

## Como Usar

### 1. Treinar o Bot com Dados Básicos

```bash
python exemplo_treinamento.py
```

Isso adiciona:
- 3 imóveis de exemplo
- Conhecimentos sobre Barra
- Dicas de venda
- Simula interações de teste

### 2. Adicionar Dados de um PDF

```python
from data_ingestion import ingestion_pipeline

# Um arquivo
ingestion_pipeline.ingest_pdf("documento.pdf", categoria="especificacao")

# Pasta inteira
ingestion_pipeline.ingest_pdf_folder("./documentos", categoria="manual")
```

### 3. Adicionar Dados de Imóvel

```python
from data_ingestion import ingestion_pipeline

imovel = {
    "nome": "Marina Residence",
    "localizacao": "Barra da Tijuca",
    "descricao": "Residencial de luxo com 450 unidades",
    "amenidades": ["Piscina", "Academia", "Playground"],
    "precos": {
        "2 Quartos": "800000",
        "3 Quartos": "1200000"
    }
}

ingestion_pipeline.ingest_property(imovel)
```

### 4. Adicionar Conhecimento Direto

```python
from data_ingestion import ingestion_pipeline

conhecimento = """
Barra da Tijuca é ideal para clientes que buscam:
- Modernidade e tecnologia
- Segurança premium
- Qualidade de vida
- Proximidade com comércio
"""

ingestion_pipeline.add_custom_knowledge(
    knowledge_text=conhecimento,
    categoria="dicas_vendas"
)
```

### 5. Consultar Estatísticas

```python
from knowledge_manager import intelligence_core

stats = intelligence_core.get_bot_stats()
print(stats)

# Output:
# {
#   "conhecimento": {
#     "total_documentos": 25,
#     "fontes": {"Imóvel: Apogeu Barra": 3, "Imóvel: Duet Barra": 2, ...},
#     "ultima_atualizacao": "2026-02-28T...",
#     "tamanho_embeddings": 25
#   },
#   "clientes_conhecidos": 5,
#   "produtos_aprendidos": 3,
#   "padroes_conversa": 12,
#   "erros_corrigidos": 2
# }
```

### 6. Buscar Conhecimento

```python
from knowledge_manager import intelligence_core

resultados = intelligence_core.search_knowledge(
    query="Qual é o preço dos apartamentos com piscina?",
    n_results=5
)

for doc, confianca in zip(resultados['documents'], resultados['similarities']):
    print(f"Confiança: {confianca:.2f}")
    print(f"Documento: {doc}")
```

### 7. Processar Feedback de Atendimento

```python
from learning_system import learning_system

# Registrar uma interação bem-sucedida
learning_system.process_interaction({
    "cliente_numero": "5521987654321",
    "pergunta": "Qual apartamento recomenda?",
    "resposta": "Recomendo o Duet Barra...",
    "satisfacao": 5,
    "feedback_texto": "Excelente atendimento!",
    "modelo_usado": "gemini"
})
```

### 8. Corrigir Respostas Incorretas

```python
from learning_system import learning_system

learning_system.correct_wrong_response(
    pergunta="Qual é o preço do Apogeu?",
    resposta_incorreta="R$ 300 mil",
    resposta_correta="Começa em R$ 450 mil"
)
```

### 9. Obter Sugestões de Melhoria

```python
from learning_system import learning_system

sugestoes = learning_system.get_improvement_suggestions()
print(sugestoes)

# Output:
# {
#   "low_satisfaction_count": 2,
#   "top_questions": ["Qual é o preço?", "Tem piscina?", ...],
#   "models_performance": {"gemini": {"total": 50, "satisfied": 48}, ...},
#   "suggestions": ["⚠️ Muitos clientes com baixa satisfação...", ...]
# }
```

## Fluxo de Aprendizado em Tempo Real

### Quando um cliente envia uma mensagem no WhatsApp:

1. **Recebimento** → Webhook recebe mensagem
2. **Busca** → Bot busca em MÚLTIPLAS bases:
   - Base histórica (motor_busca.py)
   - Base inteligente (intelligence_core)
   - Perfil do cliente (memory_system)
3. **Geração** → IA Generativa (Gemini/OpenAI) gera resposta
4. **Aprendizado** → Sistema registra:
   - Pergunta do cliente
   - Resposta gerada
   - Qual modelo foi usado
   - Preferências extraídas
5. **Memória** → Perfil do cliente é atualizado
6. **Feedback futuro** → Próximas respostas melhoram

## Estrutura de Diretórios

```
c:\Users\Lucas\AgenteCorretor\
├── conhecimento_ia/             # 🧠 Base de conhecimento
│   ├── vetorial/                # Embeddings + documentos
│   │   ├── knowledge_store.pkl
│   │   └── metadata.json
│   ├── memoria/                 # Perfis e memória
│   │   └── bot_memory.json
│   └── aprendizado/             # Histórico de aprendizados
│       ├── learning_log_20260228.jsonl
│       └── learning_log_20260301.jsonl
│
├── knowledge_manager.py         # 🧠 Núcleo de inteligência
├── data_ingestion.py            # 📥 Ingestão de dados
├── learning_system.py           # 🎓 Sistema de aprendizado
├── exemplo_treinamento.py       # 📚 Script de exemplo
│
├── documentos/                  # 📄 PDFs para ingesta (opcional)
└── dados/                       # 📝 Arquivos TXT/MD (opcional)
```

## Casos de Uso

### Caso 1: Adicionar nova documentação de produto

```bash
# 1. Coloque o PDF em ./documentos/
# 2. Execute:
python -c "from data_ingestion import ingestion_pipeline; ingestion_pipeline.ingest_pdf_folder('./documentos')"
# 3. Pronto! Bot agora conhece o novo produto
```

### Caso 2: Melhorar respostas para perguntas frequentes

```bash
# 1. Execute para ver perguntas frequentes:
python -c "from learning_system import learning_system; print(learning_system.get_improvement_suggestions())"
# 2. Adicione conhecimento para essas perguntas:
from data_ingestion import ingestion_pipeline
ingestion_pipeline.add_custom_knowledge("Resposta para pergunta frequente", "faq")
```

### Caso 3: Corrigir erro que bot cometeu

```bash
# 1. Quando notificar um erro:
from learning_system import learning_system
learning_system.correct_wrong_response(
    pergunta="Original",
    resposta_incorreta="O que foi respondido",
    resposta_correta="A resposta correta"
)
# 2. Bot nunca mais cometerá esse erro
```

## Melhorias Futuras

- [ ] Dashboard web para visualizar data de aprendizado
- [ ] API para adicionar conhecimento remotamente
- [ ] Integração com CRM para tracking de clientes
- [ ] Relatórios de performance por período
- [ ] Análise de padrões de vendas
- [ ] Recomendações automáticas para clientes
- [ ] Chatbot com histórico visual

## Resumo

**ANTES**: Bot respondia com base em dados estáticos
**AGORA**: Bot aprende continuamente, melhora cada dia, e se torna especialista

É como contratar um corretor novato que aprende a cada cliente, cada propriedade, cada feedback. Com o tempo, vira um especialista! 🚀
