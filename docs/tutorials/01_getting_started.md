# Building Your First Agent Memory System

Welcome to CORTEX-Persist! This tutorial will walk you through integrating long-term, verifiable memory into your AI agent or application. 

By the end of this guide, you will understand:
1. What CORTEX provides out of the box.
2. How to start the local memory server.
3. How to store information securely with an audit trail.
4. How to retrieve information using semantic vector search.

---

## What is CORTEX?

When building AI agents, they often "forget" past conversations or important facts between sessions. CORTEX solves this by acting as a dedicated database for your agents. It features:
- **Vector Search:** Automatically converts text to embeddings for semantic retrieval.
- **Audit Ledger:** Cryptographically logs every change, so you know exactly *who* stored *what*, and *when*.
- **Local-First:** Runs entirely on your machine using SQLite—no cloud lock-in.

## Step 1: Start the Local Server

CORTEX provides a REST API out of the box. First, ensure it's installed:

```bash
pip install cortex-persist
```

Now, start the server. This will automatically initialize the local `cortex.db` SQLite database in your current directory.

```bash
uvicorn cortex.api:app --reload
```

*Tip: You can visit `http://localhost:8000/docs` in your browser to see the interactive API documentation.*

## Step 2: The CortexClient

Let's write a simple Python script to interact with our memory server. Create a file called `agent_memory.py`.

```python
from cortex import CortexClient

# Initialize the client pointing to our local server
client = CortexClient(base_url="http://localhost:8000")

# Optional: Ensure the connection is working
print("Client initialized successfully.")
```

## Step 3: Storing a Fact

In CORTEX, any piece of information stored is called a **Fact**. When you store a fact, CORTEX automatically:
1. Validates it.
2. Generates a vector embedding for future search.
3. Records the action in the immutable audit ledger.

Let's store a fact about our user:

```python
fact = client.store(
    content="The user prefers Python over JavaScript and works as a Data Engineer.",
    fact_type="user_preference",
    project="onboarding-bot"
)

print(f"Fact securely stored with ID: {fact.id}")
```

## Step 4: Searching Memory

Now, imagine the agent is chatting with the user in a new session. We can retrieve context by searching our memory database semantically.

```python
# The agent needs to know what programming language to suggest
search_query = "What programming language does the user prefer?"

# We ask CORTEX for the top 1 most relevant fact
results = client.search(search_query, top_k=1)

for result in results:
    print("Found Memory:")
    print(f"- Content: {result.content}")
    print(f"- Relevance Score: {result.score}")
```

## Next Steps

Congratulations! You've successfully added long-term semantic memory to your workflow. 

From here, you can explore:
- **[LangChain Integration](../examples/langchain_cortex_persist_example.py):** How to use CORTEX as a retriever inside LangChain chains.
- **Ledger Auditing:** How to use the CLI tool to verify the cryptographic history of your agent's memories.
