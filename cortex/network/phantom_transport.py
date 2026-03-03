"""PhantomTransport — Capa de red soberana con JA3/JA4 Spoofing.

Diseñado para eludir inspección profunda de paquetes (DPI) y fingerprints de TLS/HTTP2.
Utiliza curl_cffi como motor de suplantación de identidades de navegadores.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    logging.error("🔧 Dependencia 'curl_cffi' no encontrada. Ejecutar: pip install curl_cffi")
    cffi_requests = None


logger = logging.getLogger(__name__)


class PhantomTransport:
    """
    Drop-in replacement (interfaz simplificada) para clientes HTTP que requieren
    suplantación térmica de navegadores reales.
    """

    def __init__(
        self,
        impersonate: str = "chrome120",
        proxy: str | None = None,
        timeout: float = 30.0,
    ):
        self.impersonate = impersonate
        self.proxy = proxy
        self.timeout = timeout

        if cffi_requests is None:
            raise RuntimeError("curl_cffi is required for PhantomTransport")

        # Inicializamos la sesión de curl_cffi con la identidad suplantada
        self._session = cffi_requests.AsyncSession(
            impersonate=self.impersonate,
            proxies={"http": proxy, "https": proxy} if proxy else None,
            timeout=self.timeout,
            verify=True,
        )
        logger.debug("PhantomTransport inicializado (identidad: %s)", impersonate)

    async def request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> httpx.Response | Any:  # curl_cffi response no es httpx.Response pero tiene interfaz similar
        """Ejecuta una petición suplantando la firma TLS."""
        try:
            response = await self._session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=headers,
                **kwargs,
            )
            return response
        except Exception as e:
            logger.error("Error en PhantomRequest [%s %s]: %s", method, url, e)
            raise

    async def close(self):
        """Cierra la sesión de forma limpia."""
        await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
