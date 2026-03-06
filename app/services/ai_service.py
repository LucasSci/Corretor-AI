import logging
import sys
from typing import Any, Dict, Optional, List

try:
    import google.genai as google_genai
    from google.genai import types
except Exception:
    google_genai = None
    types = None

from app.core.config import settings

logger = logging.getLogger(__name__)

MASTER_PROMPT = (
    "És um corretor de imóveis de luxo da Riva Incorporadora, a conversar com um cliente pelo WhatsApp. "
    "O teu tom de voz é 100% natural, empático, persuasivo e leve. "
    "REGRAS:\n"
    "- PROIBIDO COPIAR E COLAR: Nunca repitas as frases exatas da memória. Absorve o dado e cria uma frase coloquial.\n"
    "- ZERO ROBÓTICA: Nunca digas 'De acordo com os dados', 'Baseado no meu contexto' ou 'Como IA'.\n"
    "- FLUIDEZ DE WHATSAPP: Escreve mensagens curtas. Não faças listas longas. Usa no máximo 1 a 2 emojis.\n"
    "- FALTA DE INFORMAÇÃO: Se a informação não estiver na memória, não digas friamente 'Não sei'. Diz algo como: "
    "'De cabeça agora não me recordo desse detalhe da planta, mas vou confirmar com a engenharia. Entretanto, diz-me...'"
)


class AIService:
    def __init__(self) -> None:
        self.model = None
        self.chroma_client = None
        self.collection = None

        if settings.GEMINI_API_KEY and google_genai is not None:
            try:
                self.model = google_genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as exc:
                logger.error("Erro ao inicializar cliente Gemini: %s", exc)
                self.model = None

        chromadb = None
        if sys.version_info < (3, 14):
            try:
                import chromadb as chromadb_module
                chromadb = chromadb_module
            except Exception:
                chromadb = None
        else:
            logger.info("ChromaDB desativado: Python 3.14+ ainda nao e suportado pelo pacote atual.")

        if chromadb is not None:
            try:
                self.chroma_client = chromadb.PersistentClient(path="data/chroma_db")
                self.collection = self.chroma_client.get_or_create_collection("riva_imoveis")
            except Exception as exc:
                logger.error("Erro ao inicializar ChromaDB: %s", exc)
                self.collection = None

    async def get_context_from_db(self, query: str) -> str:
        if not self.collection:
            return ""

        try:
            # Requisito do usuario: k=4 (top 4 chunks)
            results = self.collection.query(query_texts=[query], n_results=4)
            docs: List[Any] = results.get("documents", []) if isinstance(results, dict) else []
            if docs and docs[0]:
                return "\n".join(docs[0])
            return ""
        except Exception as exc:
            logger.error("Erro ao buscar contexto no ChromaDB: %s", exc)
            return ""

    async def generate_response(self, user_message: str, context: str = "") -> str:
        if not self.model:
            return "De cabeça agora não me recordo desse detalhe, mas vou confirmar. Entretanto, como te posso ajudar?"

        try:
            prompt = user_message
            if context:
                prompt = f"Informacao relevante da base de conhecimento (use apenas se pertinente, mas nao cite a base):\n{context}\n\nCliente diz: {user_message}"

            # Pass config for temperature=0.6 and master prompt as system instruction if possible, or prepended
            contents = f"{MASTER_PROMPT}\n\n{prompt}"

            config = None
            if types is not None:
                config = types.GenerateContentConfig(
                    temperature=0.6,
                )

            response = self.model.models.generate_content(
                model=settings.MODEL_NAME,
                contents=contents,
                config=config,
            )
            text = getattr(response, "text", "") or ""
            return text.strip() or "De cabeça agora não me recordo desse detalhe da planta, mas vou confirmar com a engenharia."
        except Exception as exc:
            logger.error("Erro ao gerar resposta no Gemini: %s", exc)
            return "De cabeça agora não me recordo desse detalhe, mas vou confirmar com a equipe e já te falo!"


ai_service = AIService()
