"""
Tests for the Privacy-Aware Data Classifier v2.

Covers all 25 pattern categories across 4 severity tiers.
"""

from cortex.storage.classifier import DataSensitivity, classify_content

# ── Tier 0: Clean Content ─────────────────────────────────────────────


class TestClassifierCleanContent:
    """Clean content should pass through without flags."""

    def test_normal_text(self):
        r = classify_content("We decided to use React for the frontend.")
        assert not r.is_sensitive
        assert r.matches == []

    def test_code_without_secrets(self):
        r = classify_content("def hello(): return 'world'")
        assert not r.is_sensitive


# ── Tier 1: Critical (score=1.0) ──────────────────────────────────────


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
        # Constructed dynamically to avoid GitHub secret scanning
        uri = "mongodb+srv://" + "user:pass@cluster.mongodb.net"
        r = classify_content(uri)
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


# ── Tier 2: PII (score=0.9) ──────────────────────────────────────────


class TestTier2PII:
    """Tier 2: PII patterns → score 0.9"""

    def test_email_address(self):
        r = classify_content("Contact us at admin@cortex-memory.io for support.")
        assert r.score >= 0.9
        assert "email_address" in r.matches

    def test_phone_number(self):
        r = classify_content("Call us at +1-555-123-4567 for premium support.")
        assert r.score >= 0.9
        assert "phone_number" in r.matches

    def test_ssn(self):
        r = classify_content("Employee SSN: 123-45-6789 is on file.")
        assert r.score >= 0.9
        assert "ssn" in r.matches

    def test_credit_card_visa(self):
        r = classify_content("Payment with card 4111-1111-1111-1111 processed.")
        assert r.score >= 0.9
        assert "credit_card" in r.matches

    def test_credit_card_mastercard(self):
        r = classify_content("Card number: 5500 0000 0000 0004")
        assert r.score >= 0.9
        assert "credit_card" in r.matches

    def test_passport_number(self):
        r = classify_content("Passport: AB1234567, valid until 2030.")
        assert r.score >= 0.9
        assert "passport_number" in r.matches


# ── Tier 3: Platform Tokens (score=0.8) ───────────────────────────────


class TestTier3Platform:
    """Tier 3: Platform tokens → score 0.8"""

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

    def test_azure_key(self):
        r = classify_content("AccountKey=dGVzdGtleXZhbHVlMTIzNDU2Nzg5MA==")
        assert r.score >= 0.8
        assert "azure_key" in r.matches

    def test_gcp_service_account(self):
        r = classify_content('{"type": "service_account", "project_id": "cortex"}')
        assert r.score >= 0.8
        assert "gcp_service_account" in r.matches

    def test_twilio_key(self):
        # Constructed dynamically to avoid GitHub secret scanning
        sid = "AC" + "abcdef0123456789" * 2
        r = classify_content(sid)
        assert r.score >= 0.8
        assert "twilio_key" in r.matches

    def test_sendgrid_key(self):
        r = classify_content("SG.abcdefghijklmnopqrstuv.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqr")
        assert r.score >= 0.8
        assert "sendgrid_key" in r.matches


# ── Tier 4: Standard (score=0.7) ──────────────────────────────────────


class TestTier4Standard:
    """Tier 4: Generic/cloud/infra keys → score 0.7"""

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

    def test_npm_token(self):
        r = classify_content("npm_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij")
        assert r.score >= 0.7
        assert "npm_token" in r.matches

    def test_pypi_token(self):
        token = "pypi-" + "A" * 50
        r = classify_content(token)
        assert r.score >= 0.7
        assert "pypi_token" in r.matches

    def test_docker_auth(self):
        r = classify_content('{"auth": "dXNlcjpwYXNzd29yZDEyMzQ1Njc4OTA="}')
        assert r.score >= 0.7
        assert "docker_auth" in r.matches


# ── Cross-Tier Tests ─────────────────────────────────────────────────


class TestMultiplePatterns:
    """Multiple patterns in same content."""

    def test_multiple_detections(self):
        stripe_token = "".join(["s", "k", "_", "l", "i", "v", "e", "_"]) + "X" * 24
        r = classify_content(f"AKIAIOSFODNN7EXAMPLE1 and {stripe_token}")
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

    def test_pii_overrides_platform(self):
        """PII tier should override standard tier scores."""
        r = classify_content(
            "api_key: 'sk_1234567890abcdef1234567890abcdef' "
            "and SSN 123-45-6789"
        )
        assert r.score >= 0.9  # PII overrides standard's 0.7


# ── Model Tests ──────────────────────────────────────────────────────


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
