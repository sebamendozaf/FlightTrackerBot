import json
import math
import calendar
import os
import time
import requests
from datetime import datetime
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
    prefs = _load_prefs()
    return prefs.get("custom_thresholds", {})


def _delete_webhook() -> None:
    """Elimina cualquier webhook activo. Sin esto, getUpdates falla con error 409."""
    if not config.TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/deleteWebhook"
    try:
        resp = requests.post(url, timeout=10)
        data = resp.json()
        print(f"[commands] deleteWebhook: {data.get('description', data.get('result', '?'))}")
    except Exception as e:
        print(f"[commands] Error en deleteWebhook: {e}")


def _get_updates(timeout: int = 5) -> list[dict]:
    if not config.TELEGRAM_BOT_TOKEN:
        return []
    prefs = _load_prefs()
    offset = prefs.get("last_update_id", 0) + 1
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        resp = requests.get(url, params={"offset": offset, "timeout": timeout}, timeout=timeout + 10)
        resp.raise_for_status()
        return resp.json().get("result", [])
    except requests.RequestException as e:
        print(f"[commands] Error getUpdates: {e}")
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
    name = name.strip().lower()

    PAISES = {
        "alemania": ["FRA", "BER", "MUC", "HAM", "DUS", "CGN"],
        "germany": ["FRA", "BER", "MUC", "HAM", "DUS", "CGN"],
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

    if name in PAISES:
        results = []
        for iata in PAISES[name]:
            for group_dests in config.DESTINATION_GROUPS.values():
                for dest in group_dests:
                    if dest["iata"] == iata:
                        results.append(dest)
        return results

    for group_dests in config.DESTINATION_GROUPS.values():
        for dest in group_dests:
            if dest["city"].lower() == name:
                return [dest]

    return []


def _trigger_month_scan(month: int) -> int:
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY", "sebamendozaf/FlightTrackerBot")
    if not token:
        return 0
    year = datetime.now().year
    if month < datetime.now().month:
        year += 1
    _, days_in_month = calendar.monthrange(year, month)
    runs = math.ceil(days_in_month / config.DAYS_PER_RUN)
    url = f"https://api.github.com/repos/{repo}/actions/workflows/check_flights.yml/dispatches"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "FlightTrackerBot",
    }
    for _ in range(runs):
        try:
            requests.post(url, headers=headers, json={"ref": "main"}, timeout=10)
        except Exception:
            pass
    return runs


def _get_effective_threshold(iata_code: str) -> float | None:
    custom = get_custom_thresholds()
    if iata_code in custom:
        return custom[iata_code]
    return config.get_threshold_for_destination(iata_code)


def _handle_info(prefs: dict, args: str = "") -> None:
    custom = prefs.get("custom_thresholds", {})

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

    month = prefs.get("month")
    month_str = _month_name(month) if month else "Todos"

    lines = [
        "<b>ESTADO DEL BOT</b>",
        "",
        f"<b>Mes:</b> {month_str}",
        f"<b>Origen:</b> {config.ORIGIN_AIRPORT}",
        "",
        "<b>Destinos y umbrales (USD):</b>",
    ]

    for group_name, dests in config.DESTINATION_GROUPS.items():
        default_threshold = config.FIXED_THRESHOLDS.get(group_name, 0)
        lines.append("")
        lines.append(f"<b>{group_name.capitalize()}</b> (techo: ${default_threshold:,} USD)")
        for dest in dests:
            if dest["iata"] in custom:
                price_str = f"<b>${custom[dest['iata']]:,.0f}</b> (personalizado)"
            else:
                price_str = f"${default_threshold:,}"
            lines.append(f"  {dest['city']}: {price_str}")

    lines.extend([
        "",
        "<b>Comandos:</b>",
        "info [país] — detalle de un destino",
        "mes febrero — seleccionar mes",
        "precio Alemania 400 — cambiar umbral",
        "ayuda — ver todos los comandos",
    ])

    telegram_bot.send_message("\n".join(lines))


def _handle_precio(args: str, prefs: dict) -> None:
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

    if "custom_thresholds" not in prefs:
        prefs["custom_thresholds"] = {}

    names = []
    for dest in destinations:
        prefs["custom_thresholds"][dest["iata"]] = price
        names.append(f"{dest['city']} ({dest['iata']})")

    telegram_bot.send_message(
        f"Umbral actualizado a <b>USD ${price:,.0f}</b> para:\n"
        + "\n".join(f"  {n}" for n in names)
    )


