import os
import time
import json
import re
import logging
import requests
from bs4 import BeautifulSoup
from flask import Flask
import threading
from datetime import datetime, timedelta
import pytz

# ---------------------- LOG -----------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------------------- CONFIG -----------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

PRICE_MIN = 300.0
PRICE_MAX = 600.0
CHECK_INTERVAL = 300  # 10 minutos

STATE_FILE = "state_motherboard.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1"
}

# ---------------------- LOJAS -----------------------
URLS = [
    {"name": "Amazon", "url": "https://www.amazon.com.br/s?k=ASRock+B450M+Steel+Legend"},
    {"name": "Mercado Livre", "url": "https://www.mercadolivre.com.br/placa-mãe-ASRock-B450M-Steel-Legend"},
    {"name": "Casas Bahia", "url": "https://www.casasbahia.com.br/placa-mãe-ASRock-B450M-Steel-Legend"},
    {"name": "Magazine Luiza", "url": "https://www.magazineluiza.com.br/placa-mãe-ASRock-B450M-Steel-Legend"},
    {"name": "Pichau", "url": "https://www.pichau.com.br/placa-mãe-ASRock-B450M-Steel-Legend"},
    {"name": "Kabum", "url": "https://www.kabum.com.br/produto/placa-mãe-ASRock-B450M-Steel-Legend"},
    {"name": "Fast Shop", "url": "https://www.fastshop.com.br/placa-mãe-ASRock-B450M-Steel-Legend"},
    {"name": "ShopFacil", "url": "https://www.shopfacil.com.br/placa-mãe-ASRock-B450M-Steel-Legend"},
    {"name": "Carrefour", "url": "https://www.carrefour.com.br/placa-mãe-ASRock-B450M-Steel-Legend"},
    {"name": "Submarino", "url": "https://www.submarino.com.br/placa-mãe-ASRock-B450M-Steel-Legend"}
]

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

# ---------------------- MONITOR -----------------------
def monitor():
    state = load_state()
    logging.info("Loop de monitoramento iniciado.")

    tz = pytz.timezone("America/Sao_Paulo")

    while True:
        now = datetime.now(tz)
        # ---------- Mensagem de início do dia à meia-noite ----------
        if now.hour == 0 and now.minute == 0:
            send_telegram(f"🤖 {now.strftime('%d/%m/%Y %H:%M:%S')} - Irei começar a enviar updates de preço a cada 10 minutos hoje.")

        # ---------- Checagem de preços ----------
        found_any = False
        for loja in URLS:
            nome = loja.get("name", "Loja desconhecida")
            url = loja.get("url", "")
            price = fetch_price(url)
            if price is None:
                continue
            if PRICE_MIN <= price <= PRICE_MAX:
                send_telegram(f"🤖 {now.strftime('%H:%M:%S')} - Produto ASRock B450M Steel Legend a R$ {price:.2f} na loja {nome}\n{url}")
                found_any = True
                state[nome] = price
                save_state(state)

        if not found_any:
            send_telegram(f"🤖 {now.strftime('%H:%M:%S')} - Promoção do produto ASRock B450M Steel Legend não encontrada em nenhuma loja.")

        # ---------- Espera 10 minutos ----------
        time.sleep(CHECK_INTERVAL)

# ---------------------- SERVIDOR WEB -----------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot ASRock B450M Steel Legend rodando ✅"

def start_web():
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Flask rodando na porta {port}")
    app.run(host="0.0.0.0", port=port)

# ---------------------- MAIN -----------------------
if __name__ == "__main__":
    send_telegram("🤖 Bot ASRock B450M Steel Legend iniciado. Monitorando preços a cada 10 minutos.")
    threading.Thread(target=monitor, daemon=True).start()
    start_web()
