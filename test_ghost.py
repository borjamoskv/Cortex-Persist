import asyncio
from pathlib import Path

from cortex.engine.ghost_mixin import GhostMixin


async def main():
    ghost_engine = GhostMixin()
    target_dir = Path("ghost_test_zone")
    target_dir.mkdir(exist_ok=True)

    print(f"Registrando Fantasma en {target_dir}/test_target.py...")
    test_file = target_dir / "test_target.py"
    test_file.touch()

    ghost_id = await ghost_engine.register_ghost(
        reference="legacy_api_v1",
        context="Endpoint deprecated, still used in 3 places. Needs refactor.",
        project="CORTEX_CORE",
        target_file=test_file,
    )

    print(f"Fantasma registrado con ID: {ghost_id}")

    print("\nEscaneando campo topográfico (ghost_test_zone/) en busca de fantasmas...")
    # Limitamos el escaneo solo a este directorio
    ghosts = await ghost_engine.list_active_ghosts(target_dir)
    for g in ghosts:
        print(f" - Encontrado: {g}")

    print(f"\nResolviendo fantasma {ghost_id}...")
    resolved = await ghost_engine.resolve_ghost(ghost_id=ghost_id, root_dir=target_dir)
    print(f"¿Resuelto?: {resolved}")

    print("\nEscaneando nuevamente...")
    ghosts_after = await ghost_engine.list_active_ghosts(target_dir)
    print(
        f"Fantasmas restantes con ID {ghost_id}: {sum(1 for g in ghosts_after if g['id'] == ghost_id)}"
    )


if __name__ == "__main__":
    asyncio.run(main())
