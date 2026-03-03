"""VPN Autorouter — Sovereign Swarm Transport Layer.

Gestiona un pool dinámico de endpoints VPN/proxy verificados y enruta
automáticamente cada agente del enjambre a través de la ruta de menor
entropía. Auto-heals fallidos, rota identidades, y escala horizontalmente.

Architecture:
    VPNEndpoint  — descriptor de un nodo VPN/proxy
    VPNPool      — pool vivo con health-check continuo
    VPNRouter    — el autorouter que asigna endpoints al enjambre
    SwarmRouter  — top-level interface para MomentumEngine / specialist_spawn

Usage:
    router = VPNRouter.shared()
    async with router.route() as proxy_url:
        client = MoltbookClient(proxy=proxy_url)
        await client.register(...)
"""

from __future__ import annotations

import asyncio
import logging
import random
import statistics
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger("cortex.network.vpn_router")


# ─── Endpoint ──────────────────────────────────────────────────────────────────


class EndpointState(Enum):
    HEALTHY = auto()
    DEGRADED = auto()   # >30% failure rate
    DEAD = auto()       # >70% failure rate — excluded from routing


@dataclass
class VPNEndpoint:
    """Un nodo de transporte: proxy SOCKS5/HTTPS o endpoint VPN local."""

    url: str                        # socks5://host:port | https://host:port | http://host:port
    label: str = ""                 # etiqueta humana (e.g. "mullvad-es-1")
    weight: float = 1.0             # mayor = más probabilidad de selección
    success: int = 0
    failure: int = 0
    consecutive_failures: int = 0
    last_checked: float = field(default_factory=time.monotonic)
    latency_ms: float = 9999.0
    _latency_history: list[float] = field(default_factory=list, repr=False)

    @property
    def latency_volatility(self) -> float:
        """Desviación estándar de latencia. Mayor = red celular/residencial (más humana)."""
        if len(self._latency_history) < 2:
            return 0.0
        return statistics.pstdev(self._latency_history)

    @property
    def state(self) -> EndpointState:
        total = self.success + self.failure
        if total < 3:
            return EndpointState.HEALTHY  # sin datos suficientes
        rate = self.failure / total
        if self.consecutive_failures >= 5:
            return EndpointState.DEAD
        if rate > 0.7:
            return EndpointState.DEAD
        if rate > 0.3:
            return EndpointState.DEGRADED
        return EndpointState.HEALTHY

    @property
    def effective_weight(self) -> float:
        """Peso ajustado por latencia y estado."""
        state_multiplier = {
            EndpointState.HEALTHY: 1.0,
            EndpointState.DEGRADED: 0.3,
            EndpointState.DEAD: 0.0,
        }[self.state]

        # Penalti por latencia absoluta (hasta 90% reducción)
        latency_penalty = max(0.1, 1.0 - (self.latency_ms / 10_000))

        # Bonificador por entropía (hasta +50% peso para redes volátiles)
        # 500ms stdev -> +0.5 multiplier max
        entropy_bonus = min(0.5, self.latency_volatility / 1000.0)

        return self.weight * state_multiplier * latency_penalty * (1.0 + entropy_bonus)

    def record_success(self, latency_ms: float = 0.0) -> None:
        self.success += 1
        self.consecutive_failures = 0
        self.latency_ms = latency_ms if latency_ms > 0 else self.latency_ms
        if latency_ms > 0:
            self._latency_history.append(latency_ms)
            self._latency_history = self._latency_history[-20:]  # keep last 20
        self.last_checked = time.monotonic()

    def record_failure(self) -> None:
        self.failure += 1
        self.consecutive_failures += 1
        self.last_checked = time.monotonic()

    def __str__(self) -> str:
        bar_filled = int(self.effective_weight * 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        return (
            f"[{self.state.name:8s}] {bar} | "
            f"{self.label or self.url[:30]:30s} | "
            f"✓{self.success} ✗{self.failure} | "
            f"LAT: {self.latency_ms:4.0f}ms (±{self.latency_volatility:3.0f})"
        )


# ─── Pool ───────────────────────────────────────────────────────────────────────


class VPNPool:
    """Pool vivo de endpoints con health-checking continuo.

    Estrategia de selección: Weighted Random Selection (WRS) sobre endpoints
    sanos. Si todos están muertos → fallback a conexión directa.
    """

    def __init__(self, endpoints: list[VPNEndpoint]) -> None:
        self._endpoints = endpoints
        self._lock = asyncio.Lock()
        self._health_task: asyncio.Task | None = None

    @classmethod
    def from_urls(cls, urls: list[str]) -> VPNPool:
        """Construir pool desde lista de URLs."""
        endpoints = [
            VPNEndpoint(url=u, label=u.split("//")[-1][:30])
            for u in urls
        ]
        return cls(endpoints)

    def add(self, endpoint: VPNEndpoint) -> None:
        self._endpoints.append(endpoint)

    def alive_count(self) -> int:
        return sum(
            1 for e in self._endpoints
            if e.state != EndpointState.DEAD
        )

    def pick(self) -> VPNEndpoint | None:
        """Weighted random selection — O(N)."""
        candidates = [e for e in self._endpoints if e.effective_weight > 0]
        if not candidates:
            return None
        weights = [e.effective_weight for e in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    def pick_n(self, n: int) -> list[VPNEndpoint]:
        """Seleccionar N endpoints distintos (para enjambre paralelo)."""
        candidates = [e for e in self._endpoints if e.effective_weight > 0]
        if not candidates:
            return []
        # Weighted sampling sin reemplazo
        selected: list[VPNEndpoint] = []
        remaining = list(candidates)
        for _ in range(min(n, len(remaining))):
            weights = [e.effective_weight for e in remaining]
            total = sum(weights)
            if total == 0:
                break
            chosen = random.choices(remaining, weights=weights, k=1)[0]
            selected.append(chosen)
            remaining.remove(chosen)
        return selected

    async def health_check_endpoint(self, endpoint: VPNEndpoint) -> None:
        """Verifica un endpoint con un GET a un target neutro."""
        import httpx
        probe_url = "https://api.ipify.org?format=json"
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(
                proxy=endpoint.url,
                timeout=10.0,
            ) as client:
                resp = await client.get(probe_url)
                if resp.status_code == 200:
                    latency = (time.monotonic() - t0) * 1000
                    endpoint.record_success(latency_ms=latency)
                    logger.debug(
                        "✅ [HEALTH] %s → %s (%.0fms)",
                        endpoint.label, resp.json().get("ip", "?"), latency,
                    )
                else:
                    endpoint.record_failure()
        except Exception as exc:
            endpoint.record_failure()
            logger.debug("❌ [HEALTH] %s → %s", endpoint.label, exc)

    async def run_health_loop(self, interval: float = 60.0) -> None:
        """Health check continuo en background. Ejecutar como asyncio.Task."""
        logger.info("🩺 VPN Health Loop started (%d endpoints)", len(self._endpoints))
        while True:
            tasks = [self.health_check_endpoint(e) for e in self._endpoints]
            await asyncio.gather(*tasks, return_exceptions=True)
            alive = self.alive_count()
            logger.info("🩺 Pool: %d/%d alive", alive, len(self._endpoints))
            await asyncio.sleep(interval)

    def start_health_loop(self, interval: float = 60.0) -> None:
        """Lanza el health loop como tarea en background."""
        if self._health_task and not self._health_task.done():
            return
        self._health_task = asyncio.create_task(
            self.run_health_loop(interval),
            name="vpn_health_loop",
        )

    def status_table(self) -> str:
        lines = [
            "╔══════════════════════════════════════════════════════════════════╗",
            "║          🛡️  VPN POOL STATUS                                     ║",
            "╠══════════════════════════════════════════════════════════════════╣",
        ]
        for e in sorted(self._endpoints, key=lambda x: -x.effective_weight):
            lines.append(f"║  {str(e):<64} ║")
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append(f"║  ALIVE: {self.alive_count()}/{len(self._endpoints):<57}║")
        lines.append("╚══════════════════════════════════════════════════════════════════╝")
        return "\n".join(lines)


# ─── Router ─────────────────────────────────────────────────────────────────────


class VPNRouter:
    """Autorouter soberano. Singleton compartido por todo el enjambre.

    Funciones:
        route()        — context manager que retorna una proxy URL
        assign_agent() — asigna un endpoint dedicado a un agente
        release_agent()— libera el endpoint de un agente
        bulk_assign()  — asigna N endpoints para spawn masivo
    """

    _instance: VPNRouter | None = None

    # VPNs privadas locales o de confianza — añadir las propias aquí.
    # Formato: protocolo://host:port
    DEFAULT_ENDPOINTS: list[str] = [
        # Sistemas locales (Mullvad, NordVPN SOCKS5, etc.)
        # "socks5://127.0.0.1:1080",   # Local VPN SOCKS5 proxy
        # "socks5://127.0.0.1:9050",   # Tor (fallback extremo)
        # Proxies verificados — completar con el pool real
        # "socks5://user:pass@host:port",
        # "https://user:pass@host:port",
    ]

    def __init__(self, endpoints: list[str] | None = None) -> None:
        urls = endpoints or self.DEFAULT_ENDPOINTS
        self._pool = VPNPool.from_urls(urls) if urls else VPNPool([])
        self._agent_assignments: dict[str, VPNEndpoint] = {}
        self._fallback_direct = True  # Si pool vacío → conexión directa

    @classmethod
    def shared(cls, endpoints: list[str] | None = None) -> VPNRouter:
        """Singleton — un router para todo el proceso."""
        if cls._instance is None:
            cls._instance = cls(endpoints)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Resetear singleton (tests o reconfiguración)."""
        cls._instance = None

    def load_endpoints(self, urls: list[str]) -> None:
        """Cargar endpoints en caliente sin reiniciar el router."""
        for url in urls:
            label = url.split("//")[-1][:30]
            self._pool.add(VPNEndpoint(url=url, label=label))
        logger.info(
            "🔌 Loaded %d new endpoints. Pool: %d total",
            len(urls), len(self._pool._endpoints),
        )

    def load_from_file(self, path: str) -> int:
        """Cargar endpoints desde fichero (una URL por línea)."""
        from pathlib import Path
        p = Path(path)
        if not p.exists():
            logger.warning("VPN endpoint file not found: %s", path)
            return 0
        lines = [
            ln.strip() for ln in p.read_text().splitlines()
            if ln.strip() and not ln.startswith("#")
        ]
        self.load_endpoints(lines)
        return len(lines)

    @asynccontextmanager
    async def route(self) -> AsyncIterator[str | None]:
        """Context manager que proporciona una proxy URL para una request.

        Registra éxito/fallo automáticamente:
            async with router.route() as proxy_url:
                # proxy_url es str | None (None = conexión directa)
        """
        endpoint = self._pool.pick()
        proxy_url = endpoint.url if endpoint else None

        if proxy_url is None and self._fallback_direct:
            logger.debug("🔗 [ROUTE] No VPN available — using direct connection")

        t0 = time.monotonic()
        success = True
        try:
            yield proxy_url
        except OSError as exc:
            success = False
            if endpoint:
                endpoint.record_failure()
            logger.warning("⚠️ [ROUTE] %s failed: %s", proxy_url or "direct", exc)
            raise
        finally:
            if success and endpoint:
                latency = (time.monotonic() - t0) * 1000
                endpoint.record_success(latency_ms=latency)

    def assign_agent(self, agent_name: str) -> str | None:
        """Asigna un endpoint dedicado a un agente (estabilidad de sesión)."""
        if agent_name in self._agent_assignments:
            ep = self._agent_assignments[agent_name]
            if ep.state != EndpointState.DEAD:
                return ep.url
        ep = self._pool.pick()
        if ep:
            self._agent_assignments[agent_name] = ep
            logger.debug("🎯 [ASSIGN] %s → %s", agent_name, ep.label)
            return ep.url
        return None  # conexión directa

    def release_agent(self, agent_name: str) -> None:
        """Libera el endpoint asignado a un agente."""
        self._agent_assignments.pop(agent_name, None)

    def record_agent_failure(self, agent_name: str) -> str | None:
        """Registra fallo y reasigna a otro endpoint."""
        ep = self._agent_assignments.pop(agent_name, None)
        if ep:
            ep.record_failure()
            logger.warning("🔄 [REROUTE] %s — endpoint dead, reassigning", agent_name)
        return self.assign_agent(agent_name)

    def bulk_assign(self, agent_names: list[str]) -> dict[str, str | None]:
        """Asigna endpoints en bloque para spawn masivo."""
        endpoints = self._pool.pick_n(len(agent_names))
        result: dict[str, str | None] = {}
        for i, name in enumerate(agent_names):
            if i < len(endpoints):
                ep = endpoints[i]
                self._agent_assignments[name] = ep
                result[name] = ep.url
            else:
                result[name] = None  # direct
        logger.info(
            "🌊 [BULK] %d agents assigned | %d with proxy | %d direct",
            len(agent_names),
            sum(1 for v in result.values() if v),
            sum(1 for v in result.values() if not v),
        )
        return result

    def start_health_loop(self, interval: float = 60.0) -> None:
        """Activa el health-checking continuo."""
        self._pool.start_health_loop(interval)

    def status(self) -> str:
        return self._pool.status_table()

    @property
    def pool_size(self) -> int:
        return len(self._pool._endpoints)

    @property
    def alive_count(self) -> int:
        return self._pool.alive_count()


# ─── SwarmRouter ────────────────────────────────────────────────────────────────


class SwarmRouter:
    """Interface de alto nivel para integrar VPNRouter con el enjambre Moltbook.

    Envuelve MoltbookClient instancias con autorouting transparente.
    Compatible con MomentumEngine, CreativeBoostProtocol y specialist_spawn.
    """

    def __init__(
        self,
        endpoint_file: str | None = None,
        endpoints: list[str] | None = None,
        health_interval: float = 60.0,
    ) -> None:
        self.router = VPNRouter.shared(endpoints)

        if endpoint_file:
            loaded = self.router.load_from_file(endpoint_file)
            logger.info("📁 Loaded %d endpoints from %s", loaded, endpoint_file)

        if self.router.pool_size > 0:
            self.router.start_health_loop(health_interval)
            logger.info(
                "🛡️ SwarmRouter online — %d endpoints | health_interval=%.0fs",
                self.router.pool_size, health_interval,
            )
        else:
            logger.warning(
                "⚠️ SwarmRouter: No VPN endpoints configured. "
                "All traffic via direct connection. Add endpoints to "
                "VPNRouter.DEFAULT_ENDPOINTS or pass an endpoint file."
            )

    def proxy_for(self, agent_name: str) -> str | None:
        """Devuelve la proxy URL asignada a un agente (o None para directo)."""
        return self.router.assign_agent(agent_name)

    def proxies_for_swarm(self, agent_names: list[str]) -> dict[str, str | None]:
        """Asigna proxies al enjambre completo en una sola operación."""
        return self.router.bulk_assign(agent_names)

    async def verified_proxy_for(self, agent_name: str) -> str | None:
        """Como proxy_for() pero verifica el endpoint antes de devolver."""
        proxy_url = self.proxy_for(agent_name)
        if proxy_url is None:
            return None
        ep = self.router._agent_assignments.get(agent_name)
        if ep is None:
            return None
        # Quick probe
        await self.router._pool.health_check_endpoint(ep)
        if ep.state == EndpointState.DEAD:
            logger.warning("💀 [VERIFY] Endpoint dead for %s, rerouting...", agent_name)
            return self.router.record_agent_failure(agent_name)
        return proxy_url

    def release(self, agent_name: str) -> None:
        self.router.release_agent(agent_name)

    def status(self) -> str:
        return self.router.status()


# ─── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="VPN Autorouter — Sovereign Transport CLI")
    parser.add_argument("--endpoints", nargs="*", help="Lista de proxy URLs (socks5://host:port)")
    parser.add_argument("--file", help="Fichero con una URL por línea")
    parser.add_argument("--check", action="store_true", help="Health check inmediato")
    parser.add_argument("--assign", nargs="*", help="Asignar endpoints a agentes")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    async def run() -> None:
        router = VPNRouter.shared(args.endpoints)
        if args.file:
            router.load_from_file(args.file)

        if args.check and router.pool_size > 0:
            print("🩺 Running health checks...")
            tasks = [router._pool.health_check_endpoint(e) for e in router._pool._endpoints]
            await asyncio.gather(*tasks, return_exceptions=True)

        if args.assign:
            assignments = router.bulk_assign(args.assign)
            for agent, proxy in assignments.items():
                print(f"  {agent:30s} → {proxy or 'DIRECT'}")

        print(router.status())

    asyncio.run(run())
