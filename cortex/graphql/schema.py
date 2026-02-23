"""
CORTEX v6 — Transport Layer: GraphQL Schema.

Exposes a unified graph for Swarm Flight Control (admin dashboard)
to query Memories, Tenants, and Agents in a single round-trip.
"""

from typing import Any

# Note: In a full v6 deployment, `strawberry` or `ariadne` will be added to pyproject.toml
# and this file will map Python dataclasses to the GraphQL AST.


class CortexGraphQLSchema:
    """Stub for the v6 GraphQL integration."""

    def __init__(self, memory_manager: Any, auth_manager: Any) -> None:
        self.memory = memory_manager
        self.auth = auth_manager

    def generate_schema(self) -> str:
        """Generates the SDL (Schema Definition Language) for Cortex."""
        return """
        type SearchResult {
            id: ID!
            content: String!
            score: Float!
            tenant_id: String
            project: String
            metadata: String
        }

        type Query {
            me: Tenant!
            session_events(limit: Int = 100): [MemoryEvent!]!
            search(query: String!, limit: Int = 5, project: String): [SearchResult!]!
        }

        type Mutation {
            memorize(content: String!, project: String, metadata: String): SearchResult!
            forget(id: ID!): Boolean!
        }
        """
