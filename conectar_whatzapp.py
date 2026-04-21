import base64
import os
from pathlib import Path

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
PREFERRED_INSTANCE = (
    os.getenv("EVOLUTION_INSTANCE")
    or os.getenv("WHATSAPP_INSTANCE")
    or os.getenv("INSTANCIA")
    or "BotRiva"
)
OUTPUT_FILE = Path("qrcode_bot.png")


def _headers() -> dict[str, str]:
    return {
        "apikey": SERVER_API_KEY,
        "Content-Type": "application/json",
    }


def _fetch_instances() -> list[dict]:
    response = requests.get(f"{BASE_URL}/instance/fetchInstances", headers=_headers(), timeout=20)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def _resolve_instance_name() -> str:
    instances = _fetch_instances()
    names = [item.get("instance", {}).get("instanceName") for item in instances]
    names = [name for name in names if name]

    if PREFERRED_INSTANCE in names:
        return PREFERRED_INSTANCE

    if len(names) == 1:
        chosen = names[0]
        print(f"Instancia configurada nao encontrada. Usando a unica instancia existente: {chosen}")
        return chosen

    if names:
        chosen = names[0]
        print(f"Instancia configurada nao encontrada. Usando a primeira instancia encontrada: {chosen}")
        return chosen

    print(f"Criando nova instancia: {PREFERRED_INSTANCE}")
    response = requests.post(
        f"{BASE_URL}/instance/create",
        headers=_headers(),
        json={"instanceName": PREFERRED_INSTANCE, "qrcode": True},
        timeout=20,
    )
    response.raise_for_status()
    return PREFERRED_INSTANCE


def _save_qr_png(base64_png: str) -> None:
    if "," in base64_png:
        base64_png = base64_png.split(",", 1)[1]
    OUTPUT_FILE.write_bytes(base64.b64decode(base64_png))


def main() -> None:
    instance_name = _resolve_instance_name()
    print(f"Solicitando QR Code da instancia: {instance_name}")

    response = requests.get(
        f"{BASE_URL}/instance/connect/{instance_name}",
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    qr_base64 = data.get("base64")
    pairing_code = data.get("pairingCode")

    if qr_base64:
        _save_qr_png(qr_base64)
        print(f"QR Code salvo em: {OUTPUT_FILE.resolve()}")
    else:
        print("A API nao retornou imagem do QR Code.")

    if pairing_code:
        print(f"Pairing code: {pairing_code}")

    if not qr_base64 and not pairing_code:
        print(f"Resposta da API: {data}")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else str(exc)
        print(f"Erro HTTP ao falar com a Evolution API: {body}")
    except Exception as exc:
        print(f"Falha ao gerar o QR Code: {exc}")
