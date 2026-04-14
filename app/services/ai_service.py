import asyncio
import logging
import sys
from typing import Any

from app.core.config import settings

try:
    import google.genai as google_genai
except ImportError:
    google_genai = None  # type: ignore

logger = logging.getLogger(__name__)

MASTER_PROMPT = """És um corretor de imóveis de luxo da Riva Incorporadora, a conversar com um cliente pelo WhatsApp.
O teu tom de voz é 100% natural, empático, persuasivo e leve.
REGRAS:
- PROIBIDO COPIAR E COLAR: Nunca repitas as frases exatas da memória. Absorve o dado e cria uma frase coloquial.
- ZERO ROBÓTICA: Nunca digas 'De acordo com os dados', 'Baseado no meu contexto' ou 'Como IA'.
- FLUIDEZ DE WHATSAPP: Escreve mensagens curtas. Não faças listas longas. Usa no máximo 1 a 2 emojis.
- FALTA DE INFORMAÇÃO: Se a informação não estiver na memória, não digas friamente 'Não sei'. Diz algo como: 'De cabeça agora não me recordo desse detalhe da planta, mas vou confirmar com a engenharia. Entretanto, diz-me...'"""

class AIService:
    def __init__(self) -> None:
        self.model: Any = None
        self.chroma_client: Any = None
        self.collection: Any = None

        if settings.GEMINI_API_KEY and google_genai is not None:
            try:
                self.model = google_genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as exc:
                logger.error("Error initializing Gemini client: %s", exc)
                self.model = None

        chromadb = None
        if sys.version_info < (3, 14):
            try:
                import chromadb as chromadb_module
                chromadb = chromadb_module
            except ImportError:
                chromadb = None
        else:
            logger.info("ChromaDB disabled: Python 3.14+ is not yet supported by the package.")

        if chromadb is not None:
            try:
                self.chroma_client = chromadb.PersistentClient(path="data/chroma_db")
                self.collection = self.chroma_client.get_or_create_collection("riva_imoveis")
            except Exception as exc:
                logger.error("Error initializing ChromaDB: %s", exc)
                self.collection = None

    def _query_chroma(self, query: str) -> str:
        if not self.collection:
            return ""
        try:
            # Enforce k=4 results retrieval using CHROMA_K correctly
            results = self.collection.query(query_texts=[query], n_results=settings.CHROMA_K)
            docs = results.get("documents", []) if isinstance(results, dict) else []
            if docs and docs[0]:
                return "\n".join(docs[0])
            return ""
        except Exception as exc:
            logger.error("Error fetching context from ChromaDB: %s", exc)
            return ""

    async def get_context_from_db(self, query: str) -> str:
        """Fetch matching knowledge base chunks concurrently without blocking event loop."""
        return await asyncio.to_thread(self._query_chroma, query)

    def _generate_content_sync(self, prompt: str) -> str:
        fallback_msg = "De cabeça agora não me recordo desse detalhe da planta, mas vou confirmar com a engenharia. Entretanto, diz-me..."
        try:
            response = self.model.models.generate_content(
                model=settings.MODEL_NAME,
                contents=prompt,
                config={
                    "temperature": settings.AI_TEMPERATURE, # Expects 0.6
                    "system_instruction": MASTER_PROMPT
                }
            )
            text = getattr(response, "text", "") or ""
            return text.strip() or fallback_msg
        except Exception as exc:
            logger.error("Error generating response in Gemini: %s", exc)
            return fallback_msg

    async def generate_response(self, user_message: str, context: str = "") -> str:
        """Call LLM synchronously wrapped in an asyncio thread to prevent loop blocking."""
        if not self.model:
            return "De cabeça agora não me recordo desse detalhe da planta, mas vou confirmar com a engenharia. Entretanto, diz-me..."

        prompt = user_message
        if context:
            prompt = f"Relevant info in memory (DO NOT EXACTLY COPY-PASTE):\n{context}\n\nClient: {user_message}"

        return await asyncio.to_thread(self._generate_content_sync, prompt)


ai_service = AIService()
