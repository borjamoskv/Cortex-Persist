"""Tests for cortex.memory.models — Cognitive Memory Domain Models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sys
from unittest.mock import MagicMock

import pytest

# Stub qdrant_client before importing cortex.memory
_qd = MagicMock()
sys.modules["qdrant_client"] = _qd
sys.modules["qdrant_client.models"] = _qd.models

from cortex.memory.models import EpisodicSnapshot, MemoryEntry, MemoryEvent  # noqa: E402


# ─── MemoryEntry (dataclass) ──────────────────────────────────────────


class TestMemoryEntry:
    def test_defaults(self):
        entry = MemoryEntry(content="test content")
        assert entry.content == "test content"
        assert entry.source == "episodic"
        assert entry.project is None
        assert isinstance(entry.metadata, dict)
        assert entry.id  # auto-generated

    def test_auto_id_is_unique(self):
        a = MemoryEntry(content="a")
        b = MemoryEntry(content="b")
        assert a.id != b.id

    def test_custom_fields(self):
        entry = MemoryEntry(
            content="fact",
            project="cortex",
            source="reflection",
            metadata={"key": "val"},
        )
        assert entry.project == "cortex"
        assert entry.source == "reflection"
        assert entry.metadata["key"] == "val"

    def test_to_payload(self):
        entry = MemoryEntry(
            content="payload test",
            project="proj",
            source="ghost",
            metadata={"extra": 42},
        )
        payload = entry.to_payload()
        assert payload["content"] == "payload test"
        assert payload["project"] == "proj"
        assert payload["source"] == "ghost"
        assert payload["extra"] == 42
        assert "created_at" in payload

    def test_to_payload_null_project_becomes_empty(self):
        entry = MemoryEntry(content="test")
        payload = entry.to_payload()
        assert payload["project"] == ""

    def test_has_slots(self):
        assert hasattr(MemoryEntry, "__slots__")


# ─── MemoryEvent (Pydantic v2) ────────────────────────────────────────


class TestMemoryEvent:
    def test_required_fields(self):
        event = MemoryEvent(
            role="user",
            content="hello",
            token_count=5,
            session_id="s1",
        )
        assert event.role == "user"
        assert event.content == "hello"
        assert event.token_count == 5
        assert event.session_id == "s1"

    def test_auto_generated_fields(self):
        event = MemoryEvent(
            role="assistant",
            content="world",
            token_count=3,
            session_id="s1",
        )
        # UUID format
        uuid.UUID(event.event_id)
        # Timestamp is recent UTC
        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.tzinfo == timezone.utc

    def test_metadata_defaults_to_empty(self):
        event = MemoryEvent(
            role="user", content="x", token_count=1, session_id="s1"
        )
        assert event.metadata == {}

    def test_custom_metadata(self):
        event = MemoryEvent(
            role="user",
            content="x",
            token_count=1,
            session_id="s1",
            metadata={"tool": "search", "emotion": "flow"},
        )
        assert event.metadata["tool"] == "search"

    def test_negative_tokens_rejected(self):
        with pytest.raises(Exception):  # Pydantic validation error
            MemoryEvent(
                role="user", content="x", token_count=-1, session_id="s1"
            )

    def test_event_id_uniqueness(self):
        a = MemoryEvent(role="user", content="a", token_count=1, session_id="s1")
        b = MemoryEvent(role="user", content="b", token_count=1, session_id="s1")
        assert a.event_id != b.event_id


# ─── EpisodicSnapshot (Pydantic v2) ──────────────────────────────────


class TestEpisodicSnapshot:
    def test_required_fields(self):
        snap = EpisodicSnapshot(
            summary="Worked on auth system",
            vector_embedding=[0.1] * 384,
        )
        assert snap.summary == "Worked on auth system"
        assert len(snap.vector_embedding) == 384

    def test_auto_generated_fields(self):
        snap = EpisodicSnapshot(
            summary="snapshot", vector_embedding=[0.0] * 384
        )
        uuid.UUID(snap.snapshot_id)
        assert isinstance(snap.created_at, datetime)

    def test_linked_events_default_empty(self):
        snap = EpisodicSnapshot(
            summary="test", vector_embedding=[0.0] * 384
        )
        assert snap.linked_events == []

    def test_custom_linked_events(self):
        links = ["evt-1", "evt-2", "evt-3"]
        snap = EpisodicSnapshot(
            summary="test",
            vector_embedding=[0.0] * 384,
            linked_events=links,
            session_id="session-42",
        )
        assert snap.linked_events == links
        assert snap.session_id == "session-42"
