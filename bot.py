# bot.py
import os
import time
import json
import re
import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
PRICE_MIN = float(os.environ.get("PRICE_MIN", "550"))
PRICE_MAX = float(os.environ.get("PRICE_MAX", "600"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "3600"))  # em segundos
STATE_FILE = "state.json"

URLS = json.loads(os.environ.get("PRODUCT_URLS_JSON", "[]"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1"
    )
}

PROXIES = None  # ou configure se quiser usar proxy


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
            "#priceblock_ourprice", "#priceblock_dealprice", ".product-price__value",
            ".price-sales", ".valor", ".preco", ".price-wrapper"
        ]
        candidates = []
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if text:
                    candidates.append(text)
        for c in candidates:
            p = extract_price_from_text(c)
            if p:
                return p
    except requests.exceptions.HTTPError as he:
        logging.warning("Erro ao buscar preço em %s: %s", url, he)
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


def nice_price(p: float) -> str:
    return f"R$ {p:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def check_all():
    state = load_state()
    alerts = []
    for item in URLS:
        store = item.get("store", "Loja")
        url = item.get("url")
        if not url:
            continue
        price = fetch_price(url)
        logging.info("Store %s price fetched: %s", store, price)
        last_notified = state.get(url, {}).get("last_notified_price")
        if price is None:
            state.setdefault(url, {})["last_price"] = None
            continue
        in_range = (PRICE_MIN <= price <= PRICE_MAX) or (price < PRICE_MIN)
        should_notify = False
        if in_range:
            if last_notified is None or abs(price - last_notified) >= 1.0:
                should_notify = True
        state.setdefault(url, {})["last_price"] = price
        if should_notify:
            state[url]["last_notified_price"] = price
            alerts.append((store, price, url))
    save_state(state)
    for store, price, url in alerts:
        msg = (f"⚠️ <b>Alerta de preço</b>\n\n"
               f"Loja: {store}\n"
               f"Preço: {nice_price(price)}\n"
               f"Faixa: R$ {PRICE_MIN:.2f} - R$ {PRICE_MAX:.2f}\n"
               f"{url}")
        send_telegram(msg)
    return alerts


def main_loop():
    logging.info("Iniciando monitor de preços. Intervalo: %s segundos", POLL_INTERVAL)
    while True:
        try:
            alerts = check_all()
            logging.info("Check concluído. Alerts: %d", len(alerts))
        except Exception as e:
            logging.exception("Erro no check_all: %s", e)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main_loop()
