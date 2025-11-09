import os
import time
import json
import re
import logging
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

PRICE_MIN = float(os.environ.get("PRICE_MIN", "550"))
PRICE_MAX = float(os.environ.get("PRICE_MAX", "600"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "900"))  # 900 = 15 minutos

URLS = json.loads(os.environ.get("PRODUCT_URLS_JSON", "[]"))

STATE_FILE = "state.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1"
}

def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logging.error("TELEGRAM_TOKEN ou CHAT_ID não configurados.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=15)
    except:
        pass


def fetch_price(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        html = r.text

        soup = BeautifulSoup(html, "html.parser")
        symbols = ["R$", "€", "$"]

        text = soup.get_text(" ", strip=True)
        prices = re.findall(r"R\$\s*([0-9\.\,]+)", text)

        if prices:
            p = prices[0].replace(".", "").replace(",", ".")
            return float(p)
    except:
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

    while True:
        mensagem_resumo = "🕒 Atualização automática:\n"

        for loja in URLS:
            nome = loja["name"]
            url = loja["url"]

            price = fetch_price(url)

            if price is None:
                mensagem_resumo += f"{nome}: preço não encontrado ❌\n"
                continue

            mensagem_resumo += f"{nome}: R$ {price:.2f}\n"

            last_price = state.get(nome)

            if last_price != price:
                state[nome] = price
                save_state(state)
                send_telegram(
                    f"🔔 <b>Preço atualizado!</b>\n\n"
                    f"🏪 Loja: {nome}\n"
                    f"💰 Preço: R$ {price:.2f}\n\n{url}"
                )

            if PRICE_MIN <= price <= PRICE_MAX:
                send_telegram(
                    f"✅ <b>Preço dentro da faixa!</b>\n\n"
                    f"🏪 Loja: {nome}\n"
                    f"💰 Preço: R$ {price:.2f}\n\n{url}"
                )

        send_telegram(mensagem_resumo)  # ✅ manda mensagem mesmo sem mudança
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    send_telegram("🤖 Bot iniciado e monitorando preços a cada 15 minutos.")
    monitor()
