# Flujo del bot

```
GitHub Actions (cada 15 min)
│
├─ 1. Lee comandos de Telegram (/febrero, /precio, /info)
│
├─ 2. Busca vuelos solo ida en Google Flights
│     → 14 destinos × 5 días (rotación) = 70 búsquedas
│     → Scrapea precios de cada página
│
├─ 3. Guarda precios en historial (data/price_history.json)
│
├─ 4. Detecta ofertas
│     → Método 1: precio < umbral de la región (inmediato)
│     → Método 2: precio 30% bajo promedio histórico (10+ datos)
│
├─ 5. Filtra ofertas ya notificadas (data/notified_deals.json)
│
└─ 6. Envía ofertas nuevas a Telegram con link a Google Flights
```

En ~1.5 horas (6 corridas) cubre todos los días del mes sin saltarse ninguno.
