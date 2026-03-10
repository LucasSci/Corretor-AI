import json
import sys
import os
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except Exception as e:
    print("Aviso: chromadb não está disponível ou incompatível (fallback local será usado):", e)
    CHROMADB_AVAILABLE = False

import pickle
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    print("Erro: pacote 'sentence-transformers' não encontrado. Instale com: pip install sentence-transformers")
    raise

from typing import List

# Inicializa o modelo de embeddings (local)
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(EMBEDDING_MODEL_NAME)

# 1. Inicializa o banco vetorial localmente (cria uma pasta persistente)
local_store_path = "./banco_vetorial_riva"
os.makedirs(local_store_path, exist_ok=True)

if CHROMADB_AVAILABLE:
    chroma_client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=local_store_path))
    collection = chroma_client.get_or_create_collection(name="imoveis_riva")
else:
    collection = None


class LocalVectorStore:
    def __init__(self, path: str):
        self.path = path
        self.data_file = os.path.join(path, "local_store.pkl")
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

    def save(self):
        obj = {
            "ids": self.ids,
            "documents": self.documents,
            "metadatas": self.metadatas,
            "embeddings": self.embeddings.tolist(),
        }
        with open(self.data_file, "wb") as f:
            pickle.dump(obj, f)

    def add(self, ids, documents, metadatas, embeddings):
        self.ids.extend(ids)
        self.documents.extend(documents)
        self.metadatas.extend(metadatas)
        emb_arr = np.array(embeddings)
        if self.embeddings.size == 0:
            self.embeddings = emb_arr
        else:
            self.embeddings = np.vstack([self.embeddings, emb_arr])
        self.save()

    def query(self, query_embeddings, n_results=3):
        qe = np.array(query_embeddings)
        # normalize
        def _norm(x):
            denom = np.linalg.norm(x, axis=1, keepdims=True)
            denom[denom == 0] = 1.0
            return x / denom

        docs_out = []
        metas_out = []
        for q in qe:
            qn = q / (np.linalg.norm(q) or 1.0)
            emb_norm = _norm(self.embeddings)
            sims = emb_norm.dot(qn)
            idx = np.argsort(-sims)[:n_results]
            docs_out.append([self.documents[i] for i in idx.tolist()])
            metas_out.append([self.metadatas[i] for i in idx.tolist()])

        return {"documents": docs_out, "metadatas": metas_out}


local_store = LocalVectorStore(local_store_path)


def popular_banco(arquivo_jsonl: str = "data/base_conhecimento.jsonl"):
    """Lê os chunks, gera embeddings com sentence-transformers e injeta no ChromaDB."""
    print("Lendo o arquivo JSONL e gerando embeddings (isso pode levar um minutinho)...")

    documentos: List[str] = []
    metadados: List[dict] = []
    ids: List[str] = []

    try:
        with open(arquivo_jsonl, "r", encoding="utf-8") as file:
            for linha in file:
                if not linha.strip():
                    continue
                chunk = json.loads(linha)

                documentos.append(chunk.get("texto", ""))
                metadados.append(chunk.get("metadados", {}))
                ids.append(str(chunk.get("id_chunk", len(ids))))

        if documentos:
            # Gera embeddings em batch
            embeddings = model.encode(documentos, show_progress_bar=True, convert_to_numpy=True)

            # Converte para listas nativas
            embeddings_list = [vec.tolist() for vec in embeddings]

            if CHROMADB_AVAILABLE and collection is not None:
                collection.add(
                    ids=ids,
                    documents=documentos,
                    metadatas=metadados,
                    embeddings=embeddings_list,
                )
            else:
                local_store.add(ids=ids, documents=documentos, metadatas=metadados, embeddings=embeddings_list)

            print(f"✅ Sucesso! {len(documentos)} chunks foram vetorizados e salvos.")
        else:
            print("Nenhum documento encontrado no arquivo especificado.")
    except FileNotFoundError:
        print(f"Arquivo não encontrado: {arquivo_jsonl}")
    except Exception as e:
        print(f"❌ Erro ao popular o banco: {e}")


def buscar_contexto(pergunta: str, n_resultados: int = 3) -> str:
    """Retorna um texto formatado com os trechos mais relevantes à pergunta.

    Usado por outros módulos (ex: bot_corretor)."""
    print(f"  📚 [buscar_contexto] Gerando embedding para: '{pergunta[:50]}...'")
    emb = model.encode([pergunta], convert_to_numpy=True)[0].tolist()
    print(f"  ✅ [buscar_contexto] Embedding gerado")

    print(f"  🔎 [buscar_contexto] Consultando banco vetorial (usando {'ChromaDB' if CHROMADB_AVAILABLE and collection is not None else 'LocalStore'})...")
    if CHROMADB_AVAILABLE and collection is not None:
        resultados = collection.query(query_embeddings=[emb], n_results=n_resultados)
    else:
        resultados = local_store.query([emb], n_results=n_resultados)

    docs = resultados.get("documents", [[]])[0]
    metas = resultados.get("metadatas", [[]])[0]
    
    print(f"  ✅ [buscar_contexto] {len(docs)} resultado(s) encontrado(s)")

    contexto_formatado = ""
    for i in range(len(docs)):
        texto = docs[i]
        meta = metas[i] if i < len(metas) else {}
        empreendimento = meta.get('nome_empreendimento', 'Desconhecido')
        print(f"    📍 Resultado #{i+1}: {empreendimento}")
        contexto_formatado += f"--- IMÓVEL: {empreendimento} ---\n"
        contexto_formatado += f"FONTE: {meta.get('url_origem', 'N/A')}\n"
        contexto_formatado += f"DADOS: {texto}\n\n"
    return contexto_formatado


def simular_pergunta_cliente(pergunta: str, n_resultados: int = 3):
    """Busca os trechos mais relevantes para responder à pergunta."""
    print(f"\n🗣️ Cliente perguntou: '{pergunta}'\n")
    print("-" * 50)

    # Embeda a pergunta localmente e consulta por embeddings
    emb = model.encode([pergunta], convert_to_numpy=True)[0].tolist()

    if CHROMADB_AVAILABLE and collection is not None:
        resultados = collection.query(query_embeddings=[emb], n_results=n_resultados)
    else:
        resultados = local_store.query([emb], n_results=n_resultados)

    docs = resultados.get("documents", [[]])[0]
    metas = resultados.get("metadatas", [[]])[0]

    for i in range(len(docs)):
        texto_encontrado = docs[i]
        meta = metas[i] if i < len(metas) else {}

        print(f"📍 Empreendimento: {meta.get('nome_empreendimento', 'Desconhecido')}")
        print(f"🔗 Fonte: {meta.get('url_origem', 'N/A')}")
        print(f"📄 Trecho do documento:\n{texto_encontrado}...\n")
        print("-" * 50)


if __name__ == "__main__":
    # PASSO A: Rodar esta linha UMA VEZ para criar o banco e injetar os dados
    arquivo = "data/base_conhecimento.jsonl"
    if len(sys.argv) > 1:
        arquivo = sys.argv[1]

    popular_banco(arquivo)

    # PASSO B: Testar a inteligência da busca semântica
    simular_pergunta_cliente("Quais apartamentos têm varanda gourmet e piscina no condomínio?")