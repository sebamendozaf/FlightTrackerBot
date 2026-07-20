from datetime import date, timedelta
from amadeus import Client, ResponseError
import config


def get_client() -> Client:
    return Client(
        client_id=config.AMADEUS_API_KEY,
        client_secret=config.AMADEUS_API_SECRET,
    )


def search_flights(origin: str, destination: str, departure_date: str, return_date: str) -> list[dict]:
    """Busca vuelos en Amadeus API para una ruta específica."""
    client = get_client()
    try:
        response = client.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            returnDate=return_date,
            adults=1,
            currencyCode="USD",
            max=5,
            nonStop="false",
        )
        return _parse_offers(response.data, origin, destination, departure_date, return_date)
    except ResponseError as e:
        print(f"ERROR Amadeus ({origin}->{destination}): {e}")
        return []


def _parse_offers(data: list, origin: str, destination: str, departure: str, return_date: str) -> list[dict]:
    offers = []
    for item in data:
        try:
            offers.append({
                "origin": origin,
                "destination": destination,
                "departure_date": departure,
                "return_date": return_date,
                "price": float(item["price"]["total"]),
                "currency": item["price"]["currency"],
            })
        except (KeyError, ValueError):
            continue
    return offers


def search_all_destinations() -> list[dict]:
    """Busca en Amadeus (solo si hay API keys configuradas)."""
    if not config.AMADEUS_API_KEY or not config.AMADEUS_API_SECRET:
        print("Amadeus: sin API keys, saltando.")
        return []

    origin = config.ORIGIN_AIRPORT
    today = date.today()
    all_offers = []

    print("Buscando en Amadeus...")
    for dest in config.DESTINATIONS:
        for days_ahead in config.SEARCH_DEPARTURE_OFFSETS:
            for trip_days in config.SEARCH_TRIP_DURATION_DAYS:
                departure = today + timedelta(days=days_ahead)
                return_dt = departure + timedelta(days=trip_days)
                if (return_dt - today).days > config.SEARCH_DAYS_AHEAD_MAX:
                    continue

                offers = search_flights(origin, dest["iata"], departure.isoformat(), return_dt.isoformat())
                for offer in offers:
                    offer["city"] = dest["city"]
                    offer["source"] = "amadeus"
                all_offers.extend(offers)

    print(f"Amadeus: {len(all_offers)} resultados")
    return all_offers
