import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = (os.getenv("URL_EVOLUTION") or "http://127.0.0.1:8080").rstrip("/")
SERVER_API_KEY = (
    os.getenv("API_KEY_EVOLUTION")
    or os.getenv("WHATSAPP_API_TOKEN")
    or os.getenv("WHATSAPP_API_KEY")
    or "lucas_senha_123"
)
INSTANCE_NAME = (
    os.getenv("EVOLUTION_INSTANCE")
    or os.getenv("WHATSAPP_INSTANCE")
    or os.getenv("INSTANCIA")
    or "BotRiva"
)
PORT = os.getenv("PORT", "8000")
WEBHOOK_URL = os.getenv("EVOLUTION_WEBHOOK_URL") or f"http://host.docker.internal:{PORT}/webhook"


def main() -> None:
    url = f"{BASE_URL}/webhook/set/{INSTANCE_NAME}"
    headers = {
        "apikey": SERVER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "url": WEBHOOK_URL,
        "webhook_by_events": False,
        "webhook_base64": False,
        "events": [
            "MESSAGES_UPSERT",
        ],
    }

    print(f"Configurando webhook da instancia {INSTANCE_NAME}")
    print(f"Destino: {WEBHOOK_URL}")

    response = requests.post(url, json=payload, headers=headers, timeout=20)
    response.raise_for_status()
    print(response.json())


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else str(exc)
        print(f"Erro HTTP ao configurar webhook: {body}")
    except Exception as exc:
        print(f"Falha ao configurar webhook: {exc}")
