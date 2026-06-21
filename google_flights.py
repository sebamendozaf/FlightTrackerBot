import re
import time
import json
import os
import calendar
from datetime import date, timedelta
from playwright.sync_api import sync_playwright, Browser, Page
import config


def _create_browser(playwright) -> Browser:
    return playwright.chromium.launch(headless=True)


def _create_page(browser: Browser) -> Page:
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 720},
        locale="en-US",
    )
    return context.new_page()


def _extract_prices(page: Page) -> list[float]:
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass
    time.sleep(5)

    prices = []
    seen = set()
    try:
        for el in page.query_selector_all("span"):
            try:
                txt = el.inner_text()
                if "$" in txt and len(txt) < 20:
                    for match in re.findall(r"\$([\d,]+)", txt):
                        price = float(match.replace(",", ""))
                        if 50 < price < 15000 and price not in seen:
                            seen.add(price)
                            prices.append(price)
            except Exception:
                continue
    except Exception:
        pass
    return sorted(prices)


def _search_one_way(page: Page, origin: str, dest_code: str, dest_city: str,
                     departure_date: str) -> list[dict]:
    """Busca vuelos solo ida en Google Flights."""
    query = f"One way flights from {origin} to {dest_code} on {departure_date}"
    url = f"https://www.google.com/travel/flights?q={query.replace(' ', '+')}&curr=USD&hl=en"

    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        prices = _extract_prices(page)

        results = []
        for price in prices[:3]:
            results.append({
                "origin": origin,
                "destination": dest_code,
                "city": dest_city,
                "departure_date": departure_date,
                "price": price,
                "currency": "USD",
                "source": "google_flights",
            })
        return results
    except Exception as e:
        print(f"  Error {origin}->{dest_code}: {e}")
        return []


def _get_rotation_index() -> int:
    """Lee y avanza el índice de rotación para saber qué bloque de días buscar."""
    rotation_file = os.path.join(os.path.dirname(__file__), "data", "rotation.json")
    idx = 0
    if os.path.exists(rotation_file):
        with open(rotation_file, "r") as f:
            idx = json.load(f).get("index", 0)

    next_idx = idx + 1
    os.makedirs(os.path.dirname(rotation_file), exist_ok=True)
    with open(rotation_file, "w") as f:
        json.dump({"index": next_idx}, f)

    return idx


def _generate_dates(selected_month: int | None) -> list[date]:
    """Genera TODOS los días del mes seleccionado (o de los próximos 2 meses)."""
    today = date.today()
    all_dates = []

    if selected_month:
        year = today.year
        if selected_month < today.month or (selected_month == today.month and today.day > 25):
            year += 1
        last_day = calendar.monthrange(year, selected_month)[1]
        for day in range(1, last_day + 1):
            d = date(year, selected_month, day)
            if d > today:
                all_dates.append(d)
    else:
        # Sin mes seleccionado: próximos 60 días
        for i in range(1, 61):
            d = today + timedelta(days=i)
            if (d - today).days <= config.SEARCH_DAYS_AHEAD_MAX:
                all_dates.append(d)

    return all_dates


def search_all_destinations(selected_month: int | None = None) -> list[dict]:
    """Busca vuelos solo ida a todos los destinos.
    Usa rotación: cada corrida busca un bloque diferente de días.
    En varias corridas cubre todos los días del mes."""

    origin = config.ORIGIN_AIRPORT
    all_dates = _generate_dates(selected_month)

    # Rotación: divide los días en bloques y busca uno diferente cada corrida
    rotation = _get_rotation_index()
    total_blocks = max(1, len(all_dates) // config.DAYS_PER_RUN)
    block_idx = rotation % total_blocks
    start = block_idx * config.DAYS_PER_RUN
    dates_this_run = all_dates[start:start + config.DAYS_PER_RUN]

    if not dates_this_run:
        dates_this_run = all_dates[:config.DAYS_PER_RUN]

    print(f"Google Flights: bloque {block_idx + 1}/{total_blocks} "
          f"({dates_this_run[0]} a {dates_this_run[-1]}), "
          f"{len(config.DESTINATIONS)} destinos")

    all_offers = []
    try:
        with sync_playwright() as p:
            browser = _create_browser(p)
            page = _create_page(browser)

            for dest in config.DESTINATIONS:
                for dep_date in dates_this_run:
                    dep_str = dep_date.isoformat()
                    print(f"  {origin} -> {dest['city']} ({dep_str})...")
                    offers = _search_one_way(page, origin, dest["iata"], dest["city"], dep_str)
                    all_offers.extend(offers)
                    time.sleep(2)

            browser.close()
    except Exception as e:
        print(f"Error en Google Flights: {e}")

    print(f"Google Flights: {len(all_offers)} resultados")
    return all_offers
