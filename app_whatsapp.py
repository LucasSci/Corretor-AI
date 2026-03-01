from fastapi import FastAPI, Request, BackgroundTasks
import requests
import os
import logging
from typing import Optional, Any, Dict
from dotenv import load_dotenv

# Carrega variaveis de ambiente do arquivo .env (se existir)
load_dotenv()

from bot_corretor import gerar_resposta_whatsapp
from learning_system import learning_system

app = FastAPI(title="Bot Corretor Riva Vendas")

# Configuracoes da API do WhatsApp
URL_EVOLUTION = "http://localhost:8080"
INSTANCIA = "BotRiva1"
API_KEY_EVOLUTION = "lucas_senha_123"

WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", URL_EVOLUTION)
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", API_KEY_EVOLUTION)

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), force=True)
logger = logging.getLogger("app_whatsapp")


def _console_log(message: str, level: str = "info") -> None:
    log_fn = getattr(logger, level, logger.info)
    log_fn(message)
    print(message, flush=True)


def _normalize_number(number: Optional[str]) -> Optional[str]:
    if not number:
        return None
    if "@" in number:
        return number.split("@", 1)[0]
    return number


def _extract_message_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}

    key_obj: Dict[str, Any] = {}
    message_obj: Dict[str, Any] = {}

    # Evolution: data.message + data.key
    if isinstance(data.get("message"), dict):
        message_obj = data.get("message", {})
        key_obj = data.get("key", {}) if isinstance(data.get("key"), dict) else {}

    # Evolution variant: data.messages[]
    if (not message_obj) and isinstance(data.get("messages"), list) and data["messages"]:
        first = data["messages"][0]
        if isinstance(first, dict):
            if isinstance(first.get("message"), dict):
                message_obj = first["message"]
            elif isinstance(first.get("text"), dict):
                message_obj = {"text": first["text"]}
            key_obj = first.get("key", {}) if isinstance(first.get("key"), dict) else {}

    # Meta-like root: messages[]
    if (not message_obj) and isinstance(payload.get("messages"), list) and payload["messages"]:
        first = payload["messages"][0]
        if isinstance(first, dict):
            if isinstance(first.get("message"), dict):
                message_obj = first["message"]
            elif isinstance(first.get("text"), dict):
                message_obj = {"text": first["text"]}
            key_obj = first.get("key", {}) if isinstance(first.get("key"), dict) else {}

    # Extract sender number/jid
    remote_jid = None
    if isinstance(data.get("key"), dict):
        remote_jid = data["key"].get("remoteJid")
    if not remote_jid and isinstance(key_obj, dict):
        remote_jid = key_obj.get("remoteJid")
    if not remote_jid:
        remote_jid = data.get("from") or payload.get("from")
    if (not remote_jid) and isinstance(payload.get("messages"), list) and payload["messages"]:
        first = payload["messages"][0]
        if isinstance(first, dict):
            remote_jid = first.get("from")

    from_me = False
    if isinstance(data.get("key"), dict):
        from_me = bool(data["key"].get("fromMe"))
    if not from_me and isinstance(key_obj, dict):
        from_me = bool(key_obj.get("fromMe"))

    return {
        "data": data,
        "message": message_obj,
        "key": key_obj,
        "remote_jid": remote_jid,
        "from_me": from_me,
    }


def _extract_text(payload: Dict[str, Any], message_obj: Dict[str, Any]) -> str:
    text = ""

    if "conversation" in message_obj and isinstance(message_obj.get("conversation"), str):
        text = message_obj["conversation"]
    elif isinstance(message_obj.get("extendedTextMessage"), dict):
        text = message_obj["extendedTextMessage"].get("text", "")
    elif isinstance(message_obj.get("text"), dict):
        text = message_obj["text"].get("body", "")
    elif isinstance(message_obj.get("text"), str):
        text = message_obj["text"]

    if not text and isinstance(payload.get("body"), str):
        text = payload["body"]

    return text.strip()


