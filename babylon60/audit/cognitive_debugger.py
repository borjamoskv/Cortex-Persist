# [C5-REAL] Exergy-Maximized
"""
COGNITIVE-DEBUGGER: Replay debugger engine explaining matching rules and category triggers.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from babylon60.audit.cognitive_classifier import cosine_similarity

if TYPE_CHECKING:
    from babylon60.audit.cognitive_router import CognitiveRouter


class RoutingReplayDebugger:
    """Deterministic trace debugger explaining why a model decision was made for auditing."""

    def __init__(self, router: CognitiveRouter) -> None:
        self.router = router

    async def explain_decision(self, routing_id: str, prompt: str) -> dict[str, Any]:
        """Explains why a decision was reached for a logged record by replaying classification."""
        cursor = await self.router._conn.execute(
            """SELECT timestamp, prompt_hash, detected_sensitivity, user_tier, assigned_model, 
                      data_retention_flag, prev_hash, classifier_version, routing_policy_version 
               FROM cognitive_router_log WHERE routing_id = ?""",
            (routing_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Decision matching routing_id {routing_id} not found in database.")

        (
            timestamp,
            prompt_hash,
            sensitivity_json,
            user_tier,
            assigned_model,
            retention_flag,
            prev_hash,
            classifier_ver,
            routing_policy_ver,
        ) = row
        recorded_sensitivity = json.loads(sensitivity_json)

        # 1. Trace classification triggers
        detection_traces = []
        normalized_prompt = self.router.classifier._normalize_text(prompt)
        prompt_words = normalized_prompt.split()

        for cat_name, cat_data in self.router.classifier.categories.items():
            keywords = cat_data.get("keywords", [])
            for kw in keywords:
                if self.router.classifier._matches_keyword(prompt_words, kw):
                    detection_traces.append(
                        {
                            "category": cat_name,
                            "type": "keyword_match",
                            "matched_trigger": kw,
                            "details": f"Prompt matched token keyword '{kw}' after unicode normalization.",
                        }
                    )

        # Semantic anchor tracing
        if self.router.classifier.embedder and self.router.classifier._anchor_embeddings:
            try:
                if hasattr(self.router.classifier.embedder, "aembed"):
                    prompt_vector = await self.router.classifier.embedder.aembed(prompt)
                else:
                    prompt_vector = self.router.classifier.embedder.embed(prompt)

                for cat_name, anchor_vectors in self.router.classifier._anchor_embeddings.items():
                    anchors = self.router.classifier.categories[cat_name].get(
                        "semantic_anchors", []
                    )
                    for anchor_text, anchor_vector in zip(anchors, anchor_vectors, strict=True):
                        sim = cosine_similarity(prompt_vector, anchor_vector)
                        if sim >= self.router.classifier.semantic_threshold:
                            detection_traces.append(
                                {
                                    "category": cat_name,
                                    "type": "semantic_match",
                                    "matched_trigger": anchor_text,
                                    "similarity_score": sim,
                                    "threshold": self.router.classifier.semantic_threshold,
                                    "details": f"Similarity ({sim:.4f}) matched anchor '{anchor_text}' >= threshold ({self.router.classifier.semantic_threshold}).",
                                }
                            )
            except (ValueError, TypeError, OSError, KeyError) as e:
                detection_traces.append({"error": f"Semantic trace exception: {e}"})

        # 2. Trace declarative rules mapping
        tier_policy = self.router.routing_policy["tiers"].get(user_tier)
        if not tier_policy:
            tier_policy = self.router.routing_policy["tiers"][
                self.router.routing_policy["default_tier"]
            ]
            policy_tier_used = self.router.routing_policy["default_tier"]
        else:
            policy_tier_used = user_tier

        applied_rule = None
        if recorded_sensitivity:
            for rule in tier_policy.get("rules", []):
                if rule["match_category"] in recorded_sensitivity:
                    applied_rule = {
                        "rule_type": "tier_routing_rule",
                        "category": rule["match_category"],
                        "assigned_model": rule["assigned_model"],
                        "retention_required": rule.get("retention_required", False),
                    }
                    break
            if not applied_rule:
                applied_rule = {
                    "rule_type": "restricted_fallback",
                    "assigned_model": tier_policy.get(
                        "restricted_fallback_model", "Opus-4.8-Fallback"
                    ),
                    "retention_required": tier_policy.get("retention_for_restricted", False),
                }
        else:
            applied_rule = {
                "rule_type": "default_safe_rule",
                "assigned_model": tier_policy.get("default_model", "Fable-5-Core"),
                "retention_required": False,
            }

        replay_consistent = (
            assigned_model == applied_rule["assigned_model"]
            and bool(retention_flag) == applied_rule["retention_required"]
        )

        return {
            "routing_id": routing_id,
            "timestamp": timestamp,
            "prompt_hash": prompt_hash,
            "user_tier": user_tier,
            "policy_tier_used": policy_tier_used,
            "recorded_assigned_model": assigned_model,
            "recorded_retention_flag": retention_flag,
            "detected_sensitivity": recorded_sensitivity,
            "applied_rule": applied_rule,
            "detection_traces": detection_traces,
            "replay_consistent": replay_consistent,
            "versions": {
                "classifier": classifier_ver,
                "policy": routing_policy_ver,
            },
        }
