# Tutorial: Memory for LangChain Agents

Give your LangChain agent persistent, searchable memory backed by CORTEX.

## The Problem

LangChain's default memory is ephemeral — it disappears when your process dies. CORTEX gives you:

- **Persistent** memory that survives restarts
- **Semantic search** across past interactions
- **Temporal queries** to recall what the agent knew at any point

## Setup

```bash
pip install cortex-memory langchain-openai
```

```python
from cortex.engine import CortexEngine

engine = CortexEngine(db_path="~/.cortex/cortex.db")
engine.init_db()
```

## Store Agent Observations

After each agent step, store what it learned:

```python
def store_observation(project: str, observation: str, tags: list[str] | None = None):
    """Store an agent observation in CORTEX."""
    engine.store(
        project=project,
        content=observation,
        fact_type="knowledge",
        tags=tags,
        source="langchain-agent",
    )
```

## Build Context from Memory

Before each agent invocation, recall relevant context:

```python
def build_context(project: str, query: str, top_k: int = 5) -> str:
    """Search CORTEX for relevant past knowledge."""
    results = engine.search(query, project=project, top_k=top_k)

    if not results:
        return "No relevant past observations found."

    context_parts = []
    for r in results:
        context_parts.append(f"- [{r.fact_type}] {r.content} (score: {r.score:.2f})")

    return "## Relevant Past Knowledge\n" + "\n".join(context_parts)
```

## Integration with LangChain

```python
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

llm = ChatOpenAI(model="gpt-4o")

def agent_step(project: str, user_input: str) -> str:
    # 1. Search memory for context
    context = build_context(project, user_input)

    # 2. Build prompt with memory
    messages = [
        SystemMessage(content=f"You are a helpful assistant.\n\n{context}"),
        HumanMessage(content=user_input),
    ]

    # 3. Get response
    response = llm.invoke(messages)

    # 4. Store the interaction as memory
    store_observation(
        project=project,
        observation=f"User asked: {user_input}. Agent answered: {response.content[:200]}",
        tags=["interaction"],
    )

    return response.content
```

## Using the API Instead

For distributed agents, use the REST API:

```python
from cortex.client import CortexClient

client = CortexClient(base_url="http://localhost:8742", api_key="your-key")

# Store
client.store(project="my-agent", content="Learned that X does Y")

# Search
results = client.search("how does X work?", top_k=3)
```

## Next Steps

- Use `cortex recall my-agent` to inspect everything your agent knows
- Use `cortex history my-agent --at "2026-01-15"` to see what it knew last week
- Use `cortex export` to create a context snapshot for cold starts