def enviar_mensagem_whatsapp(numero_cliente: str, texto_resposta: str):
    """Envia a resposta de volta para o cliente via WhatsApp."""
    
    print(f"\n" + "="*60)
    print(f"📤 [enviar_mensagem_whatsapp] Iniciado")
    print(f"📞 Numero destino: {numero_cliente}")
    print(f"💬 Texto a enviar: {texto_resposta[:100]}...")
    print(f"="*60)

    numero_norm = _normalize_number(numero_cliente)
    print(f"✅ Numero normalizado: {numero_norm}")

    bot_num = os.getenv("WHATSAPP_BOT_NUMBER")
    if bot_num and numero_norm == _normalize_number(bot_num):
        _console_log(f"[AUTO] Mensagem para o proprio numero ({numero_norm}): {texto_resposta}", "info")
        return True

    headers = {"Content-Type": "application/json"}
    if WHATSAPP_API_TOKEN:
        if WHATSAPP_API_TOKEN.lower().startswith("bearer "):
            headers["Authorization"] = WHATSAPP_API_TOKEN
        else:
            headers["apikey"] = WHATSAPP_API_TOKEN
    print(f"✅ Headers preparados")

    if WHATSAPP_API_URL.rstrip("/") == URL_EVOLUTION.rstrip("/"):
        print(f"\n🔄 Tentativa 1: Evolution API")
        endpoint = f"{URL_EVOLUTION.rstrip('/')}/message/sendText/{INSTANCIA}"
        payload = {
            "number": numero_norm,
            "options": {"delay": 1200, "presence": "composing"},
            "textMessage": {"text": texto_resposta},
        }

        _console_log(f"[Evolution] Enviando para {numero_norm} | endpoint={endpoint}", "info")
        print(f"  Endpoint: {endpoint}")
        print(f"  Payload: {str(payload)[:200]}")
        try:
            resp = requests.post(
                endpoint,
                json=payload,
                headers={"apikey": API_KEY_EVOLUTION, "Content-Type": "application/json"},
                timeout=15,
            )
            print(f"  Status Code: {resp.status_code}")
            print(f"  Response: {resp.text[:200]}")
            if resp.status_code in (200, 201):
                _console_log(f"[OK] Mensagem enviada para {numero_norm} via Evolution.", "info")
                print(f"\n✅ SUCESSO: Mensagem entregue via Evolution!")
                print(f"="*60 + "\n")
                return True
            _console_log(f"[ERRO] Evolution ({resp.status_code}): {resp.text}", "warning")
        except Exception as exc:
            _console_log(f"[ERRO] Falha na requisicao Evolution: {exc}", "error")
            print(f"  ❌ Erro: {exc}")

    payloads = [
        {"number": numero_norm, "textMessage": {"text": texto_resposta}},
        {"phone": numero_norm, "message": texto_resposta},
        {"to": numero_norm, "type": "text", "text": {"body": texto_resposta}},
    ]

    last_exc = None
    for idx, p in enumerate(payloads, start=1):
        print(f"\n🔄 Tentativa {idx + 1}: Payload generico")
        _console_log(f"[Tentativa] Envio generico para {numero_norm}", "info")
        print(f"  URL: {WHATSAPP_API_URL}")
        print(f"  Payload: {str(p)[:200]}")
        try:
            resp = requests.post(WHATSAPP_API_URL, json=p, headers=headers, timeout=10)
            print(f"  Status Code: {resp.status_code}")
            print(f"  Response: {resp.text[:200]}")
            if 200 <= resp.status_code < 300:
                _console_log(f"[OK] Mensagem enviada para {numero_norm} com status {resp.status_code}", "info")
                print(f"\n✅ SUCESSO: Mensagem entregue!")
                print(f"="*60 + "\n")
                return True
            _console_log(f"[ERRO] Falha envio ({resp.status_code})", "warning")
            print(f"  ⚠️ Falhou com status {resp.status_code}")
            last_exc = Exception(f"status {resp.status_code}")
        except Exception as exc:
            _console_log(f"[ERRO] Erro ao enviar: {exc}", "warning")
            print(f"  ❌ Erro: {exc}")
            last_exc = exc

    print(f"\n❌ FALHA: Nao foi possivel enviar a mensagem para {numero_norm}")
    print(f"  Ultimo erro: {last_exc}")
    print(f"="*60 + "\n")
    logger.error("Nao foi possivel enviar mensagem para %s: %s", numero_norm, last_exc)
    return False


