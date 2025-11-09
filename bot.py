import requests
from bs4 import BeautifulSoup
import time
import os

# ======================= CONFIGURAÇÕES DO BOT =======================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Intervalo entre verificações (15 minutos)
CHECK_INTERVAL = 15 * 60  # 15 minutos em segundos

# Faixa de preço desejada
MIN_PRICE = 550.00
MAX_PRICE = 600.00

# Lojas para monitorar
URLS = [
    {
        "store": "KaBuM!",
        "url": "https://www.kabum.com.br/produto/100672/placa-mae-asrock-b450m-steel-legend-amd-am4-matx-ddr4-preto-b450m-steel-legend"
    },
    {
        "store": "Amazon BR",
        "url": "https://www.amazon.com.br/s?k=asrock+b450m+steel+legend"
    },
    {
        "store": "Mercado Livre",
        "url": "https://lista.mercadolivre.com.br/asrock-b450m-steel-legend"
    },
    {
        "store": "TechDreamStore",
        "url": "https://www.techdreamstore.com.br/placa-mae-asrock-b450m-steel-legend-am4-matx-ddr4-90-mxb9y0-a0uayz"
    }
]


# ======================= FUNÇÕES DO BOT =======================

def send_telegram_message(text):
    """Envia mensagem para o Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=payload)


def get_price(store, url):
    """Obtém o preço de uma página dependendo da loja."""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    html = requests.get(url, headers=headers, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    price = None

    if store == "KaBuM!":
        price_tag = soup.select_one(".finalPrice")
        if price_tag:
            price = price_tag.text.strip()

    elif store == "Amazon BR":
        price_tag = soup.select_one(".a-price-whole")
        if price_tag:
            price = price_tag.text.strip() + ",00"

    elif store == "Mercado Livre":
        price_tag = soup.select_one(".ui-search-price__second-line .price-tag-fraction")
        if price_tag:
            price = price_tag.text.strip() + ",00"

    elif store == "TechDreamStore":
        price_tag = soup.select_one(".sale-price")
        if price_tag:
            price = price_tag.text.strip()

    if price:
        price = (
            price.replace("R$", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
        return float(price)

    return None


# ======================= LOOP PRINCIPAL =======================

send_telegram_message("🔍 Monitor de preços iniciado com sucesso!")

while True:
    for item in URLS:
        store = item["store"]
        url = item["url"]

        try:
            price = get_price(store, url)

            if price is not None:
                if MIN_PRICE <= price <= MAX_PRICE:
                    send_telegram_message(
                        f"🔥 *ALERTA DE PREÇO*\n\n"
                        f"Lojá: {store}\n"
                        f"💰 Preço: R$ {price:.2f}\n"
                        f"🔗 {url}"
                    )
                else:
                    print(f"{store}: preço fora da faixa → R$ {price:.2f}")

            else:
                print(f"{store}: não foi possível achar preço.")

        except:
            print(f"Erro ao verificar {store}")

    print("Aguardando próxima verificação...\n")
    time.sleep(CHECK_INTERVAL)
