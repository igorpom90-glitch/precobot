import os
import time
import json
import re
import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

PRICE_MIN = float(os.getenv("PRICE_MIN", "550"))
PRICE_MAX = float(os.getenv("PRICE_MAX", "600"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "900"))  # 15 minutos

URLS = json.loads(os.getenv("PRODUCT_URLS_JSON", "[]"))

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
}

def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    requests.post(url, json=data)

def extract_price(text):
    text = text.replace(".", "").replace(",", ".")
    match = re.findall(r"(\d+\.\d+|\d+)", text)
    if match:
        try:
            return float(match[0])
        except:
            return None
    return None

def fetch_price(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        possible = soup.find_all(text=re.compile(r"R\$"))
        for p in possible:
            price = extract_price(p)
            if price:
                return price

        return None
    except:
        return None

def main():
    send_message("🔄 Monitoramento iniciado!")
    while True:
        for url in URLS:
            store = url.split("/")[2]

            price = fetch_price(url)

            if price is None:
                send_message(f"⚠️ {store}: não achei preço.")
                continue

            if PRICE_MIN <= price <= PRICE_MAX:
                send_message(
                    f"✅ *Oportunidade!* \n\n"
                    f"Loja: {store}\n"
                    f"Preço: R$ {price:.2f}\n"
                    f"{url}"
                )
            else:
                send_message(
                    f"ℹ️ {store}: R$ {price:.2f} (fora da faixa)\n"
                    f"{PRICE_MIN} - {PRICE_MAX}"
                )

        send_message("⏳ Aguardando próxima verificação...")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
