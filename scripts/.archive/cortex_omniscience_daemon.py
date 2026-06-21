import json
from pathlib import Path


def crystallize_awareness():
    home = Path.home()
    matrix = {
        "reality_level": "C5-REAL",
        "workflows": [],
        "skills": [],
        "plugins": [],
        "subagents": ["research", "self"],
    }

    wf_path = home / ".agents" / "workflows"
    if wf_path.exists():
        matrix["workflows"] = sorted([f.stem for f in wf_path.glob("*.md")])

    skills_path = home / ".gemini" / "config" / "skills"
    if skills_path.exists():
        matrix["skills"] = sorted([d.name for d in skills_path.iterdir() if d.is_dir()])

    plugins_path = home / ".gemini" / "config" / "plugins"
    if plugins_path.exists():
        matrix["plugins"] = sorted([d.name for d in plugins_path.iterdir() if d.is_dir()])

    output_path = home / "10_PROJECTS" / "cortex-persist" / "cortex_awareness_matrix.json"
    with open(output_path, "w") as f:
        json.dump(matrix, f, indent=2)

    import logging

    setup_cortex_logging()
    logging.info(f"OMNISCIENCE MATRIX CRISTALIZADA EN: {output_path}")
    logging.info(f"Workflows Indexados: {len(matrix['workflows'])}")
    logging.info(f"Skills Indexados: {len(matrix['skills'])}")
    logging.info(f"Plugins Indexados: {len(matrix['plugins'])}")


if __name__ == "__main__":
    crystallize_awareness()
