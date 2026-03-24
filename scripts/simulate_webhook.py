import requests
import json

URL = "http://localhost:8000/webhook"

payloads = [
    # Evolution-like
    {
        "data": {
            "message": {"conversation": "Olá, qual o preço do apartamento 101?"},
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False}
        }
    },
    # Meta-like messages array
    {
        "messages": [
            {"text": {"body": "Tem vaga de garagem?"}, "from": "5511888888888"}
        ]
    },
    # Simple body
    {"body": "Quero agendar visita", "from": "5511777777777"},
    # Self-test: mensagem vinda do próprio número (fromMe True)
    {
        "data": {
            "message": {"conversation": "Teste interno para mim mesmo"},
            "key": {"remoteJid": "551975907217@s.whatsapp.net", "fromMe": True}
        }
    }
]

for p in payloads:
    try:
        r = requests.post(URL, json=p, timeout=5)
        print("Enviado payload, status:", r.status_code, r.text)
    except Exception as e:
        print("Erro ao enviar payload:", e)
