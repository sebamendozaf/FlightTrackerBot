import json
import os
from datetime import datetime
import config


def _load_json(filepath: str) -> dict:
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(filepath: str, data: dict) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _route_key(origin: str, destination: str) -> str:
    return f"{origin}-{destination}"


def record_prices(offers: list[dict]) -> None:
    """Guarda los precios en data/price_history.json agrupados por ruta."""
    history = _load_json(config.PRICE_HISTORY_FILE)
    now = datetime.now().isoformat()

    for offer in offers:
        key = _route_key(offer["origin"], offer["destination"])
        if key not in history:
            history[key] = []
        history[key].append({
            "price": offer["price"],
            "currency": offer["currency"],
            "date": now,
            "departure_date": offer["departure_date"],
        })

    _save_json(config.PRICE_HISTORY_FILE, history)


def get_average_price(origin: str, destination: str) -> tuple[float | None, int]:
    """Retorna (promedio, cantidad_datos) para una ruta."""
    history = _load_json(config.PRICE_HISTORY_FILE)
    entries = history.get(_route_key(origin, destination), [])
    if not entries:
        return None, 0
    prices = [e["price"] for e in entries]
    return sum(prices) / len(prices), len(prices)


def find_deals(offers: list[dict]) -> list[dict]:
    """Detecta ofertas por umbral fijo (inmediato) o por historial (30% bajo promedio)."""
    import telegram_commands
    custom = telegram_commands.get_custom_thresholds()
    deals = []

    for offer in offers:
        deal = None

        # Umbral fijo: personalizado o por región
        threshold = custom.get(offer["destination"]) or config.get_threshold_for_destination(offer["destination"])
        if threshold and offer["price"] <= threshold:
            deal = {**offer, "deal_type": "umbral_fijo", "threshold": threshold}

        # Comparación histórica
        avg, count = get_average_price(offer["origin"], offer["destination"])
        if avg and count >= config.MIN_HISTORICAL_DATA_POINTS:
            discount = ((avg - offer["price"]) / avg) * 100
            if discount >= config.DEAL_THRESHOLD_PERCENT:
                deal = deal or {**offer}
                deal.update({"deal_type": "historico", "avg_price": avg,
                             "discount_percent": discount, "historical_count": count})

        if deal:
            deals.append(deal)

    return deals


def is_already_notified(deal: dict) -> bool:
    notified = _load_json(config.NOTIFIED_DEALS_FILE)
    key = f"{deal['origin']}-{deal['destination']}-{deal['departure_date']}-{deal['price']}"
    return key in notified


def mark_as_notified(deal: dict) -> None:
    notified = _load_json(config.NOTIFIED_DEALS_FILE)
    key = f"{deal['origin']}-{deal['destination']}-{deal['departure_date']}-{deal['price']}"
    notified[key] = datetime.now().isoformat()
    _save_json(config.NOTIFIED_DEALS_FILE, notified)
