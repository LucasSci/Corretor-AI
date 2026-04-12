import requests
import base64

# Configurações do seu Docker local
url = "http://localhost:8080/instance/create"
headers = {
    "apikey": "lucas_senha_123",  # A senha que você definiu no comando do Docker
    "Content-Type": "application/json"
}

# Dados da nova instância
payload = {
    "instanceName": "BotRiva1",
    "qrcode": True
}

print("⏳ Criando a instância e gerando o QR Code...")

try:
    resposta = requests.post(url, json=payload, headers=headers)
    dados = resposta.json()

    # A Evolution API retorna a imagem em formato de texto (Base64)
    if "qrcode" in dados and "base64" in dados["qrcode"]:
        # Pega apenas a parte do código da imagem
        b64_string = dados["qrcode"]["base64"].split(",")[1]
        
        # Converte o texto de volta para imagem e salva como PNG
        with open("qrcode_bot.png", "wb") as imagem:
            imagem.write(base64.b64decode(b64_string))
            
        print("✅ SUCESSO! O arquivo 'qrcode_bot.png' foi salvo na sua pasta.")
        print("📱 Abra a imagem no seu computador e escaneie com o WhatsApp.")
    else:
        print("⚠️ Resposta inesperada da API (a instância já pode existir):")
        print(dados)

except Exception as e:
    print(f"❌ Erro de conexão com o Docker: {e}")