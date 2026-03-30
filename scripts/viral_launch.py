"""
scripts/viral_launch.py
───────────────────────
Viral Launch System — Seed Coordination + Timing Engine

Maximiza probabilidad de >1000 reacciones via:
1. Timing óptimo por plataforma (datos empíricos)
2. Coordinación de seed audience via WhatsApp CDP
3. Tracking de resultados

Usage:
    python3 scripts/viral_launch.py schedule --platform linkedin
    python3 scripts/viral_launch.py launch --platform linkedin --url "https://..." --chat "VIRAL SEED"
    python3 scripts/viral_launch.py track --platform linkedin --reactions 1200 --url "https://..."
"""

import argparse
import asyncio
import json
import logging
import socket
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("viral-launch")

CONFIG_PATH = Path(__file__).parent / "viral_seed_config.json"
HISTORY_PATH = Path(__file__).parent / "viral_launch_history.jsonl"

DAY_NAMES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        logger.error("Config not found: %s", CONFIG_PATH)
        raise SystemExit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_tz(config: dict) -> ZoneInfo:
    return ZoneInfo(config.get("timezone", "Europe/Madrid"))


# ──────────────────────────────────────────────
# SCHEDULE — Timing Engine
# ──────────────────────────────────────────────


def next_optimal_window(platform: str, config: dict) -> dict:
    """Calcula la próxima ventana óptima de publicación."""
    pdata = config["platforms"].get(platform)
    if not pdata:
        available = ", ".join(config["platforms"].keys())
        logger.error("Plataforma '%s' no encontrada. Disponibles: %s", platform, available)
        raise SystemExit(1)

    tz = get_tz(config)
    now = datetime.now(tz)

    candidates = []
    # Check next 7 days
    for day_offset in range(7):
        check_date = now + timedelta(days=day_offset)
        weekday = check_date.weekday()  # 0=Monday

        if weekday not in pdata["days"]:
            continue

        for window in pdata["windows"]:
            start_h, start_m = map(int, window[0].split(":"))
            end_h, end_m = map(int, window[1].split(":"))

            window_start = check_date.replace(
                hour=start_h, minute=start_m, second=0, microsecond=0
            )
            window_end = check_date.replace(
                hour=end_h, minute=end_m, second=0, microsecond=0
            )

            # If window is in the future, or we're currently inside it
            if window_end > now:
                is_active = window_start <= now <= window_end
                candidates.append({
                    "date": check_date.strftime("%Y-%m-%d"),
                    "day": DAY_NAMES[weekday],
                    "window": f"{window[0]}-{window[1]}",
                    "start": window_start,
                    "end": window_end,
                    "active_now": is_active,
                    "minutes_until": max(0, int((window_start - now).total_seconds() / 60)),
                })

    candidates.sort(key=lambda c: c["start"])
    return candidates[0] if candidates else {}


def cmd_schedule(args, config: dict):
    """Muestra la próxima ventana óptima de publicación."""
    platform = args.platform.lower()
    pdata = config["platforms"].get(platform)
    emoji = pdata["emoji"] if pdata else "📊"

    result = next_optimal_window(platform, config)
    if not result:
        logger.error("No se encontraron ventanas para '%s'", platform)
        return

    print(f"\n{emoji}  VIRAL LAUNCH — TIMING ENGINE")
    print(f"{'─' * 45}")
    print(f"  Plataforma:   {platform.upper()}")
    print(f"  Próxima ventana: {result['day']} {result['date']}")
    print(f"  Horario:      {result['window']} (UTC+1)")

    if result["active_now"]:
        print(f"  Estado:       🟢 VENTANA ACTIVA AHORA")
        print(f"  Acción:       Publica YA para máximo alcance")
    else:
        hours = result["minutes_until"] // 60
        mins = result["minutes_until"] % 60
        print(f"  Estado:       ⏳ En {hours}h {mins}m")
        print(f"  Acción:       Prepara el contenido")

    # Show all windows for the next 3 days
    print(f"\n  📅 Próximas ventanas ({platform}):")
    all_windows = []
    for day_offset in range(7):
        tz = get_tz(config)
        check_date = datetime.now(tz) + timedelta(days=day_offset)
        weekday = check_date.weekday()
        if weekday in pdata["days"]:
            for w in pdata["windows"]:
                start_h, start_m = map(int, w[0].split(":"))
                window_start = check_date.replace(
                    hour=start_h, minute=start_m, second=0, microsecond=0
                )
                if window_start > datetime.now(tz):
                    all_windows.append(
                        f"     {DAY_NAMES[weekday]} {check_date.strftime('%d/%m')} "
                        f"→ {w[0]}-{w[1]}"
                    )
        if len(all_windows) >= 5:
            break

    for w in all_windows[:5]:
        print(w)
    print()


