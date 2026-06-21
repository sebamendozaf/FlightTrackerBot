import json
import os
import requests
import config
import telegram_bot


def _load_prefs() -> dict:
    if not os.path.exists(config.USER_PREFS_FILE):
        return {}
    with open(config.USER_PREFS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_prefs(prefs: dict) -> None:
    os.makedirs(os.path.dirname(config.USER_PREFS_FILE), exist_ok=True)
    with open(config.USER_PREFS_FILE, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2, ensure_ascii=False)


def get_selected_month() -> int | None:
    prefs = _load_prefs()
    return prefs.get("month")


def get_custom_thresholds() -> dict:
    """Retorna los umbrales personalizados por destino (código IATA → precio).
    Ejemplo: {"FRA": 500, "BER": 500}"""
    prefs = _load_prefs()
    return prefs.get("custom_thresholds", {})


def _get_updates() -> list[dict]:
    if not config.TELEGRAM_BOT_TOKEN:
        return []
    prefs = _load_prefs()
    offset = prefs.get("last_update_id", 0) + 1
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        resp = requests.get(url, params={"offset": offset, "timeout": 5}, timeout=15)
        resp.raise_for_status()
        return resp.json().get("result", [])
    except requests.RequestException as e:
        print(f"Error obteniendo mensajes de Telegram: {e}")
        return []


def _parse_month(text: str) -> int | None:
    text = text.strip().lower()
    try:
        num = int(text)
        if 1 <= num <= 12:
            return num
    except ValueError:
        pass
    return config.MESES.get(text)


def _month_name(month: int) -> str:
    for name, num in config.MESES.items():
        if num == month:
            return name.capitalize()
    return str(month)


def _find_destination_by_name(name: str) -> list[dict]:
    """Busca destinos que coincidan con el nombre (ciudad o país).
    Ej: 'Alemania' → Frankfurt, Berlín. 'Madrid' → Madrid."""
    name = name.strip().lower()

    # Mapeo de países a sus ciudades/destinos
    PAISES = {
        "alemania": ["FRA", "BER"],
        "germany": ["FRA", "BER"],
        "españa": ["MAD", "BCN"],
        "spain": ["MAD", "BCN"],
        "francia": ["CDG"],
        "france": ["CDG"],
        "italia": ["FCO", "MXP"],
        "italy": ["FCO", "MXP"],
        "inglaterra": ["LHR"],
        "england": ["LHR"],
        "reino unido": ["LHR"],
        "holanda": ["AMS"],
        "paises bajos": ["AMS"],
        "portugal": ["LIS"],
        "australia": ["SYD", "MEL"],
        "nueva zelanda": ["AKL"],
        "new zealand": ["AKL"],
        "japon": ["NRT"],
        "japón": ["NRT"],
        "tailandia": ["BKK"],
        "singapur": ["SIN"],
        "corea": ["ICN"],
        "emiratos": ["DXB"],
        "dubai": ["DXB"],
        "dubái": ["DXB"],
        "estados unidos": ["JFK", "MIA", "LAX"],
        "usa": ["JFK", "MIA", "LAX"],
        "canada": ["YYZ"],
        "canadá": ["YYZ"],
        "mexico": ["MEX"],
        "méxico": ["MEX"],
        "argentina": ["EZE"],
        "brasil": ["GRU", "GIG"],
        "peru": ["LIM"],
        "perú": ["LIM"],
        "colombia": ["BOG"],
    }

    # Primero busca por nombre de país
    if name in PAISES:
        results = []
        for iata in PAISES[name]:
            for group_dests in config.DESTINATION_GROUPS.values():
                for dest in group_dests:
                    if dest["iata"] == iata:
                        results.append(dest)
        return results

    # Luego busca por nombre de ciudad
    for group_dests in config.DESTINATION_GROUPS.values():
        for dest in group_dests:
            if dest["city"].lower() == name:
                return [dest]

    return []


def _get_effective_threshold(iata_code: str) -> float | None:
    """Retorna el umbral efectivo para un destino: personalizado si existe,
    o el de la región por defecto."""
    custom = get_custom_thresholds()
    if iata_code in custom:
        return custom[iata_code]
    return config.get_threshold_for_destination(iata_code)


def _handle_info(prefs: dict, args: str = "") -> None:
    """Comando /info: muestra estado del bot.
    Sin argumentos: lista todos los países con sus umbrales.
    Con argumento: muestra detalle del país indicado."""

    custom = prefs.get("custom_thresholds", {})

    # ---- /info Alemania → detalle de un país ----
    if args:
        destinations = _find_destination_by_name(args)
        if not destinations:
            telegram_bot.send_message(f"No encontré '{args}'. Prueba: Alemania, Australia, España, etc.")
            return

        lines = [f"<b>Info: {args.capitalize()}</b>", ""]
        for dest in destinations:
            threshold = custom.get(dest["iata"]) or config.get_threshold_for_destination(dest["iata"]) or "?"
            is_custom = dest["iata"] in custom
            label = " (personalizado)" if is_custom else ""
            lines.append(f"  {dest['city']} ({dest['iata']}): <b>${threshold:,.0f}</b>{label}")
        telegram_bot.send_message("\n".join(lines))
        return

    # ---- /info sin argumentos → resumen completo ----
    month = prefs.get("month")
    month_str = _month_name(month) if month else "Todos"

    lines = [
        f"<b>ESTADO DEL BOT</b>",
        f"",
        f"<b>Mes:</b> {month_str}",
        f"<b>Origen:</b> {config.ORIGIN_AIRPORT}",
        f"",
        f"<b>Destinos y umbrales (USD):</b>",
    ]

    for group_name, dests in config.DESTINATION_GROUPS.items():
        default_threshold = config.FIXED_THRESHOLDS.get(group_name, 0)
        lines.append(f"")
        lines.append(f"<b>{group_name.capitalize()}</b> (base: ${default_threshold:,})")
        for dest in dests:
            if dest["iata"] in custom:
                price_str = f"<b>${custom[dest['iata']]:,.0f}</b> ✏️"
            else:
                price_str = f"${default_threshold:,}"
            lines.append(f"  {dest['city']}: {price_str}")

    lines.extend([
        f"",
        f"✏️ = precio personalizado (via /precio)",
    ])

    telegram_bot.send_message("\n".join(lines))


def _handle_precio(args: str, prefs: dict) -> None:
    """Comando /precio: establece un umbral personalizado para un destino.
    Formato: /precio Alemania 500"""
    parts = args.rsplit(maxsplit=1)
    if len(parts) < 2:
        telegram_bot.send_message(
            "Uso: <b>/precio Alemania 500</b>\n"
            "Esto pone el umbral en $500 USD para todos los destinos en Alemania.\n"
            "\n"
            "También puedes usar ciudades: /precio Madrid 450"
        )
        return

    dest_name = parts[0].strip()
    try:
        price = float(parts[1].replace(",", "").replace(".", ""))
    except ValueError:
        telegram_bot.send_message(f"'{parts[1]}' no es un precio válido. Ejemplo: /precio Alemania 500")
        return

    destinations = _find_destination_by_name(dest_name)
    if not destinations:
        telegram_bot.send_message(
            f"No encontré el destino '{dest_name}'.\n"
            "Prueba con: Alemania, España, Francia, Australia, etc."
        )
        return

    # Guarda el umbral personalizado para cada destino encontrado
    if "custom_thresholds" not in prefs:
        prefs["custom_thresholds"] = {}

    names = []
    for dest in destinations:
        prefs["custom_thresholds"][dest["iata"]] = price
        names.append(f"{dest['city']} ({dest['iata']})")

    telegram_bot.send_message(
        f"Umbral actualizado a <b>USD ${price:,.0f}</b> para:\n"
        + "\n".join(f"  • {n}" for n in names)
    )


def process_commands() -> None:
    """Revisa los mensajes nuevos del bot y procesa los comandos."""
    updates = _get_updates()
    if not updates:
        return

    prefs = _load_prefs()

    for update in updates:
        prefs["last_update_id"] = update["update_id"]
        message = update.get("message", {})
        text = message.get("text", "").strip()
        if not text:
            continue

        # Normaliza: si escribió sin /, lo trata igual
        if not text.startswith("/"):
            text = "/" + text

        print(f"Comando recibido: {text}")
        cmd_lower = text.lower()

        # ---- /info o /info Alemania ----
        if cmd_lower.startswith("/info"):
            args = text[5:].strip()
            _handle_info(prefs, args)

        # ---- /precio Alemania 500 ----
        elif cmd_lower.startswith("/precio"):
            args = text[7:].strip()
            _handle_precio(args, prefs)

        # ---- /mes agosto ----
        elif cmd_lower.startswith("/mes"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                telegram_bot.send_message("Uso: /mes agosto (o número 1-12)")
                continue
            arg = parts[1].strip().lower()
            if arg == "todos":
                prefs.pop("month", None)
                telegram_bot.send_message("Listo, buscaré vuelos en todas las fechas.")
            else:
                month = _parse_month(arg)
                if month:
                    prefs["month"] = month
                    telegram_bot.send_message(f"Listo, buscando vuelos para <b>{_month_name(month)}</b>...")
                else:
                    telegram_bot.send_message(f"No entendí '{arg}'. Usa nombre de mes o número (1-12).")

        # ---- /ayuda ----
        elif cmd_lower.startswith("/ayuda") or cmd_lower.startswith("/help") or cmd_lower.startswith("/start"):
            telegram_bot.send_message(
                "<b>Comandos disponibles:</b>\n"
                "\n"
                "<b>Mes (cualquiera):</b>\n"
                "/enero /febrero /marzo /abril\n"
                "/mayo /junio /julio /agosto\n"
                "/septiembre /octubre /noviembre /diciembre\n"
                "/todos — Volver a buscar en todas las fechas\n"
                "\n"
                "<b>Precios:</b>\n"
                "/precio Alemania 500 — Umbral de $500\n"
                "/precio Australia 600 — Umbral de $600\n"
                "(funciona con cualquier país o ciudad)\n"
                "\n"
                "<b>Info:</b>\n"
                "/info — Ver mes activo, destinos y precios\n"
                "/info Alemania — Detalle de un país\n"
                "/ayuda — Mostrar este mensaje\n"
                "\n"
                "El bot busca cada 15 minutos automáticamente."
            )

        # ---- Comando directo: /febrero, /agosto, /todos, etc. ----
        else:
            cmd = text[1:].strip().lower()
            month = _parse_month(cmd)
            if month:
                prefs["month"] = month
                telegram_bot.send_message(f"Listo, buscando vuelos para <b>{_month_name(month)}</b>...")
            elif cmd == "todos":
                prefs.pop("month", None)
                telegram_bot.send_message("Listo, buscaré vuelos en todas las fechas.")
            else:
                telegram_bot.send_message(
                    f"No entendí '{text}'. Escribe /ayuda para ver los comandos."
                )

    _save_prefs(prefs)
