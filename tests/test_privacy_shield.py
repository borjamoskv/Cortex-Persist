"""
Integration test: Privacy Shield in StoreMixin.

Verifies that sensitive content gets privacy metadata injected
at the data ingress point (_store_impl → _apply_privacy_shield).
"""



from cortex.engine.store_mixin import StoreMixin


class TestPrivacyShield:
    """Test the _apply_privacy_shield static method."""

    def test_clean_content_passes_through(self):
        """Non-sensitive content should NOT get privacy metadata."""
        meta = StoreMixin._apply_privacy_shield(
            "We decided to use React for the frontend.",
            "my-project",
            None,
        )
        assert meta is None

    def test_clean_content_preserves_existing_meta(self):
        """Existing meta should be untouched for clean content."""
        original = {"author": "borja", "source": "cli"}
        meta = StoreMixin._apply_privacy_shield(
            "Normal technical decision about architecture.",
            "my-project",
            original,
        )
        assert meta == original

    def test_api_key_triggers_flag(self):
        """Content with an API key must be flagged."""
        meta = StoreMixin._apply_privacy_shield(
            "Set api_key: 'sk_1234567890abcdef1234567890abcdef' in config.",
            "secrets-project",
            None,
        )
        assert meta is not None
        assert meta["privacy_flagged"] is True
        assert "generic_api_key" in meta["privacy_matches"]
        assert meta["privacy_score"] >= 0.7

    def test_private_key_triggers_critical_flag(self):
        """Private keys must trigger a critical (1.0) score."""
        meta = StoreMixin._apply_privacy_shield(
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAK...\n-----END RSA PRIVATE KEY-----",
            "infra-project",
            None,
        )
        assert meta is not None
        assert meta["privacy_flagged"] is True
        assert "private_key" in meta["privacy_matches"]
        assert meta["privacy_score"] > 0.9

    def test_connection_string_triggers_critical_flag(self):
        """Database connection strings must trigger critical flag."""
        meta = StoreMixin._apply_privacy_shield(
            "Use postgres://admin:s3cret@db.example.com:5432/cortex for prod.",
            "infra-project",
            None,
        )
        assert meta is not None
        assert meta["privacy_flagged"] is True
        assert "connection_string" in meta["privacy_matches"]
        assert meta["privacy_score"] > 0.9

    def test_stripe_key_triggers_flag(self):
        """Stripe live keys must be detected."""
        token = "".join(["s", "k", "_", "l", "i", "v", "e", "_"]) + "X" * 24
        meta = StoreMixin._apply_privacy_shield(
            f"Payment configured: {token}",
            "billing-project",
            None,
        )
        assert meta is not None
        assert meta["privacy_flagged"] is True
        assert "stripe_key" in meta["privacy_matches"]

    def test_aws_key_triggers_flag(self):
        """AWS access keys must be detected."""
        meta = StoreMixin._apply_privacy_shield(
            "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE1",
            "cloud-project",
            None,
        )
        assert meta is not None
        assert meta["privacy_flagged"] is True
        assert "aws_key" in meta["privacy_matches"]

    def test_existing_meta_merged_not_replaced(self):
        """Privacy metadata should merge with existing meta, not replace it."""
        original = {"author": "borja", "importance": "high"}
        meta = StoreMixin._apply_privacy_shield(
            "Set api_key: 'sk_1234567890abcdef1234567890abcdef'",
            "test-project",
            original,
        )
        assert meta is not None
        # Original keys preserved
        assert meta["author"] == "borja"
        assert meta["importance"] == "high"
        # Privacy keys added
        assert meta["privacy_flagged"] is True
        assert "generic_api_key" in meta["privacy_matches"]

    def test_multiple_patterns_all_captured(self):
        """When multiple patterns match, all should appear in matches."""
        token = "".join(["s", "k", "_", "l", "i", "v", "e", "_"]) + "X" * 24
        meta = StoreMixin._apply_privacy_shield(
            f"aws: AKIAIOSFODNN7EXAMPLE1, stripe: {token}",
            "multi-project",
            None,
        )
        assert meta is not None
        assert "aws_key" in meta["privacy_matches"]
        assert "stripe_key" in meta["privacy_matches"]
        assert len(meta["privacy_matches"]) >= 2