# ──────────────────────────────────────────────
# LAUNCH — Seed Coordination via WhatsApp CDP
# ──────────────────────────────────────────────


def is_port_open(host: str, port: int) -> bool:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex((host, port)) == 0


async def send_seed_message(chat_name: str, message: str, port: int):
    """Envía mensaje de coordinación al grupo seed via WhatsApp CDP."""
    from playwright.async_api import async_playwright

    cdp_url = f"http://127.0.0.1:{port}"

    if not is_port_open("127.0.0.1", port):
        logger.error(
            "Chrome no disponible en puerto CDP %d. "
            "Inicia con: --remote-debugging-port=%d",
            port, port,
        )
        raise SystemExit(1)

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            logger.error("Error CDP: %s", e)
            raise SystemExit(1)

        # Find WhatsApp tab
        wa_page = None
        for context in browser.contexts:
            for page in context.pages:
                if "web.whatsapp.com" in page.url:
                    wa_page = page
                    break

        if not wa_page:
            logger.error("No se encontró pestaña de WhatsApp Web.")
            raise SystemExit(1)

        logger.info("✅ Conectado a WhatsApp Web")

        # Search and select chat
        logger.info("Buscando chat: %s", chat_name)
        search_box = await wa_page.wait_for_selector(
            'div[contenteditable="true"][data-tab="3"]', timeout=10000
        )
        await search_box.click()
        await search_box.fill("")
        await search_box.type(chat_name)
        await asyncio.sleep(2)

        contact = f'span[title="{chat_name}"]'
        await wa_page.click(contact)
        await asyncio.sleep(2)

        # Send message via clipboard paste (handles long messages)
        msg_box = await wa_page.wait_for_selector(
            'div[contenteditable="true"][data-tab="10"]', timeout=5000
        )
        await msg_box.click()

        await wa_page.evaluate(
            """([element, txt]) => {
            const dt = new DataTransfer();
            dt.setData('text/plain', txt);
            element.dispatchEvent(new ClipboardEvent('paste', {
                clipboardData: dt, bubbles: true, cancelable: true
            }));
        }""",
            [msg_box, message],
        )
        await asyncio.sleep(0.5)
        await wa_page.keyboard.press("Enter")
        await asyncio.sleep(1)

        logger.info("✅ Mensaje seed enviado a '%s'", chat_name)


def build_launch_message(platform: str, url: str, config: dict) -> str:
    """Construye el mensaje de coordinación para el grupo seed."""
    pdata = config["platforms"].get(platform, {})
    emoji = pdata.get("emoji", "🚀")

    return (
        f"🚀 LAUNCH ALERT — {platform.upper()} {emoji}\n"
        f"\n"
        f"Acabo de publicar. Link:\n"
        f"{url}\n"
        f"\n"
        f"Los primeros 30 min son críticos para el algoritmo.\n"
        f"👉 Like + comentario ahora = máximo alcance.\n"
        f"\n"
        f"Gracias, equipo. 🔥"
    )


