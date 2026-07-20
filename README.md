# Flight Tracker Bot

Tracks one-way flight prices from Santiago (SCL) to Europe, Australia and New Zealand. Scrapes Google Flights every 15 minutes and sends a Telegram alert when a price drops below your set limit.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.40+-2EAD33?logo=playwright&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot_API-26A5E4?logo=telegram&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-free-2088FF?logo=githubactions&logoColor=white)

## How it works

**`check_flights.yml` — every 15 minutes**
Runs `main.py` which:

1. **Handles Telegram commands** — `commands.yml` runs separately every 5 min via long polling. Response time is 1–3 minutes depending on when the runner starts.

2. **Scrapes Google Flights** — launches a headless Chromium browser with [Playwright](https://playwright.dev/python/) for each destination and date. Each run covers 5 days, cycling through the full month in ~1.5 hours.

3. **Queries Amadeus API** (optional) — if API keys are set, also pulls data from the [Amadeus Flight Offers Search API](https://developers.amadeus.com/) as a secondary source.

4. **Logs price history** — every price found is stored in `data/price_history.json` grouped by route.

5. **Detects deals** — a price is a deal only if it's below the fixed threshold for its region. If there are 10+ data points for a route, the discount percentage is shown in the notification.

6. **Sends Telegram alerts** — HTML-formatted messages with price, date, and a direct Google Flights link.

## Destinations

- **Europe:** Frankfurt (FRA), Berlin (BER), Munich (MUC), Hamburg (HAM), Düsseldorf (DUS), Cologne (CGN), Madrid, Barcelona, Lisbon, Rome, Milan, Paris, Amsterdam, London, Istanbul, Warsaw
- **Oceania:** Sydney (SYD), Auckland (AKL)

## Telegram commands

```
info              → bot status and all thresholds
info Alemania     → detail for a specific country

mes febrero       → search February only
mes todos         → search all dates

precio Alemania 400  → change threshold for Germany
precio Madrid 350    → change threshold for a specific city

ayuda             → list commands
```

## Tech stack

| Technology | Purpose |
|---|---|
| **Python 3.12** | main language |
| **Playwright** | headless scraping |
| **Google Flights** | price source |
| **Telegram Bot API** | commands and alerts |
| **GitHub Actions** | scheduling (free for public repos) |
| **Amadeus API** | secondary price source (optional) |
