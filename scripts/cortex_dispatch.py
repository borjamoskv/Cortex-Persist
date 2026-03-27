import argparse
import asyncio
import logging
import socket
from contextlib import closing

from playwright.async_api import async_playwright

from cortex.cli.common import get_engine
from cortex.extensions.agents import keter

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger("cortex-dispatch")


def is_port_open(host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex((host, port)) == 0


async def get_whatsapp_page(browser):
    for context in browser.contexts:
        for page in context.pages:
            if "web.whatsapp.com" in page.url:
                return page
    return None


async def select_chat(page, chat_name):
    logger.info("Seleccionando chat: %s", chat_name)
    search_box = await page.wait_for_selector(
        'div[contenteditable="true"][data-tab="3"]', timeout=10000
    )
    await search_box.click()
    await search_box.fill("")
    await search_box.type(chat_name)
    await asyncio.sleep(2)

    contact_selector = f'span[title="{chat_name}"]'
    await page.click(contact_selector)
    await asyncio.sleep(2)


async def get_last_message(page) -> str:
    messages = await page.query_selector_all('div[role="row"]')
    if not messages:
        return ""

    last_msg = messages[-1]
    text_content = await last_msg.inner_text()
    return text_content.strip()


async def send_reply(page, text: str):
    logger.info("Enviando respuesta a WhatsApp...")
    msg_box = await page.wait_for_selector(
        'div[contenteditable="true"][data-tab="10"]', timeout=5000
    )
    await msg_box.click()

    # Fragmentar mensajes muy largos por los límites de WhatsApp (~65K caracteres, pero Playwright rinde mejor con menos)
    max_chunk = 4000
    chunks = [text[i : i + max_chunk] for i in range(0, len(text), max_chunk)]

    for chunk in chunks:
        await page.evaluate(
            """([element, txt]) => {
            const dataTransfer = new DataTransfer();
            dataTransfer.setData('text/plain', txt);
            element.dispatchEvent(new ClipboardEvent('paste', {
                clipboardData: dataTransfer,
                bubbles: true,
                cancelable: true
            }));
        }""",
            [msg_box, chunk],
        )
        await asyncio.sleep(0.5)
        await page.keyboard.press("Enter")
        await asyncio.sleep(0.5)


async def process_task(task: str, project: str) -> str:
    """Executes the prompt securely via CORTEX bus (`keter.ignite`)."""
    engine = get_engine()

    logger.info("💾 Registrando Inbound en el Sovereign Ledger...")
    await engine.store(
        project=project,
        fact=f"DISPATCH INBOUND: {task}",
        fact_type="command",
        confidence="verified",
    )

    out_msg = ""
    try:
        logger.info("⚡ Ejecutando task localmente vía CORTEX KETER...")
        output = await keter.ignite(task, project=project)
        out_msg = f"[CORTEX] Tarea Ejecutada:\n{output}"

        logger.info("💾 Registrando Outbound (SUCCESS) en el Sovereign Ledger...")
        await engine.store(
            project=project,
            fact=f"DISPATCH OUTBOUND (SUCCESS): {output[:500]}...",
            fact_type="task_result",
            confidence="verified",
        )
    except Exception as e:
        logger.error("❌ Error en KETER: %s", e)
        out_msg = f"[CORTEX] Error Interno:\n{e}"
        await engine.store(
            project=project,
            fact=f"DISPATCH OUTBOUND (ERROR): {e}",
            fact_type="task_error",
            confidence="verified",
        )

    return out_msg


async def handle_whatsapp(args):
    cdp_url = f"http://127.0.0.1:{args.port}"
    if not is_port_open("127.0.0.1", args.port):
        logger.error("Chrome no está disponible en el puerto CDP %s.", args.port)
        logger.error("Inicia Chrome con: --remote-debugging-port=%s", args.port)
        return

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            logger.error("Error CDP: %s", e)
            return

        page = await get_whatsapp_page(browser)
        if not page:
            logger.error("No se encontró la pestaña de WhatsApp Web.")
            await browser.close()
            return

        logger.info("✅ Conectado a WhatsApp Web.")
        await select_chat(page, args.chat)

        logger.info("📡 Observer (Polling) iniciado en chat '%s'...", args.chat)
        last_processed_msg = await get_last_message(page)

        while True:
            await asyncio.sleep(args.interval)

            try:
                current_msg = await get_last_message(page)
            except Exception as e:
                logger.warning("Error consultando el DOM de WhatsApp: %s", e)
                continue

            if current_msg and current_msg != last_processed_msg:
                # Ignorar si es nuestro propio eco o la validación inicial
                if "[CORTEX]" in current_msg:
                    last_processed_msg = current_msg
                    continue

                logger.info("📥 Nuevo Inbound Detectado: %s...", current_msg[:80])

                # Feedback de procesamiento
                await send_reply(page, "[CORTEX] ⏳ Recibido. Resolviendo localmente...")
                last_processed_msg = await get_last_message(page)  # Update before processing

                # Task Execution
                result = await process_task(current_msg, args.project)

                # Enviar Outbound
                await send_reply(page, result)

                # Refrescar estado actual para no re-procesar nuestra respuesta
                last_processed_msg = await get_last_message(page)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="[CORTEX DISPATCH] Sovereign Daemon for WhatsApp Web"
    )
    parser.add_argument(
        "--chat",
        type=str,
        required=True,
        help="Nombre del chat a monitorear (Ej: 'CORTEX DISPATCH')",
    )
    parser.add_argument("--port", type=int, default=9222, help="Puerto de Chrome CDP")
    parser.add_argument(
        "--interval", type=float, default=2.0, help="Intervalo de polling en segundos"
    )
    parser.add_argument(
        "--project",
        type=str,
        default="cortex-dispatch",
        help="Proyecto CORTEX para la inyección registral",
    )

    args = parser.parse_args()

    try:
        asyncio.run(handle_whatsapp(args))
    except KeyboardInterrupt:
        logger.info("\n⏹ Daemon detenido por el Operador.")
