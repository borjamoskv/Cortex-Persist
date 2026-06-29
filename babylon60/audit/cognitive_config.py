# [C5-REAL] Exergy-Maximized
"""
COGNITIVE-CONFIG: Declarative policies and SQL definitions for Cognitive Router.
"""

from babylon60.audit.cognitive_classifier import SafetyClassifier

_CREATE_ROUTER_LOG_SQL = """
CREATE TABLE IF NOT EXISTS cognitive_router_log (
    routing_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,
    detected_sensitivity TEXT NOT NULL,
    user_tier TEXT NOT NULL,
    assigned_model TEXT NOT NULL,
    data_retention_flag INTEGER NOT NULL,
    prev_hash TEXT NOT NULL UNIQUE,
    signature TEXT NOT NULL,
    classifier_version TEXT NOT NULL,
    routing_policy_version TEXT NOT NULL
);
"""

DEFAULT_ROUTING_POLICY = {
    "version": "v2.0.0-declarative",
    "default_tier": "General-Public",
    "categories": SafetyClassifier.DEFAULT_CATEGORIES,
    "tiers": {
        "Trusted-Partner": {
            "rules": [
                {
                    "match_category": "cybersecurity",
                    "assigned_model": "Mythos-5-Unleashed",
                    "retention_required": True,
                },
                {
                    "match_category": "biology",
                    "assigned_model": "Mythos-5-Unleashed",
                    "retention_required": True,
                },
                {
                    "match_category": "chemistry",
                    "assigned_model": "Mythos-5-Unleashed",
                    "retention_required": True,
                },
            ],
            "default_model": "Fable-5-Core",
        },
        "General-Public": {
            "rules": [
                {
                    "match_category": "cybersecurity",
                    "assigned_model": "Opus-4.8-Fallback",
                    "retention_required": False,
                },
                {
                    "match_category": "biology",
                    "assigned_model": "Opus-4.8-Fallback",
                    "retention_required": False,
                },
                {
                    "match_category": "chemistry",
                    "assigned_model": "Opus-4.8-Fallback",
                    "retention_required": False,
                },
            ],
            "default_model": "Fable-5-Core",
        },
    },
}
