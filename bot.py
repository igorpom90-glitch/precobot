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
CHECK_INTERVAL = 300  # Checa a cada 5 minutos
ACTIVE_INTERVAL = 600  # Mensagem de "ainda ativo" a cada 10 minutos
STATE_FILE = "state_motherboard.json"

URLS = json.loads(os.environ.get("PRODUCT_URLS_JSON", "[]"))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1"
}

TIMEZONE = pytz.timezone("America/Sao_Paulo")

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
    last_active = 0
    last_day = None

    while True:
        now = datetime.now(TIMEZONE)
        current_day = now.date()
        current_time = now.strftime("%H:%M:%S")

        # ---------- Mensagem de início do dia ----------
        if last_day != current_day:
            last_day = current_day
            send_telegram(f"🤖 Dia {now.strftime('%d/%m/%Y')} - 00:00:00, começando updates de monitoramento de preços de 10 em 10 minutos.")

        # ---------- Mensagem de "ainda ativo" ----------
        if time.time() - last_active >= ACTIVE_INTERVAL:
            send_telegram(f"🤖 Ainda estou ativo - {current_time}, verificando preços de placas-mãe...")
            last_active = time.time()

        # ---------- Checagem de preços ----------
        promotions_found = False
        for loja in URLS:
            nome = loja.get("name", "Loja desconhecida")
            url = loja.get("url", "")
            price = fetch_price(url)

            if price is None:
                continue

            last_price = state.get(nome)

            if last_price != price:
                state[nome] = price
                save_state(state)
                send_telegram(f"🔔 Preço atualizado!\n🏪 {nome}\n💰 R$ {price:.2f}\n{url}")

            if PRICE_MIN <= price <= PRICE_MAX:
                send_telegram(f"✅ Achei placa-mãe a preço {price:.2f} na loja {nome}\n{url}")
                promotions_found = True

        if not promotions_found:
            send_telegram(f"🤖 Ainda estou ativo - {current_time}, promoção da placa-mãe não encontrada em nenhuma loja.")

        time.sleep(CHECK_INTERVAL)

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
    send_telegram("🤖 Bot de placas-mãe iniciado. Monitorando preços e enviando atualizações a cada 10 minutos.")
    threading.Thread(target=monitor, daemon=True).start()
    start_web()