def cmd_launch(args, config: dict):
    """Envía mensajes de coordinación seed a los chats configurados."""
    platform = args.platform.lower()
    url = args.url

    if not url:
        logger.error("--url es obligatorio para launch")
        raise SystemExit(1)

    # Determine which chats to notify
    chats = [args.chat] if args.chat else config.get("seed_chats", [])
    port = args.port or config.get("cdp_port", 9222)

    if not chats:
        logger.error("No hay chats seed configurados. Usa --chat o configura seed_chats en config.")
        raise SystemExit(1)

    message = build_launch_message(platform, url, config)

    print(f"\n🚀 VIRAL LAUNCH — SEED COORDINATION")
    print(f"{'─' * 45}")
    print(f"  Plataforma: {platform.upper()}")
    print(f"  URL:        {url[:60]}...")
    print(f"  Chats seed: {', '.join(chats)}")
    print(f"  Puerto CDP: {port}")
    print(f"\n  📨 Mensaje:")
    for line in message.split("\n"):
        print(f"     {line}")
    print()

    # Send to each seed chat
    for chat in chats:
        logger.info("Enviando a chat: %s", chat)
        asyncio.run(send_seed_message(chat, message, port))

    # Log to history
    record = {
        "timestamp": datetime.now().isoformat(),
        "platform": platform,
        "url": url,
        "chats": chats,
        "action": "launch",
    }
    with open(HISTORY_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

    print(f"  ✅ Coordinación seed completada. Registrado en {HISTORY_PATH.name}")
    print(f"  ⏱  Ahora: responde TODOS los comentarios durante 60 min.\n")


# ──────────────────────────────────────────────
# TRACK — Resultado post-publicación
# ──────────────────────────────────────────────


def cmd_track(args, config: dict):
    """Registra el resultado de un lanzamiento."""
    platform = args.platform.lower()
    reactions = args.reactions
    url = args.url or "N/A"

    record = {
        "timestamp": datetime.now().isoformat(),
        "platform": platform,
        "url": url,
        "reactions": reactions,
        "action": "track",
        "success": reactions >= 1000,
    }

    with open(HISTORY_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

    pdata = config["platforms"].get(platform, {})
    emoji = pdata.get("emoji", "📊")
    status = "🟢 ÉXITO (>1000)" if reactions >= 1000 else "🟡 POR DEBAJO (<1000)"

    print(f"\n{emoji}  VIRAL LAUNCH — TRACKING")
    print(f"{'─' * 45}")
    print(f"  Plataforma: {platform.upper()}")
    print(f"  Reacciones: {reactions}")
    print(f"  Estado:     {status}")
    print(f"  URL:        {url}")
    print(f"  Registrado: {HISTORY_PATH.name}\n")

    # Show historical stats if available
    if HISTORY_PATH.exists():
        tracks = []
        with open(HISTORY_PATH) as f:
            for line in f:
                line = line.strip()
                if line:
                    entry = json.loads(line)
                    if entry.get("action") == "track":
                        tracks.append(entry)

        if len(tracks) >= 2:
            total = len(tracks)
            wins = sum(1 for t in tracks if t.get("success"))
            avg = sum(t.get("reactions", 0) for t in tracks) / total
            print(f"  📊 Historial: {wins}/{total} éxitos ({wins/total*100:.0f}%)")
            print(f"  📊 Media:     {avg:.0f} reacciones\n")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="[VIRAL LAUNCH] Timing Engine + Seed Coordination"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # schedule
    p_sched = sub.add_parser("schedule", help="Muestra próxima ventana óptima")
    p_sched.add_argument("--platform", required=True, help="linkedin|twitter|instagram|tiktok|substack")

    # launch
    p_launch = sub.add_parser("launch", help="Envía coordinación seed via WhatsApp")
    p_launch.add_argument("--platform", required=True, help="linkedin|twitter|instagram|tiktok|substack")
    p_launch.add_argument("--url", required=True, help="URL del post publicado")
    p_launch.add_argument("--chat", help="Chat de WhatsApp (override config)")
    p_launch.add_argument("--port", type=int, help="Puerto CDP (override config)")

    # track
    p_track = sub.add_parser("track", help="Registra resultado post-publicación")
    p_track.add_argument("--platform", required=True, help="linkedin|twitter|instagram|tiktok|substack")
    p_track.add_argument("--reactions", type=int, required=True, help="Número de reacciones obtenidas")
    p_track.add_argument("--url", help="URL del post")

    args = parser.parse_args()
    config = load_config()

    if args.command == "schedule":
        cmd_schedule(args, config)
    elif args.command == "launch":
        cmd_launch(args, config)
    elif args.command == "track":
        cmd_track(args, config)


if __name__ == "__main__":
    main()
