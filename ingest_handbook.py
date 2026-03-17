from cortex.cli.common import DEFAULT_DB, get_engine


def main():
    engine = get_engine(DEFAULT_DB)
    with open(
        "/Users/borjafernandezangulo/.cortex/ai_agents_handbook.pdf.txt", encoding="utf-8"
    ) as f:
        content = f.read()

    # Using the store_sync method from CortexEngine
    fact_id = engine.store_sync(
        project="CORTEX_STANDARDS",
        content=content,
        fact_type="axiom",  # Using axiom as rulebook
        source="agent:moskv",
        confidence="C5",
        tags=["google_agent_handbook", "standardization"],
    )
    print(f"✅ Handbook ingested successfully into Ledger. Fact ID: {fact_id}")


if __name__ == "__main__":
    main()
