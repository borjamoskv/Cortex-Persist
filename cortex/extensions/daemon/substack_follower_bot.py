import asyncio
import logging
import random

from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("CDP-Automata")


async def run_automata():
    """
    Se conecta al puerto CDP 9222 del Chrome del usuario.
    Audita los seguidores en la página actual y hace "Follow".
    """
    try:
        async with async_playwright() as p:
            # Conectar a la sesión del usuario (Donde ya está logueado en Substack)
            logger.info("Intentando conectar al navegador local (CDP puerto 9222)...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")

            # Obtener el contexto y la pestaña activa
            contexts = browser.contexts
            if not contexts:
                logger.error(
                    "No se encontraron contextos de navegador. Abre Chrome con el flag --remote-debugging-port=9222"
                )
                return

            context = contexts[0]
            pages = context.pages

            # Buscamos la pestaña que tenga "substack.com/profile/subscribers" abierta, o usamos la primera activa
            target_page = None
            for page in pages:
                if "substack.com" in page.url:
                    target_page = page
                    break

            if not target_page:
                target_page = pages[0]
                logger.warning(
                    f"No se encontró una URL explícita de Substack. Operando sobre la pestaña activa: {target_page.url}"
                )

            logger.info(f"Auditoría activa en la URL: {target_page.url}")

            # Validar que estamos en la lista de suscriptores/oyentes
            logger.info("Escaneando el DOM en busca de oyentes...")

            # Substack cambia las clases, pero los botones de seguir suelen tener el texto "Follow" o una clase específica.
            # Localizamos todos los botones que contengan el texto "Follow" o "Seguir".
            follow_buttons = await target_page.locator("button:has-text('Follow')").all()
            seguir_buttons = await target_page.locator("button:has-text('Seguir')").all()

            buttons_to_click = follow_buttons + seguir_buttons

            if not buttons_to_click:
                logger.warning("No se encontraron botones de Follow sin pulsar en la vista actual.")
                # Opcional: Hacer scroll para cargar más
                await target_page.mouse.wheel(0, 1000)
                await asyncio.sleep(2)
            else:
                logger.info(f"[C5-REAL] Nodos sin seguir detectados: {len(buttons_to_click)}")

                for i, button in enumerate(buttons_to_click):
                    try:
                        # Comprobar si el botón sigue visible y habilitado
                        if await button.is_visible() and await button.is_enabled():
                            # El click en cascada. AX-042 (Eficiencia).
                            await button.click()
                            logger.info(f" -> Nodo {i + 1} sincronizado (Followed).")

                            # Pausa estocástica (1 a 3 segundos) para engañar a los sistemas antibot de Substack
                            await asyncio.sleep(random.uniform(1.2, 3.1))
                        else:
                            logger.info(
                                f" -> Nodo {i + 1} ignorado (Botón oculto o deshabilitado)."
                            )
                    except Exception as e:
                        logger.error(f"Fricción al sincronizar nodo {i + 1}: {e}")

            logger.info("Auditoría de pantalla completada.")
            # Desconectarse limpiamente
            await browser.close()

    except Exception as e:
        logger.error(f"Fallo crítico en el Automata CDP: {e}")
        logger.info("¿Has iniciado Google Chrome con el puerto abierto en la terminal?")


if __name__ == "__main__":
    asyncio.run(run_automata())
