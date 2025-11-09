import os
import time
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_message(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text}
        requests.post(url, json=data)
        print(f"Mensagem enviada: {text}")
    except Exception as e:
        print("Erro ao enviar mensagem:", e)

def main():
    while True:
        send_message("oi")
        time.sleep(30)  # 30 segundos

if __name__ == "__main__":
    send_message("Bot iniciado (modo teste).")
    main()
