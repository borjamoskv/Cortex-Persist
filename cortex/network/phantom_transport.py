"""PhantomTransport — Capa de red soberana con JA3/JA4 Spoofing.

Diseñado para eludir inspección profunda de paquetes (DPI) y fingerprints de TLS/HTTP2.
Utiliza curl_cffi como motor de suplantación de identidades de navegadores.
"""

import asyncio
import logging
import random
from typing import Any

import httpx

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    logging.error("🔧 Dependencia 'curl_cffi' no encontrada. Ejecutar: pip install curl_cffi")
    cffi_requests = None

from cortex.concurrency import SovereignGate

logger = logging.getLogger(__name__)
_GATE = SovereignGate.shared()


class PhantomTransport:
    """
    Drop-in replacement (interfaz simplificada) para clientes HTTP que requieren
    suplantación térmica de navegadores reales.
    """

    def __init__(
        self,
        impersonate: str = "chrome120",
        proxy: str | None = None,
        timeout: float = 60.0,
        use_vpn_router: bool = False,
    ):
        self.impersonate = impersonate
        self.proxy = proxy
        self.timeout = timeout
        self._direct_fallback = False
        self._current_endpoint = None  # VPNEndpoint | None

        # VPNRouter auto-assignment: si no hay proxy explícito y se pide router
        if use_vpn_router and not proxy:
            try:
                from cortex.network.vpn_router import VPNRouter
                _router = VPNRouter.shared()
                ep = _router._pool.pick()
                if ep:
                    self.proxy = ep.url
                    self._current_endpoint = ep
                    logger.debug("🛡️ [VPN-ROUTER] Auto-assigned: %s", ep.label or ep.url)
                else:
                    logger.debug("🔗 [VPN-ROUTER] Pool empty — direct connection")
            except Exception as exc:
                logger.debug("VPNRouter unavailable: %s", exc)

        if cffi_requests is None:
            raise RuntimeError("curl_cffi is required for PhantomTransport")

        # Inicializamos la sesión de curl_cffi con la identidad suplantada
        self._session = cffi_requests.AsyncSession(
            impersonate=self.impersonate,
            proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
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
        max_retries: int = 3,
        **kwargs,
    ) -> httpx.Response | Any:
        """
        [ULTRATHINK] Decisión de diseño: Implementar resiliencia multi-capa (Ω₅).
        - Capa 1: Reintentos exponenciales con jitter.
        - Capa 2: Fallback de proxy ante errores térmicos.
        - Capa 3: Inyección de entropía en headers.
        """
        last_err = None
        headers = headers or {}
        
        # Inyección de Entropía Estructural (Anti-Fingerprint)
        if "User-Agent" not in headers:
            headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        for attempt in range(max_retries + 1):
            try:
                async with _GATE.gate(provider="network"): # Throttle preventivo
                    return await self._session.request(
                        method=method,
                        url=url,
                        params=params,
                        json=json,
                        headers=headers,
                        **kwargs,
                    )
            except Exception as e:
                last_err = e
                # EFECTO-2: Soberanía de Red / Fallback Silencioso
                if self.proxy and not self._direct_fallback:
                    logger.warning("⚠️ [NET-FALLBACK] Proxy failure detected: %s. Collapsing to direct connection...", e)
                    self._direct_fallback = True
                    await self._session.close()
                    self._session = cffi_requests.AsyncSession(
                        impersonate=self.impersonate,
                        proxies=None,
                        timeout=self.timeout,
                        verify=True,
                    )
                    continue # Reintentar instantáneo sin fricción de proxy
                
                if attempt < max_retries:
                    # AIROS-Ω: Retroceso estocástico basado en la Proporción Áurea (φ)
                    wait = (1.618 ** attempt) + random.uniform(0.5, 2.0)
                    logger.warning(
                        "🛡️ [STABILIZE] Network anomaly (Attempt %d/%d). Sleeping %.2fs...",
                        attempt + 1, max_retries, wait
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        "🛑 CRITICAL: Network collapse after %d retries [%s %s]",
                        max_retries, method, url
                    )
                    raise last_err from None

    async def close(self):
        """Cierra la sesión de forma limpia."""
        await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
