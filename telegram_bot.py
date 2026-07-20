import requests
import config


def send_message(text: str) -> bool:
    """Envía un mensaje a Telegram via Bot API."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("ERROR: tokens de Telegram no configurados")
        return False

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        print("Mensaje enviado a Telegram OK")
        return True
    except requests.RequestException as e:
        print(f"ERROR Telegram: {e}")
        return False


def format_deal_message(deal: dict) -> str:
    """Formatea una oferta como mensaje de Telegram con link a Google Flights."""
    origin = deal.get("origin", "???")
    destination = deal.get("destination", "???")
    city = deal.get("city", destination)
    price = deal.get("price", 0)
    currency = deal.get("currency", "USD")
    departure = deal.get("departure_date", "???")
    return_date = deal.get("return_date", "???")
    avg_price = deal.get("avg_price")
    discount = deal.get("discount_percent")
    deal_type = deal.get("deal_type", "")
    threshold = deal.get("threshold")

    lines = [
        f"<b>OFERTA DE VUELO</b>",
        f"",
        f"{origin} → {city} ({destination})",
        f"<b>Precio: {currency} {price:,.0f}</b>",
    ]

    if avg_price and discount:
        lines.append(f"Promedio histórico: {currency} {avg_price:,.0f}")
        lines.append(f"Descuento: {discount:.0f}%")
    elif deal_type == "umbral_fijo" and threshold:
        lines.append(f"Bajo umbral de {currency} {threshold:,.0f} para esta región")

    lines.extend([f"", f"Fecha: {departure}"])
    if return_date and return_date != "???":
        lines.append(f"Vuelta: {return_date}")

    query = f"One way flights from {origin} to {destination} on {departure}"
    gf_url = f"https://www.google.com/travel/flights?q={query.replace(' ', '+')}&curr=USD&hl=es"
    lines.extend([f"", f"<a href='{gf_url}'>Ver en Google Flights</a>"])

    return "\n".join(lines)


def notify_deal(deal: dict) -> bool:
    return send_message(format_deal_message(deal))
