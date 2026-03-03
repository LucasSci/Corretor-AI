import json
import os
from dotenv import load_dotenv
from openai import OpenAI, APIError, RateLimitError

try:
    import google.genai as google_genai
except Exception:
    google_genai = None

try:
    from google.genai.errors import APIError as GoogleAPIError, ClientError
except Exception:
    GoogleAPIError = Exception
    ClientError = Exception

try:
    from knowledge_manager import intelligence_core
except Exception:
    intelligence_core = None

try:
    from motor_busca import buscar_contexto
except Exception:
    def buscar_contexto(_pergunta: str) -> str:
        return ""

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

cliente_gemini = None
if GEMINI_API_KEY and google_genai is not None:
    try:
        cliente_gemini = google_genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        cliente_gemini = None

cliente_openai = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
modelo_em_uso = "indisponivel"


def _format_response_output(texto: str, return_details: bool):
    if return_details:
        return {"resposta": texto, "modelo_usado": modelo_em_uso}
    return texto


def gerar_resposta_whatsapp(pergunta_cliente: str, cliente_numero: str = None, return_details: bool = False):
    global modelo_em_uso

    contexto_historico = buscar_contexto(pergunta_cliente)

    resultados_inteligencia = {"documents": [], "similarities": []}
    if intelligence_core is not None:
        try:
            resultados_inteligencia = intelligence_core.search_knowledge(pergunta_cliente, n_results=5)
        except Exception:
            resultados_inteligencia = {"documents": [], "similarities": []}

    contexto_inteligencia = "\n".join(
        f"- {doc} (confianca: {sim:.2f})"
        for doc, sim in zip(resultados_inteligencia.get("documents", []), resultados_inteligencia.get("similarities", []))
    )

    contexto_cliente = ""
    if cliente_numero and intelligence_core is not None:
        try:
            perfil = intelligence_core.memory_system.get_client_profile(cliente_numero)
            if perfil:
                preferencias = perfil.get("preferencias", {})
                contexto_cliente = f"Historico do cliente: {json.dumps(preferencias, ensure_ascii=False)}"
        except Exception:
            contexto_cliente = ""

    contexto_recuperado = (
        f"{contexto_historico}\n\n"
        f"[CONHECIMENTO INTELIGENTE ACUMULADO]\n{contexto_inteligencia}\n\n"
        f"{contexto_cliente}"
    ).strip()

    if not contexto_recuperado or len(contexto_recuperado) < 20:
        modelo_em_uso = "fallback_local"
        return _format_response_output(
            "Desculpe, ainda estou aprendendo sobre este assunto. Posso verificar com a gerencia para uma resposta mais precisa?",
            return_details,
        )

    prompt_mestre = f"""
Voce e um corretor de imoveis de alto padrao, especialista nos lancamentos da Riva Vendas.
Seu tom deve ser educado, persuasivo, agil e focado em fechar negocios.
Voce esta respondendo a um cliente no WhatsApp (use emojis moderadamente e paragrafos curtos).

REGRA DE OURO: Use APENAS as informacoes contidas no [CONTEXTO DA BASE DE DADOS] abaixo para responder.
Se a resposta nao estiver no contexto, diga educadamente que vai verificar com a gerencia. Nao invente precos, metragens ou itens de lazer.

[CONTEXTO DA BASE DE DADOS]
{contexto_recuperado}

[PERGUNTA DO CLIENTE]
{pergunta_cliente}
""".strip()

    if cliente_gemini is not None:
        try:
            response = cliente_gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_mestre,
            )
            resposta_text = getattr(response, "text", "") or ""
            if resposta_text.strip():
                modelo_em_uso = "gemini"
                return _format_response_output(resposta_text, return_details)
        except (RateLimitError, APIError, GoogleAPIError, ClientError):
            pass
        except Exception:
            pass

    if cliente_openai is not None:
        try:
            resposta_openai = cliente_openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Voce e um corretor de imoveis de alto padrao, especialista nos lancamentos da Riva Vendas.",
                    },
                    {"role": "user", "content": prompt_mestre},
                ],
                temperature=0.7,
                max_tokens=1500,
            )
            resposta_text = resposta_openai.choices[0].message.content or ""
            if resposta_text.strip():
                modelo_em_uso = "openai"
                return _format_response_output(resposta_text, return_details)
        except Exception:
            pass

    modelo_em_uso = "fallback_local"
    return _format_response_output(
        "Desculpe, estou com dificuldades tecnicas no momento. Por favor, tente novamente em alguns instantes.",
        return_details,
    )


if __name__ == "__main__":
    print("Bot de Corretagem Iniciado! (Digite 'sair' para encerrar)\n")
    while True:
        pergunta = input("Cliente: ")
        if pergunta.lower() == "sair":
            break
        resposta_bot = gerar_resposta_whatsapp(pergunta)
        print(f"\nBot Corretor:\n{resposta_bot}\n")
        print("-" * 50)
