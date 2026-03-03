import logging
from typing import Dict, List, Any, Optional
import google.generativeai as genai
import chromadb

from app.core.config import settings

logger = logging.getLogger(__name__)

MASTER_PROMPT: str = """És um corretor de imóveis de luxo da Riva Incorporadora, a conversar com um cliente pelo WhatsApp.
O teu tom de voz é 100% natural, empático, persuasivo e leve.
REGRAS:
- PROIBIDO COPIAR E COLAR: Nunca repitas as frases exatas da memória. Absorve o dado e cria uma frase coloquial.
- ZERO ROBÓTICA: Nunca digas 'De acordo com os dados', 'Baseado no meu contexto' ou 'Como IA'.
- FLUIDEZ DE WHATSAPP: Escreve mensagens curtas. Não faças listas longas. Usa no máximo 1 a 2 emojis.
- FALTA DE INFORMAÇÃO: Se a informação não estiver na memória, não digas friamente 'Não sei'. Diz algo como: 'De cabeça agora não me recordo desse detalhe da planta, mas vou confirmar com a engenharia. Entretanto, diz-me...'"""

class AIService:
    def __init__(self) -> None:
        try:
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel(
                    "gemini-1.5-pro",
                    system_instruction=MASTER_PROMPT,
                    generation_config=genai.GenerationConfig(
                        temperature=settings.AI_TEMPERATURE
                    )
                )
            else:
                self.model = None

            self.chroma_client = chromadb.PersistentClient(path="data/chroma_db")
            self.collection = self.chroma_client.get_or_create_collection("riva_imoveis")
        except Exception as e:
            logger.error(f"Erro ao inicializar serviços de IA: {e}")
            self.model = None
            self.collection = None

    async def get_context_from_db(self, query: str) -> str:
        if not self.collection:
            return ""

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=settings.CHROMA_K
            )

            if results and results.get("documents") and len(results["documents"]) > 0:
                return "\n".join(results["documents"][0])
            return ""
        except Exception as e:
            logger.error(f"Erro ao buscar contexto no ChromaDB: {e}")
            return ""

    async def generate_response(self, user_message: str, context: str = "") -> str:
        if not self.model:
            return "Estou com um pouco de instabilidade no sistema agora, podemos falar mais tarde?"

        try:
            prompt: str = user_message
            if context:
                prompt = f"Informação relevante:\n{context}\n\nCliente: {user_message}"

            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Erro ao gerar resposta com Gemini: {e}")
            return "Vou verificar essa informação e já te retorno!"

ai_service = AIService()
