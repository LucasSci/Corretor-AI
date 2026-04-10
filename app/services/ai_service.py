import logging
import sys
from typing import Any, Dict, Optional

try:
    import google.genai as google_genai
except Exception:
    google_genai = None

from app.core.config import settings

logger = logging.getLogger(__name__)

import asyncio

MASTER_PROMPT = """És um corretor de imóveis de luxo da Riva Incorporadora, a conversar com um cliente pelo WhatsApp.
O teu tom de voz é 100% natural, empático, persuasivo e leve.
REGRAS:
- PROIBIDO COPIAR E COLAR: Nunca repitas as frases exatas da memória. Absorve o dado e cria uma frase coloquial.
- ZERO ROBÓTICA: Nunca digas 'De acordo com os dados', 'Baseado no meu contexto' ou 'Como IA'.
- FLUIDEZ DE WHATSAPP: Escreve mensagens curtas. Não faças listas longas. Usa no máximo 1 a 2 emojis.
- FALTA DE INFORMAÇÃO: Se a informação não estiver na memória, não digas friamente 'Não sei'. Diz algo como: 'De cabeça agora não me recordo desse detalhe da planta, mas vou confirmar com a engenharia. Entretanto, diz-me...'"""

class AIService:
    def __init__(self):
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

    def _query_chroma(self, query: str) -> str:
        if not self.collection:
            return ""
        try:
            results = self.collection.query(query_texts=[query], n_results=settings.CHROMA_K)
            docs = results.get("documents", []) if isinstance(results, dict) else []
            if docs and docs[0]:
                return "\n".join(docs[0])
            return ""
        except Exception as exc:
            logger.error("Erro ao buscar contexto no ChromaDB: %s", exc)
            return ""

    async def get_context_from_db(self, query: str) -> str:
        return await asyncio.to_thread(self._query_chroma, query)

    def _generate_content_sync(self, prompt: str) -> str:
        try:
            response = self.model.models.generate_content(
                model=settings.MODEL_NAME,
                contents=prompt,
                config={
                    "temperature": settings.AI_TEMPERATURE,
                    "system_instruction": MASTER_PROMPT
                }
            )
            text = getattr(response, "text", "") or ""
            return text.strip() or "De cabeça agora não me recordo desse detalhe, mas vou confirmar com a engenharia. Entretanto, diz-me..."
        except Exception as exc:
            logger.error("Erro ao gerar resposta no Gemini: %s", exc)
            return "De cabeça agora não me recordo desse detalhe, mas vou confirmar com a engenharia. Entretanto, diz-me..."

    async def generate_response(self, user_message: str, context: str = "") -> str:
        if not self.model:
            return "De cabeça agora não me recordo desse detalhe, mas vou confirmar com a engenharia. Entretanto, diz-me..."

        prompt = user_message
        if context:
            prompt = f"Informacao relevante na memoria (NÃO COPIE EXATAMENTE):\n{context}\n\nCliente: {user_message}"

        return await asyncio.to_thread(self._generate_content_sync, prompt)


ai_service = AIService()
