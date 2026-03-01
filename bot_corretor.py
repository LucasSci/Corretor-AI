import os
import json
import google.genai
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError

# Importa exceções do google.genai
try:
    from google.genai.errors import APIError as GoogleAPIError, ClientError
except ImportError:
    # Fallback se as exceções não existirem
    GoogleAPIError = Exception
    ClientError = Exception

# Importa novos sistemas de conhecimento
from knowledge_manager import intelligence_core
from learning_system import learning_system

# função de busca com fallback local/ChromaDB
from motor_busca import buscar_contexto

# Carrega a chave de API do arquivo .env
load_dotenv()

# Configura chave da API do Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY não está configurada no .env")

# Inicializa cliente Gemini
cliente_gemini = google.genai.Client(api_key=GEMINI_API_KEY)

# Inicializa cliente OpenAI
cliente_openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# Flag para rastrear qual modelo está em uso
modelo_em_uso = "gemini"

def gerar_resposta_whatsapp(pergunta_cliente, cliente_numero: str = None):
    """Gera resposta usando conhecimento inteligente acumulado."""
    
    global modelo_em_uso
    
    print(f"\n" + "="*60)
    print(f"🔄 [gerar_resposta_whatsapp] Iniciado")
    print(f"📝 Pergunta recebida: {pergunta_cliente}")
    print(f"="*60)
    
    # 1. Busca contexto em MÚLTIPLAS FONTES
    print(f"🔍 [BUSCA] Consultando base de conhecimento integrada...")
    
    # 1a. Busca na base vetorial histórica
    contexto_historico = buscar_contexto(pergunta_cliente)
    print(f"  📚 Base histórica: {len(contexto_historico)} caracteres")
    
    # 1b. Busca na nova base de inteligência
    resultados_inteligencia = intelligence_core.search_knowledge(pergunta_cliente, n_results=5)
    contexto_inteligencia = "\n".join([
        f"- {doc} (confiança: {sim:.2f})" 
        for doc, sim in zip(resultados_inteligencia['documents'], resultados_inteligencia['similarities'])
    ])
    print(f"  🧠 Base inteligente: {len(contexto_inteligencia)} caracteres")
    
    # 1c. Recuperar informações do cliente se disponível
    contexto_cliente = ""
    if cliente_numero:
        perfil = intelligence_core.memory_system.get_client_profile(cliente_numero)
        if perfil:
            preferencias = perfil.get("preferencias", {})
            contexto_cliente = f"Histórico do cliente: {json.dumps(preferencias, ensure_ascii=False)}"
            print(f"  👤 Perfil do cliente carregado")
    
    # Combinar contextos
    contexto_recuperado = f"""
{contexto_historico}

[CONHECIMENTO INTELIGENTE ACUMULADO]
{contexto_inteligencia}

{contexto_cliente}
    """.strip()
    
    if not contexto_recuperado.strip() or len(contexto_recuperado) < 20:
        print(f"⚠️  [RESPOSTA] Conhecimento limitado, usando resposta genérica")
        return "Desculpe, ainda estou aprendendo sobre este assunto. Posso verificar com a gerência para uma resposta mais precisa?"

    # 2. O 'System Prompt': Onde você define a personalidade do corretor
    prompt_mestre = f"""
    Você é um corretor de imóveis de alto padrão, especialista nos lançamentos da Riva Vendas.
    Seu tom deve ser educado, persuasivo, ágil e focado em fechar negócios.
    Você está respondendo a um cliente no WhatsApp (use emojis moderadamente e parágrafos curtos).

    REGRA DE OURO: Use APENAS as informações contidas no [CONTEXTO DA BASE DE DADOS] abaixo para responder. 
    Se a resposta não estiver no contexto, diga educadamente que vai verificar com a gerência. Não invente preços, metragens ou itens de lazer.

    [CONTEXTO DA BASE DE DADOS]
    {contexto_recuperado}

    [PERGUNTA DO CLIENTE]
    {pergunta_cliente}
    """

    # 3. Tenta Gemini primeiro
    print(f"🧠 [IA] Tentando Google Gemini...")
    try:
        response = cliente_gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_mestre,
        )
        modelo_em_uso = "gemini"
        resposta_text = response.text
        print(f"✅ [IA] Usando Google Gemini")
        print(f"✅ [IA] Resposta gerada com sucesso ({len(resposta_text)} caracteres)")
        print(f"💬 [RESPOSTA] {resposta_text}")
        print(f"="*60 + "\n")
        return resposta_text
    
    except (RateLimitError, APIError, GoogleAPIError, ClientError) as exc:
        print(f"⚠️  [IA] Erro com Gemini (Quota/RateLimit): {str(exc)[:100]}")
        print(f"↩️  [IA] Alternando para OpenAI...")
        
        # Se falhar, tenta OpenAI
        try:
            resposta_openai = cliente_openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um corretor de imóveis de alto padrão, especialista nos lançamentos da Riva Vendas."},
                    {"role": "user", "content": prompt_mestre}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            modelo_em_uso = "openai"
            resposta_text = resposta_openai.choices[0].message.content
            print(f"✅ [IA] Usando OpenAI (GPT-3.5)")
            print(f"✅ [IA] Resposta gerada com sucesso ({len(resposta_text)} caracteres)")
            print(f"💬 [RESPOSTA] {resposta_text}")
            print(f"="*60 + "\n")
            return resposta_text
        
        except Exception as exc_openai:
            print(f"❌ [IA] Erro com OpenAI também: {exc_openai}")
            print(f"="*60 + "\n")
            return "Desculpe, estou com dificuldades técnicas no momento. Por favor, tente novamente em alguns instantes."
    
    except Exception as exc_geral:
        print(f"⚠️  [IA] Erro com Gemini: {str(exc_geral)[:100]}")
        print(f"↩️  [IA] Alternando para OpenAI...")
        
        # Tenta OpenAI mesmo para erros genéricos
        try:
            resposta_openai = cliente_openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um corretor de imóveis de alto padrão, especialista nos lançamentos da Riva Vendas."},
                    {"role": "user", "content": prompt_mestre}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            modelo_em_uso = "openai"
            resposta_text = resposta_openai.choices[0].message.content
            print(f"✅ [IA] Usando OpenAI (GPT-3.5)")
            print(f"✅ [IA] Resposta gerada com sucesso ({len(resposta_text)} caracteres)")
            print(f"💬 [RESPOSTA] {resposta_text}")
            print(f"="*60 + "\n")
            return resposta_text
        
        except Exception as exc_final:
            print(f"❌ [IA] Erro crítico - ambas APIs falharam: {exc_final}")
            print(f"="*60 + "\n")
            return "Desculpe, estou com dificuldades técnicas no momento. Por favor, tente novamente em alguns instantes."

# --- TESTANDO O BOT ---
if __name__ == "__main__":
    print("🤖 Bot de Corretagem Iniciado! (Digite 'sair' para encerrar)\n")
    
    while True:
        pergunta = input("👤 Cliente: ")
        if pergunta.lower() == 'sair':
            break
            
        resposta_bot = gerar_resposta_whatsapp(pergunta)
        
        print(f"\n📲 Bot Corretor:\n{resposta_bot}\n")
        print("-" * 50)