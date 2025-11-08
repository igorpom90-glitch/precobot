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

# Lista de URLs vem da variável de ambiente PRODUCT_URLS_JSON (uma única linha JSON)
URLS = json.loads(os.environ.get("PRODUCT_URLS_JSON", "[]"))

# User-Agent alterado: iPhone Safari (pode ajudar em alguns bloqueios simples)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1"
    )
}

# Se você quiser testar proxies, descomente e preencha abaixo (opcional):
# PROXIES = {
#     "http": "http://user:pass@IP_DO_PROXY:PORT",
#     "https": "http://user:pass@IP_DO_PROXY:PORT"
# }
PROXIES = None  # deixar None se não for usar proxy


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
    # procura padrões como R$ 1.234,56 ou 1234,56
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
    # fallback: busca número com vírgula
    m = re.search(r"([0-9]{2,}\,[0-9]{2})", text)
    if m:
        try:
            return float(m.group(1).replace('.', '').replace(',', '.'))
        except:
            pass
    return None


def fetch_price(url: str) -> Optional[float]:
    try:
        # usa proxy se fornecido
        if PROXIES:
            r = requests.get(url, headers=HEADERS, timeout=20, proxies=PROXIES)
        else:
            r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        html = r.text

        # tentativa genérica via regex no HTML bruto
        price = extract_price_from_text(html)
        if price:
            return price

        # tentativa com selectores comuns via BeautifulSoup
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
