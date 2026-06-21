# Flight Tracker Bot

Bot that tracks one-way flight prices from Santiago (SCL) to Europe, Australia and New Zealand. Scrapes Google Flights every 15 minutes and sends Telegram alerts when it finds deals.

## How it works

Every 15 minutes, GitHub Actions triggers `main.py` which:

1. **Checks Telegram for commands** — reads user messages via the [Telegram Bot API](https://core.telegram.org/bots/api) (`getUpdates` endpoint) to process month selection, price thresholds, etc.

2. **Scrapes Google Flights** — launches a headless Chromium browser with [Playwright](https://playwright.dev/python/), navigates to Google Flights for each destination/date combo, and extracts prices from the DOM. Uses a rotation system: each run covers 5 days, cycling through the full month in ~1.5 hours.

3. **Queries Amadeus API** (optional) — if API keys are set, it also pulls data from the [Amadeus Flight Offers Search API](https://developers.amadeus.com/) as a secondary source.

4. **Logs price history** — every price found is stored in `data/price_history.json` grouped by route (e.g. `SCL-FRA`), enabling historical trend analysis.

5. **Detects deals** — compares prices against two criteria:
   - **Fixed threshold**: region-based price ceiling (e.g. Europe < $480 USD)
   - **Historical average**: flags prices 30%+ below the route's rolling average (requires 10+ data points)
   - Thresholds are customizable per country via Telegram (`/precio Germany 500`)

6. **Sends Telegram alerts** — pushes HTML-formatted notifications with price, date, and a direct Google Flights link.

## Tech stack

| Technology | Purpose |
|---|---|
| **Python 3.12** | Core language |
| **Playwright** | Browser automation for Google Flights scraping |
| **Chromium (headless)** | Renders Google Flights pages without a GUI |
| **Google Flights** | Primary flight price source (covers all airlines) |
| **Telegram Bot API** | User commands and push notifications |
| **GitHub Actions** | Scheduled execution every 15 min |
| **Amadeus API** | Secondary price source (optional) |

## Destinations

- **Germany:** Frankfurt (FRA), Berlin (BER)
- **Europe:** Madrid, Barcelona, Lisbon, Rome, Milan, Paris, Amsterdam, London, Istanbul, Warsaw
- **Oceania:** Sydney (SYD), Auckland (AKL)

## Telegram commands

```
/info              → Active destinations with price thresholds
/info Germany      → Detail for a specific country
/precio Germany 500 → Set custom threshold to $500 USD
/february          → Search flights for February
/todos             → Search all dates (default)
/ayuda             → Show available commands
```

## Setup

1. Create a Telegram bot via `@BotFather` → copy the token
2. Send a message to the bot → grab your `chat_id` from `api.telegram.org/bot<TOKEN>/getUpdates`
3. Fork the repo → Settings → Secrets → add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
