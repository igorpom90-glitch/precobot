import os
import time
import json
import re
import logging
import requests
from bs4 import BeautifulSoup
from flask import Flask
import threading

# ---------------------- LOG -----------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------------------- CONFIG -----------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

PRICE_MIN = float(os.environ.get("PRICE_MIN", "550"))
PRICE_MAX = float(os.environ.get("PRICE_MAX", "600"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "900"))  # 900 = 15 min

URLS = json.loads(os.environ.get("PRODUCT_URLS_JSON", "[]"))

STATE_FILE = "state.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1"
}

# ---------------------- FUNÇÕES -----------------------
def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logging.error("TELEGRAM_TOKEN ou CHAT_ID não configurados.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        logging.error(f"Erro ao enviar Telegram: {e}")


def fetch_price(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
        prices = re.findall(r"R\$\s*([0-9\.\,]+)", text)
        if prices:
            return float(prices[0].replace(".", "").replace(",", "."))
    except Exception as e:
        logging.error(f"Erro ao buscar preço de {url}: {e}")
    return None


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def monitor():
    state = load_state()
    logging.info("Loop de monitoramento iniciado.")
    while True:
        mensagem_resumo = "🕒 Atualização automática:\n"

        for loja in URLS:
            nome = loja.get("name", "Loja desconhecida")
            url = loja.get("url", "")
            price = fetch_price(url)

            if price is None:
                mensagem_resumo += f"{nome}: preço não encontrado ❌\n"
                continue

            mensagem_resumo += f"{nome}: R$ {price:.2f}\n"

            last_price = state.get(nome)

            if last_price != price:
                state[nome] = price
                save_state(state)
                send_telegram(f"🔔 <b>Preço atualizado!</b>\n\n🏪 {nome}\n💰 R$ {price:.2f}\n{url}")

            if PRICE_MIN <= price <= PRICE_MAX:
                send_telegram(f"✅ <b>Preço dentro da faixa!</b>\n\n🏪 {nome}\n💰 R$ {price:.2f}\n{url}")

        logging.info(mensagem_resumo)
        time.sleep(POLL_INTERVAL)


# ---------------------- SERVIDOR WEB -----------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot rodando ✅"


def start_web():
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Flask rodando na porta {port}")
    app.run(host="0.0.0.0", port=port)


# ---------------------- MAIN -----------------------
if __name__ == "__main__":
    send_telegram("🤖 Bot iniciado. Monitorando preços a cada 15 minutos.")
    
    # Inicia monitoramento em thread separada
    threading.Thread(target=monitor, daemon=True).start()
    
    # Inicia Flask
    start_web()
