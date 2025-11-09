# bot.py
import os
import time
import json
import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "900"))  # Agora 15 minutos
STATE_FILE = "state.json"

URLS = json.loads(os.environ.get("PRODUCT_URLS_JSON", "[]"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1"
    )
}

# Se quiser ativar proxy, ajuste aqui:
PROXIES = None
# Exemplo:
# PROXIES = {
#     "http": "http://user:pass@157.175.42.134:3902",
#     "https": "http://user:pass@157.175.42.134:3902"
# }


def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logging.error("TELEGRAM_TOKEN ou CHAT_ID não configurados.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=15)
        r.raise_for_status()
        logging.info("Mensagem enviada ao Telegram.")
    except Exception as e:
        logging.exception("Erro ao enviar mensagem Telegram: %s", e)


def extract_price_from_text(text: str) -> Optional[float]:
    patterns = [
        r"R\$\s*([0-9\.\,]{1,})",
        r"([0-9\.\,]{1,})\s*R\$",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            raw = m.group(1)
            num = raw.replace('.', '').replace(',', '.')
            try:
                return float(num)
            except:
                continue
    m = re.search(r"([0-9]{2,}\,[0-9]{2})", text)
    if m:
        try:
            return float(m.group(1).replace('.', '').replace(',', '.'))
        except:
            pass
    return None


def fetch_price(url: str) -> Optional[float]:
    try:
        if PROXIES:
            r = requests.get(url, headers=HEADERS, timeout=20, proxies=PROXIES)
        else:
            r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()

        html = r.text

        price = extract_price_from_text(html)
        if price:
            return price

        soup = BeautifulSoup(html, "html.parser")
        selectors = [
            "span.price", ".price", ".product-price", ".price-tag",
            ".valor", ".preco", ".price-wrapper"
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                p = extract_price_from_text(el.get_text(strip=True))
                if p:
                    return p

    except Exception as e:
        logging.warning("Erro ao buscar preço em %s: %s", url, e)
    return None


def load_state() -> Dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_state(state: Dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def main_loop():
    state = load_state()
    logging.info("Iniciando monitor de preços. Intervalo: %s segundos", POLL_INTERVAL)

    while True:
        alerts = 0
        for url in URLS:
            store_name = url.split("/")[2]
            price = fetch_price(url)
            state[url] = price
            save_state(state)

            send_telegram(f"Preço atual em {store_name}: R$ {price if price else '??'}\n{url}")
            alerts += 1

        logging.info("Check concluído. Alerts: %s", alerts)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main_loop()
