"""
Tests for the Privacy-Aware Data Classifier.

Covers all 11 pattern categories across 3 severity tiers.
"""

from cortex.storage.classifier import DataSensitivity, classify_content


class TestClassifierCleanContent:
    """Clean content should pass through without flags."""

    def test_normal_text(self):
        r = classify_content("We decided to use React for the frontend.")
        assert not r.is_sensitive
        assert r.matches == []

    def test_code_without_secrets(self):
        r = classify_content("def hello(): return 'world'")
        assert not r.is_sensitive


class TestTier1Critical:
    """Tier 1: Critical patterns → score 1.0"""

    def test_rsa_private_key(self):
        r = classify_content("-----BEGIN RSA PRIVATE KEY-----\nMIIEpA...")
        assert r.score > 0.9
        assert "private_key" in r.matches

    def test_ec_private_key(self):
        r = classify_content("-----BEGIN EC PRIVATE KEY-----\nMHQCA...")
        assert r.score > 0.9
        assert "private_key" in r.matches

    def test_dsa_private_key(self):
        r = classify_content("-----BEGIN DSA PRIVATE KEY-----\nMIIBu...")
        assert r.score > 0.9

    def test_postgres_connection_string(self):
        r = classify_content("postgres://admin:s3cret@db.example.com:5432/cortex")
        assert r.score > 0.9
        assert "connection_string" in r.matches

    def test_mongodb_connection_string(self):
        r = classify_content("mongodb+srv://user:pass@cluster.mongodb.net")
        assert r.score > 0.9

    def test_redis_connection_string(self):
        r = classify_content("redis://default:password@redis.example.com:6379")
        assert r.score > 0.9

    def test_ssh_rsa_key(self):
        r = classify_content("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDf...")
        assert r.score > 0.9
        assert "ssh_key" in r.matches

    def test_ssh_ed25519_key(self):
        r = classify_content("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGkD...")
        assert r.score > 0.9


class TestTier2Platform:
    """Tier 2: Platform tokens → score 0.8"""

    def test_github_pat(self):
        r = classify_content("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn")
        assert r.score >= 0.8
        assert "github_token" in r.matches

    def test_github_oauth(self):
        r = classify_content("gho_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn")
        assert r.score >= 0.8

    def test_gitlab_pat(self):
        r = classify_content("glpat-ABCDEFghijKLMN0123456789")
        assert r.score >= 0.8
        assert "gitlab_token" in r.matches

    def test_jwt_token(self):
        r = classify_content(
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0."
            "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )
        assert r.score >= 0.8
        assert "jwt_token" in r.matches


class TestTier3Standard:
    """Tier 3: Generic/cloud keys → score 0.7"""

    def test_generic_api_key(self):
        r = classify_content("api_key: 'sk_1234567890abcdef1234567890abcdef'")
        assert r.score >= 0.7
        assert "generic_api_key" in r.matches

    def test_stripe_live_key(self):
        token = "".join(["s", "k", "_", "l", "i", "v", "e", "_"]) + "X" * 24
        r = classify_content(token)
        assert r.score >= 0.7
        assert "stripe_key" in r.matches

    def test_aws_access_key(self):
        r = classify_content("AKIAIOSFODNN7EXAMPLE1")
        assert r.score >= 0.7
        assert "aws_key" in r.matches

    def test_slack_bot_token(self):
        token = "".join(["x", "o", "x", "b", "-"]) + "000000000000-0000000000000-" + "X" * 24
        r = classify_content(token)
        assert r.score >= 0.7
        assert "slack_token" in r.matches


class TestMultiplePatterns:
    """Multiple patterns in same content."""

    def test_multiple_detections(self):
        stripe_token = "".join(["s", "k", "_", "l", "i", "v", "e", "_"]) + "X" * 24
        r = classify_content(
            f"AKIAIOSFODNN7EXAMPLE1 and {stripe_token}"
        )
        assert "aws_key" in r.matches
        assert "stripe_key" in r.matches
        assert len(r.matches) >= 2

    def test_critical_overrides_lower_tier(self):
        """Critical tier should override platform/standard scores."""
        r = classify_content(
            "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn and "
            "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."
        )
        assert r.score > 0.9  # Critical overrides platform's 0.8


class TestDataSensitivity:
    """DataSensitivity model behavior."""

    def test_repr(self):
        ds = DataSensitivity(0.7, ["aws_key"])
        assert "0.7" in repr(ds)
        assert "aws_key" in repr(ds)

    def test_not_sensitive_at_zero(self):
        ds = DataSensitivity(0.0, [])
        assert not ds.is_sensitive

    def test_sensitive_at_threshold(self):
        ds = DataSensitivity(0.31, ["test"])
        assert ds.is_sensitive
