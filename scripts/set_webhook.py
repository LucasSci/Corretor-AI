import os
import requests
from dotenv import load_dotenv

load_dotenv()

# 1. Coloque o nome da instância que você conectou o QR Code
NOME_INSTANCIA = os.getenv("EVOLUTION_INSTANCE", "")

# 2. Coloque a URL gerada pelo Ngrok + /webhook no final
URL_NGROK = os.getenv("WEBHOOK_URL", "https://alexander-irreproachable-wayne.ngrok-free.dev/webhook")

URL_EVOLUTION = os.getenv("URL_EVOLUTION", "").rstrip("/")
API_KEY_EVOLUTION = os.getenv("API_KEY_EVOLUTION", "")

url = f"{URL_EVOLUTION}/webhook/set/{NOME_INSTANCIA}"

headers = {
    "apikey": API_KEY_EVOLUTION,
    "Content-Type": "application/json"
}

payload = {
    "url": URL_NGROK,
    "webhook_by_events": False,
    "webhook_base64": False,
    "events": [
        "MESSAGES_UPSERT" # Só queremos ser avisados de novas mensagens
    ]
}

print("Configurando a ponte entre o WhatsApp e a sua IA...")

try:
    resposta = requests.post(url, json=payload, headers=headers)
    
    # Agora aceitamos o 200 (OK) e o 201 (Created/Criado)
    if resposta.status_code in [200, 201]:
        print("✅ WEBHOOK CONFIGURADO COM SUCESSO!")
        print(f"Status da API: {resposta.status_code}")
        print("A ponte com o seu Ngrok está perfeita.")
    else:
        print(f"❌ ERRO REAL ({resposta.status_code}): {resposta.text}")
except Exception as e:
    print(f"Erro no script: {e}")