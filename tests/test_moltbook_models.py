"""Tests for Moltbook data models — frozen/slots, defaults, construction."""

import pytest

from moltbook.models import (
    HomeResponse,
    MoltbookCredentials,
    Post,
)


class TestModelDefaults:
    """Verify dataclass defaults and slot behavior."""

    def test_post_defaults(self):
        p = Post(id="p1", title="Test Post")
        assert p.upvotes == 0
        assert p.downvotes == 0
        assert p.comment_count == 0
        assert p.author is None
        assert p.submolt is None
        assert p.content is None
        assert p.verification_status is None

    def test_credentials_frozen(self):
        creds = MoltbookCredentials(api_key="sk_test", agent_name="bot")
        assert creds.api_key == "sk_test"
        with pytest.raises(AttributeError):
            creds.api_key = "sk_mutated"  # type: ignore[misc]

    def test_home_response_defaults(self):
        hr = HomeResponse()
        assert hr.agent_name == ""
        assert hr.karma == 0
        assert hr.unread_notifications == 0
        assert hr.activity_on_posts == []
        assert hr.direct_messages == []
        assert hr.announcement is None
        assert hr.following_posts == []
        assert hr.what_to_do_next == []
