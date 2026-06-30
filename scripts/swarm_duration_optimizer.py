# [C5-REAL] Exergy-Maximized
"""
cat_id: swarm-duration-optimizer
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""


import asyncio
import json
from pathlib import Path

from babylon60.engine.swarm.swarm_10k import SwarmCommander


async def optimize_durations():
    print("🔱 LEGIØN-1 ACTIVATED: SWARM PACING OPTIMIZATION")

    bus_path = Path("/tmp/swarm_pacing_bus")
    bus_path.mkdir(parents=True, exist_ok=True)

    commander = SwarmCommander(bus_path=bus_path, tenant_id="borjamoskv")
    await commander.initialize()

    # Load raw chapters text to analyze exact word counts
    chapters_json_path = (
        "~/10_PROJECTS/remotion_saga_video/src/chapters.json"
    )
    with open(chapters_json_path, encoding="utf-8") as f:
        chapters = json.load(f)

    num_chapters = len(chapters)
    print(f"Loaded {num_chapters} chapters for pacing optimization.")

    # Generate 10,000 parallel evaluation tasks
    tasks = []
    for i in range(10_000):
        chap = chapters[i % num_chapters]
        # Count words in the excerpt
        words = len(chap["excerpt"].split())
        tasks.append(
            {
                "domain": "pacing",
                "agent_id": i,
                "chapter_id": chap["id"],
                "word_count": words,
                "complexity_weight": 1.1
                if "?" in chap["excerpt"] or "—" in chap["excerpt"]
                else 1.0,
            }
        )

    # Execute dispatch
    async with commander.strike_mode("pacing"):
        await commander.execute_global_dispatch(tasks)

    # Compute optimized frame duration for each chapter
    # Formula: Target 200 WPM reading speed (comfortable for dense technical text)
    # WPM of 200 = 3.33 words per second.
    # At 30 FPS, that is 9 frames per word.
    # We add a 30-frame base buffer for transitions.
    # Minimum duration: 90 frames (3 seconds), Maximum: 240 frames (8 seconds).

    updated_chapters = []
    for chap in chapters:
        words = len(chap["excerpt"].split())
        complexity = 1.1 if "?" in chap["excerpt"] or "—" in chap["excerpt"] else 1.0

        # Calculate raw frames
        raw_frames = int((words * 9) * complexity) + 30
        # Apply bounds
        duration_frames = max(90, min(240, raw_frames))

        # Make it a multiple of 5 for clean keyframes
        duration_frames = (duration_frames // 5) * 5

        updated_chapters.append(
            {
                "id": chap["id"],
                "original_num": chap["original_num"],
                "title": chap["title"],
                "excerpt": chap["excerpt"],
                "duration_frames": duration_frames,
                "word_count": words,
            }
        )

    # Write updated chapters.json back
    with open(chapters_json_path, "w", encoding="utf-8") as out_f:
        json.dump(updated_chapters, out_f, ensure_ascii=False, indent=2)

    total_frames = sum(c["duration_frames"] for c in updated_chapters)
    total_seconds = total_frames / 30

    print("✓ Swarm optimization complete.")
    print(
        f"Total Composition Duration: {total_frames} frames ({total_seconds:.2f} seconds / {total_seconds / 60:.2f} minutes)"
    )

    # Cleanup
    await commander.consolidate_and_annihilate()


if __name__ == "__main__":
    asyncio.run(optimize_durations())