@app.post("/webhook")
async def receber_mensagem(request: Request, background_tasks: BackgroundTasks):
    """Recebe webhook e processa mensagens."""
    
    print(f"\n" + "#"*60)
    print(f"#" + " "*58 + "#")
    print(f"#" + " "*10 + "📬 NOVA MENSAGEM RECEBIDA NO WEBHOOK!" + " "*12 + "#")
    print(f"#" + " "*58 + "#")
    print(f"#"*60)

    dados = await request.json()
    _console_log(f"[WEBHOOK] Payload recebido: {str(dados)[:1500]}", "info")
    print(f"\n📃 Tamanho do payload: {len(str(dados))} caracteres")

    event_raw = str(dados.get("event", "")).strip()
    event_norm = event_raw.lower().replace("_", ".")
    if event_raw and event_norm != "messages.upsert":
        print(f"⚠️  [SKIP] Evento ignorado: {event_raw}")
        _console_log(f"[WEBHOOK] Evento ignorado: {event_raw}", "info")
        return {"status": "ignorado", "motivo": "evento"}

    try:
        ctx = _extract_message_context(dados)
        numero_cliente = ctx.get("remote_jid")

        if not numero_cliente:
            print(f"\n⚠️  [SKIP] NUMERO NAO ENCONTRADO")
            _console_log(f"[WEBHOOK] Numero nao encontrado no pacote: {dados}", "warning")
            return {"status": "ignorado", "motivo": "numero_nao_encontrado"}

        if "@lid" in str(numero_cliente):
            print(f"🔄 ID interno detectado, redirecionando...")
            _console_log("[WEBHOOK] ID interno detectado. Redirecionando para numero de teste.", "warning")
            numero_cliente = os.getenv("WHATSAPP_TEST_NUMBER", str(numero_cliente))

        if "@g.us" in str(numero_cliente) or "status@broadcast" in str(numero_cliente):
            print(f"\n⚠️  [SKIP] Mensagem de grupo ou status ignorada")
            _console_log(f"[WEBHOOK] Mensagem de grupo/status ignorada: {numero_cliente}", "info")
            return {"status": "ignorado", "motivo": "grupo_ou_status"}

        # ℹ️ Permitindo from_me=True durante TESTES - remover em produção
        # if ctx.get("from_me") is True:
        #     print(f"\n⚠️  [SKIP] Mensagem enviada pelo BOT (fromMe=True)")
        #     _console_log(f"[WEBHOOK] Mensagem com fromMe=True ignorada: {numero_cliente}", "info")
        #     return {"status": "ignorado", "motivo": "from_me"}

        texto_recebido = _extract_text(dados, ctx.get("message", {}))
        if not texto_recebido:
            print(f"\n⚠️  [SKIP] Mensagem vazia")
            _console_log(f"[WEBHOOK] Mensagem vazia, ignorando: {dados}", "info")
            return {"status": "ignorado", "motivo": "mensagem_vazia"}

        numero_log = str(numero_cliente).split("@", 1)[0]
        print(f"\n🗣️  Cliente: {numero_log}")
        print(f"💬 Mensagem recebida: {texto_recebido}")
        _console_log(f"[WHATSAPP] Cliente {numero_log} diz: {texto_recebido}", "info")

        print(f"\n⏳ Aguarde... chamando BOT para gerar resposta...")
        resposta_inteligente = gerar_resposta_whatsapp(texto_recebido, cliente_numero=numero_cliente)
        _console_log(f"[BOT] Resposta gerada para {numero_log}: {resposta_inteligente}", "info")
        print(f"\n🤖 Resposta do BOT pronta!")
        
        # Registrar aprendizado
        print(f"\n📚 Registrando aprendizado da interação...")
        learning_system.process_interaction({
            "cliente_numero": numero_cliente,
            "pergunta": texto_recebido,
            "resposta": resposta_inteligente,
            "modelo_usado": "gemini"  # Padrão, pode ser atualizado conforme necessário
        })
        
        print(f"\n📤 Agendando envio da mensagem..")

        background_tasks.add_task(enviar_mensagem_whatsapp, str(numero_cliente), resposta_inteligente)
        print(f"✅ Tarefa agendada com sucesso!\n")
        return {"status": "sucesso"}

    except Exception as exc:
        print(f"\n🛑 ERRO NO WEBHOOK: {exc}\n")
        logger.exception("Erro no webhook")
        return {"status": "erro", "detalhe": str(exc)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
