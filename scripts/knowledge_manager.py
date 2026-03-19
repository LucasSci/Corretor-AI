"""
Sistema central de gerenciamento de conhecimento do bot.
Responsável por armazenar, indexar e recuperar todo o conhecimento acumulado.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
import sys

# force stdout to utf-8 with replacement errors so emojis don't crash on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Inicializa modelo de embeddings
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(EMBEDDING_MODEL_NAME)

# Diretórios de armazenamento
KNOWLEDGE_DIR = "./conhecimento_ia"
VECTOR_STORE_PATH = os.path.join(KNOWLEDGE_DIR, "vetorial")
LEARNING_LOG_PATH = os.path.join(KNOWLEDGE_DIR, "aprendizado")
MEMORY_PATH = os.path.join(KNOWLEDGE_DIR, "memoria")

# Criar diretórios se não existirem
for path in [KNOWLEDGE_DIR, VECTOR_STORE_PATH, LEARNING_LOG_PATH, MEMORY_PATH]:
    os.makedirs(path, exist_ok=True)


class KnowledgeStore:
    """Armazenamento vetorial local de conhecimento."""
    
    def __init__(self, path: str = VECTOR_STORE_PATH):
        self.path = path
        self.data_file = os.path.join(path, "knowledge_store.pkl")
        self.metadata_file = os.path.join(path, "metadata.json")
        
        # Carregar dados existentes
        if os.path.exists(self.data_file):
            with open(self.data_file, "rb") as f:
                obj = pickle.load(f)
                self.ids = obj.get("ids", [])
                self.documents = obj.get("documents", [])
                self.metadatas = obj.get("metadatas", [])
                self.embeddings = np.array(obj.get("embeddings", []))
        else:
            self.ids = []
            self.documents = []
            self.metadatas = []
            self.embeddings = np.empty((0, model.get_sentence_embedding_dimension()))
        
        # Carregar metadados
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "total_documentos": 0,
                "fontes": {},
                "ultima_atualizacao": None,
                "versao": "1.0"
            }
    
    def save(self):
        """Salva dados no disco."""
        obj = {
            "ids": self.ids,
            "documents": self.documents,
            "metadatas": self.metadatas,
            "embeddings": self.embeddings.tolist(),
        }
        with open(self.data_file, "wb") as f:
            pickle.dump(obj, f)
        
        # Salvar metadados
        self.metadata["ultima_atualizacao"] = datetime.now().isoformat()
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def add(self, documents: List[str], metadatas: List[dict], ids: Optional[List[str]] = None):
        """Adiciona documentos ao conhecimento."""
        if not documents:
            return
        
        # Gerar IDs se não fornecidos
        if ids is None:
            ids = [f"doc_{len(self.ids) + i}" for i in range(len(documents))]
        
        print(f"📚 [KnowledgeStore] Adicionando {len(documents)} documento(s)...")
        
        # Gerar embeddings
        embeddings = model.encode(documents, show_progress_bar=True, convert_to_numpy=True)
        
        # Adicionar ao armazenamento
        self.ids.extend(ids)
        self.documents.extend(documents)
        self.metadatas.extend(metadatas)
        
        emb_arr = np.array(embeddings)
        if self.embeddings.size == 0:
            self.embeddings = emb_arr
        else:
            self.embeddings = np.vstack([self.embeddings, emb_arr])
        
        # Atualizar metadados
        self.metadata["total_documentos"] = len(self.ids)
        for meta in metadatas:
            fonte = meta.get("fonte", "desconhecida")
            self.metadata["fontes"][fonte] = self.metadata["fontes"].get(fonte, 0) + 1
        
        self.save()
        print(f"✅ [KnowledgeStore] {len(documents)} documento(s) armazenado(s)")
    
    def search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Busca documentos similares."""
        if self.embeddings.size == 0:
            return {"documents": [], "metadatas": [], "ids": [], "similarities": []}
        
        # Gerar embedding da query
        query_emb = model.encode([query], convert_to_numpy=True)[0]
        
        # Normalizar
        def _norm(x):
            denom = np.linalg.norm(x, axis=1, keepdims=True)
            denom[denom == 0] = 1.0
            return x / denom
        
        # Calcular similaridade
        query_norm = query_emb / (np.linalg.norm(query_emb) or 1.0)
        emb_norm = _norm(self.embeddings)
        similarities = emb_norm.dot(query_norm)
        
        # Top-N
        idx = np.argsort(-similarities)[:n_results]
        
        results = {
            "documents": [self.documents[i] for i in idx],
            "metadatas": [self.metadatas[i] for i in idx],
            "ids": [self.ids[i] for i in idx],
            "similarities": [float(similarities[i]) for i in idx]
        }
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do armazenamento."""
        return {
            "total_documentos": len(self.ids),
            "fontes": self.metadata.get("fontes", {}),
            "ultima_atualizacao": self.metadata.get("ultima_atualizacao"),
            "tamanho_embeddings": len(self.embeddings) if self.embeddings.size > 0 else 0
        }


class LearningLogger:
    """Registra todas as interações e aprendizados."""
    
    def __init__(self, path: str = LEARNING_LOG_PATH):
        self.path = path
        self.log_file = os.path.join(path, f"learning_log_{datetime.now().strftime('%Y%m%d')}.jsonl")
    
    def log_interaction(self, interaction: Dict[str, Any]):
        """Registra uma interação do atendimento."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tipo": "interacao",
            **interaction
        }
        self._append_log(entry)
    
    def log_feedback(self, feedback: Dict[str, Any]):
        """Registra feedback sobre qualidade de resposta."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tipo": "feedback",
            **feedback
        }
        self._append_log(entry)
    
    def log_new_knowledge(self, knowledge: Dict[str, Any]):
        """Registra novo conhecimento adquirido."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tipo": "novo_conhecimento",
            **knowledge
        }
        self._append_log(entry)
    
    def _append_log(self, entry: Dict[str, Any]):
        """Adiciona entrada ao arquivo de log."""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def get_recent_learnings(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna aprendizados recentes."""
        learnings = []
        if os.path.exists(self.log_file):
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        learnings.append(json.loads(line))
        return learnings[-limit:]


class MemorySystem:
    """Sistema de memória persistente do bot."""
    
    def __init__(self, path: str = MEMORY_PATH):
        self.path = path
        self.memory_file = os.path.join(path, "bot_memory.json")
        
        # Carregar memória existente
        if os.path.exists(self.memory_file):
            with open(self.memory_file, "r", encoding="utf-8") as f:
                self.memory = json.load(f)
        else:
            self.memory = {
                "clientes_conhecidos": {},
                "produtos_aprendidos": {},
                "padroes_conversa": [],
                "erros_corrigidos": [],
                "especialidades": [],
                "contexto_geral": {}
            }
    
    def add_client_profile(self, numero: str, profile: Dict[str, Any]):
        """Adiciona perfil de cliente à memória."""
        self.memory["clientes_conhecidos"][numero] = {
            "timestamp": datetime.now().isoformat(),
            **profile
        }
        self._save()
    
    def add_product_knowledge(self, produto_id: str, conhecimento: Dict[str, Any]):
        """Adiciona conhecimento sobre um produto."""
        self.memory["produtos_aprendidos"][produto_id] = {
            "timestamp": datetime.now().isoformat(),
            **conhecimento
        }
        self._save()
    
    def add_conversation_pattern(self, pattern: Dict[str, Any]):
        """Registra padrão de conversa bem-sucedido."""
        self.memory["padroes_conversa"].append({
            "timestamp": datetime.now().isoformat(),
            **pattern
        })
        self._save()
    
    def add_corrected_error(self, erro: str, correcao: str):
        """Registra erro corrigido para evitar repetição."""
        self.memory["erros_corrigidos"].append({
            "timestamp": datetime.now().isoformat(),
            "erro": erro,
            "correcao": correcao
        })
        self._save()
    
    def get_client_profile(self, numero: str) -> Optional[Dict[str, Any]]:
        """Recupera perfil de cliente."""
        return self.memory["clientes_conhecidos"].get(numero)
    
    def get_all_knowledge(self) -> Dict[str, Any]:
        """Retorna toda memória acumulada."""
        return self.memory
    
    def _save(self):
        """Salva memória no disco."""
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2)
        print(f"💾 Memória salva em {self.memory_file}")


class IntelligenceCore:
    """núcleo central de inteligência do bot."""
    
    def __init__(self):
        self.knowledge_store = KnowledgeStore()
        self.learning_logger = LearningLogger()
        self.memory_system = MemorySystem()
    
    def add_training_data(self, documents: List[str], source: str, category: str = "geral", public: bool = True):
        """Adiciona dados de treinamento.

        Args:
            documents: lista de textos
            source: origem (URL, PDF etc)
            category: categoria para classificação
            public: se False, o documento não será usado em respostas ao cliente
        """
        metadatas = [
            {
                "fonte": source,
                "categoria": category,
                "data_adicao": datetime.now().isoformat(),
                "expose_to_client": public
            }
            for _ in documents
        ]
        
        self.knowledge_store.add(documents, metadatas)
        self.learning_logger.log_new_knowledge({
            "source": source,
            "category": category,
            "documentos_adicionados": len(documents)
        })
    
    def search_knowledge(self, query: str, n_results: int = 5, client_visible: bool = True) -> Dict[str, Any]:
        """Busca conhecimento relevante.

        Args:
            query: texto de busca
            n_results: número de resultados
            client_visible: se True, filtra fora documentos marcados como não públicos
        """
        results = self.knowledge_store.search(query, n_results)
        if client_visible:
            # filtrar documentos onde metadata.expose_to_client == False
            filtered_docs = []
            filtered_meta = []
            filtered_ids = []
            filtered_sims = []
            for doc, meta, id_, sim in zip(results['documents'], results['metadatas'], results['ids'], results['similarities']):
                if meta.get('expose_to_client', True):
                    filtered_docs.append(doc)
                    filtered_meta.append(meta)
                    filtered_ids.append(id_)
                    filtered_sims.append(sim)
            results = {
                'documents': filtered_docs,
                'metadatas': filtered_meta,
                'ids': filtered_ids,
                'similarities': filtered_sims
            }
        print(f"🔍 Busca realizada: '{query}'")
        print(f"📊 Resultados: {len(results['documents'])} documento(s) encontrado(s)")
        
        return results
    
    def log_interaction(self, cliente_numero: str, pergunta: str, resposta: str, 
                       satisfacao: float = None, feedback: str = None):
        """Registra interação do cliente."""
        self.learning_logger.log_interaction({
            "cliente": cliente_numero,
            "pergunta": pergunta,
            "resposta": resposta,
            "satisfacao": satisfacao,
            "feedback": feedback
        })
    
    def get_bot_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do bot."""
        return {
            "conhecimento": self.knowledge_store.get_stats(),
            "clientes_conhecidos": len(self.memory_system.memory["clientes_conhecidos"]),
            "produtos_aprendidos": len(self.memory_system.memory["produtos_aprendidos"]),
            "padroes_conversa": len(self.memory_system.memory["padroes_conversa"]),
            "erros_corrigidos": len(self.memory_system.memory["erros_corrigidos"])
        }


# Instância global
intelligence_core = IntelligenceCore()


if __name__ == "__main__":
    print("🧠 Sistema de Conhecimento Inicializado")
    
    # Teste
    teste_docs = [
        "O Apogeu Barra é um empreendimento de luxo com 2 piscinas e área de lazer completa",
        "Duet Barra oferece apartamentos com varanda e vista para o mar",
        "Ilhamar Beach Home é ideal para famílias com playground e quadra de esportes"
    ]
    
    intelligence_core.add_training_data(
        documents=teste_docs,
        source="manual",
        category="imovel"
    )
    
    print("\n📊 Estatísticas:")
    print(json.dumps(intelligence_core.get_bot_stats(), indent=2, ensure_ascii=False))
