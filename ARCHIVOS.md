# Archivos del proyecto

| Archivo | Función | ¿Editable? |
|---------|---------|------------|
| `config.py` | Destinos, umbrales de precio, parámetros de búsqueda | **Sí** |
| `main.py` | Punto de entrada, orquesta la búsqueda de vuelos | No |
| `google_flights.py` | Scraper de Google Flights con Playwright | No |
| `flight_api.py` | Amadeus API (opcional, solo si hay API keys) | No |
| `telegram_bot.py` | Envío de mensajes y formato de notificaciones | No |
| `telegram_commands.py` | Procesamiento de comandos (/info, /precio, /mes) | No |
| `price_tracker.py` | Historial de precios y detección de ofertas | No |
| `.env` | Tokens y variables sensibles (no se sube a git) | **Sí** |
| `check_flights.yml` | Workflow GitHub Actions — búsqueda de vuelos cada 15 min | Solo frecuencia |
| `commands.yml` | Workflow GitHub Actions — comandos Telegram cada 5 min | Solo frecuencia |
| `data/*.json` | Historial, notificaciones, preferencias (autogenerado) | No tocar |
