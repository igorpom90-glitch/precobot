def monitor():
    state = load_state()
    logging.info("Loop de monitoramento iniciado.")

    # ---------- Primeira atualização imediata ----------
    logging.info("Primeira atualização imediata do monitor.")
    atualizar_precos(state)

    # ---------- Loop contínuo ----------
    while True:
        time.sleep(POLL_INTERVAL)
        atualizar_precos(state)


# ---------- Função separada para atualizar preços ----------
def atualizar_precos(state):
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