def _dispatch(text: str, prefs: dict) -> None:
    """Procesa un mensaje de Telegram y ejecuta el comando correspondiente."""
    if not text.startswith("/"):
        text = "/" + text

    print(f"Comando recibido: {text}")
    cmd_lower = text.lower()

    if cmd_lower.startswith("/info"):
        args = text[5:].strip()
        _handle_info(prefs, args)

    elif cmd_lower.startswith("/precio"):
        args = text[7:].strip()
        _handle_precio(args, prefs)

    elif cmd_lower.startswith("/mes"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            telegram_bot.send_message("Uso: <b>mes febrero</b>\nPara quitar: <b>mes todos</b>")
        else:
            arg = parts[1].strip().lower()
            if arg == "todos":
                prefs.pop("month", None)
                telegram_bot.send_message("Listo, buscaré vuelos en todas las fechas.")
            else:
                month = _parse_month(arg)
                if month:
                    prefs["month"] = month
                    runs = _trigger_month_scan(month)
                    extra = f"\nEscaneo iniciado: {runs} búsquedas en cola." if runs else ""
                    telegram_bot.send_message(f"Listo, buscando vuelos para <b>{_month_name(month)}</b>.{extra}")
                else:
                    telegram_bot.send_message(f"No entendí '{arg}'. Usa nombre de mes o número (1-12).")

    elif cmd_lower.startswith("/todos"):
        prefs.pop("month", None)
        telegram_bot.send_message("Listo, buscaré vuelos en todas las fechas.")

    elif cmd_lower.startswith("/ayuda") or cmd_lower.startswith("/help") or cmd_lower.startswith("/start"):
        telegram_bot.send_message(
            "<b>Comandos:</b>\n"
            "\n"
            "info — estado del bot y umbrales\n"
            "info Alemania — detalle de un país\n"
            "\n"
            "mes febrero — seleccionar mes\n"
            "mes todos — buscar en todas las fechas\n"
            "\n"
            "precio Alemania 400 — cambiar umbral\n"
            "\n"
            "ayuda — este mensaje"
        )

    else:
        telegram_bot.send_message(
            f"No entendí '{text}'.\nEscribe <b>ayuda</b> para ver los comandos."
        )


def _process_updates(updates: list[dict]) -> None:
    if not updates:
        return
    prefs = _load_prefs()
    for update in updates:
        prefs["last_update_id"] = update["update_id"]
        message = update.get("message", {})
        text = message.get("text", "").strip()
        try:
            if text:
                _dispatch(text, prefs)
        except Exception as e:
            print(f"[commands] Error en dispatch '{text}': {e}")
        _save_prefs(prefs)


def process_commands() -> None:
    """One-shot: revisa mensajes pendientes y los procesa. Usado por main.py."""
    updates = _get_updates(timeout=5)
    if updates:
        print(f"[commands] Procesando {len(updates)} mensaje(s)...")
    _process_updates(updates)


def run_loop(duration_seconds: int = 270) -> None:
    """Long polling loop: mantiene conexión abierta con Telegram durante duration_seconds.
    Responde comandos en segundos en lugar de esperar el próximo cron."""
    import traceback
    print(f"[commands] Iniciando long polling por {duration_seconds}s...")
    print(f"[commands] Token configurado: {'SI' if config.TELEGRAM_BOT_TOKEN else 'NO'}")
    print(f"[commands] Chat ID configurado: {'SI' if config.TELEGRAM_CHAT_ID else 'NO'}")
    _delete_webhook()

    deadline = time.time() + duration_seconds

    while True:
        remaining = int(deadline - time.time())
        if remaining <= 2:
            break
        poll_timeout = min(25, remaining - 1)
        try:
            updates = _get_updates(timeout=poll_timeout)
            if updates:
                print(f"[commands] {len(updates)} mensaje(s) recibido(s)")
            _process_updates(updates)
        except Exception as e:
            print(f"[commands] ERROR en loop: {e}")
            traceback.print_exc()
            time.sleep(2)

    print("[commands] Long polling finalizado.")
