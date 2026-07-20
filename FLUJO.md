# Flujo del bot

## Disparador (Cloudflare Worker — cada 15 minutos exactos)

```
Cloudflare Worker (flight-trigger)
│
└─ Llama a GitHub API → dispara check_flights.yml al instante
```

GitHub no respeta el cron propio con precisión. Cloudflare sí es puntual y le ordena a GitHub correr la búsqueda cada 15 minutos exactos.

## Comandos (commands.yml — cada 5 minutos)

```
GitHub Actions arranca runner (~1 min overhead)
│
└─ Long polling durante 4 minutos
      │
      ├─ Usuario escribe /info → responde en segundos
      ├─ Usuario escribe /mes febrero → guarda preferencia, confirma
      ├─ Usuario escribe /precio Alemania 400 → actualiza umbral, confirma
      └─ (sin mensajes: espera hasta que llega uno o se acaba el tiempo)
```

Tiempo de respuesta real: 1–3 minutos (depende de cuándo arrancó el runner).

## Búsqueda de vuelos (check_flights.yml — disparado por Cloudflare)

```
GitHub Actions
│
├─ 1. Lee comandos pendientes de Telegram (fallback, por si commands.yml los perdió)
│
├─ 2. Lee preferencias del usuario (mes seleccionado, umbrales personalizados)
│     → desde data/user_prefs.json (compartido entre corridas via cache)
│
├─ 3. Busca vuelos solo ida en Google Flights
│     → 18 destinos × 5 días (rotación) = 90 búsquedas por corrida
│     → En ~1.5 horas cubre todos los días del mes
│
├─ 4. Guarda precios en historial (data/price_history.json)
│
├─ 5. Detecta ofertas
│     → Precio ≤ umbral de la región (techo duro: Europa $480, Oceanía $600)
│     → Si hay historial suficiente (10+ datos), agrega info del % de descuento
│     → Solo el umbral fijo determina si se notifica o no
│
├─ 6. Filtra el vuelo más barato por destino
│
├─ 7. Filtra ofertas ya notificadas (data/notified_deals.json)
│
└─ 8. Envía ofertas nuevas a Telegram con precio, fecha y link a Google Flights
```

---

*FlightTrackerBot_V1_9*
