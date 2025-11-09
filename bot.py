import os
import time
import requests
from bs4 import BeautifulSoup
import json
import logging

# Configuração do log
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Variáveis de ambiente do Railway
KABUM_URL = os.getenv("KABUM_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TARGET_PRICE_LOW = float(os.getenv("TARGET_PRICE_LOW", "0"))
TARGET_PRICE_HIGH = float(os.getenv("TARGET_PRICE_HIGH", "99999"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "900"))  # 900 = 15 minutos

STATE_FILE = "state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_price": None}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)

def send_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass

def get_price_kabum(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        # Novos seletores da Kabum
        price_element = soup.select_one("h4.final-price") or soup.select_one("span.price__current")
        if not price_element:
            logging.info("Kabum: não encontrou seletor de preço.")
            return None

        price = price_element.get_text().strip()
        price = price.replace("R$", "").replace(".", "").replace(",", ".")
        return float(price)

    except Exception as e:
        logging.warning(f"Erro ao verificar Kabum: {e}")
        return None

def main():
    state = load_state()
    logging.info("Iniciando monitoramento...")

    while True:
        price = get_price_kabum(KABUM_URL)

        if price:
            logging.info(f"Kabum: preço atual R$ {price:.2f}")

            if TARGET_PRICE_LOW <= price <= TARGET_PRICE_HIGH:
                msg = (
                    f"🎯 *ALERTA DE PREÇO*\n\n"
                    f"LojA: Kabum\n"
                    f"💲 Preço: R$ {price:.2f}\n"
                    f"🔗 {KABUM_URL}"
                )
                send_message(msg)

            state["last_price"] = price
            save_state(state)

        else:
            logging.info("Kabum: não foi possível achar preço.")

        logging.info(f"Aguardando {CHECK_INTERVAL} segundos...\n")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
