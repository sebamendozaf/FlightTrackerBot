import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET", "")
ORIGIN_AIRPORT = os.getenv("ORIGIN_AIRPORT", "SCL")

DEAL_THRESHOLD_PERCENT = 30
MIN_HISTORICAL_DATA_POINTS = 10

# 14 destinos: Alemania + 10 Europa con ofertas frecuentes + Australia/NZ
DESTINATION_GROUPS = {
    "europa": [
        {"city": "Frankfurt", "iata": "FRA"},
        {"city": "Berlín", "iata": "BER"},
        {"city": "Madrid", "iata": "MAD"},
        {"city": "Barcelona", "iata": "BCN"},
        {"city": "Lisboa", "iata": "LIS"},
        {"city": "Roma", "iata": "FCO"},
        {"city": "Milán", "iata": "MXP"},
        {"city": "París", "iata": "CDG"},
        {"city": "Ámsterdam", "iata": "AMS"},
        {"city": "Londres", "iata": "LHR"},
        {"city": "Estambul", "iata": "IST"},
        {"city": "Varsovia", "iata": "WAW"},
    ],
    "oceania": [
        {"city": "Sídney", "iata": "SYD"},
        {"city": "Auckland", "iata": "AKL"},
    ],
}

ACTIVE_GROUPS = os.getenv("ACTIVE_GROUPS", "europa,oceania").split(",")

DESTINATIONS = []
for group in ACTIVE_GROUPS:
    group = group.strip().lower()
    if group in DESTINATION_GROUPS:
        DESTINATIONS.extend(DESTINATION_GROUPS[group])

# Umbral fijo (USD) — bajo este precio = oferta inmediata
FIXED_THRESHOLDS = {
    "europa": 480,
    "oceania": 600,
}


def get_threshold_for_destination(iata_code: str) -> float | None:
    for group_name, dests in DESTINATION_GROUPS.items():
        for dest in dests:
            if dest["iata"] == iata_code:
                return FIXED_THRESHOLDS.get(group_name)
    return None


# Búsqueda solo ida, cada día del mes, con rotación
SEARCH_DAYS_AHEAD_MAX = 180
DAYS_PER_RUN = 5  # cuántos días busca cada corrida (rotación)

PRICE_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "data", "price_history.json")
NOTIFIED_DEALS_FILE = os.path.join(os.path.dirname(__file__), "data", "notified_deals.json")
USER_PREFS_FILE = os.path.join(os.path.dirname(__file__), "data", "user_preferences.json")

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
