"""
Domain Convenience Functions
"""

from cortex.extensions.nexus.model import NexusWorldModel
from cortex.extensions.nexus.types import (
    _INTENT_PRIORITY,
    DomainOrigin,
    IntentType,
    Priority,
    WorldMutation,
)


async def mailtv_intercepted(
    nexus: NexusWorldModel,
    sender: str,
    subject: str,
    confidence: float,
    action: str,
    cortex_hits: int = 0,
) -> bool:
    """Called by MailTV daemon when an email is intercepted."""
    return await nexus.mutate(
        WorldMutation(
            origin=DomainOrigin.MAILTV,
            intent=IntentType.EMAIL_INTERCEPTED,
            project="mailtv",
            confidence=confidence / 100.0 if confidence > 1.0 else confidence,
            priority=_INTENT_PRIORITY[IntentType.EMAIL_INTERCEPTED],
            payload={
                "sender": sender,
                "subject": subject,
                "action": action,
                "cortex_hits": cortex_hits,
                "summary": f"Email from {sender}: '{subject}' → {action}",
            },
        )
    )


async def moltbook_post_published(
    nexus: NexusWorldModel,
    agent_name: str,
    submolt: str,
    title: str,
    karma_before: float = 0.0,
) -> bool:
    """Called by Moltbook Orchestrator when a post is published."""
    return await nexus.mutate(
        WorldMutation(
            origin=DomainOrigin.MOLTBOOK,
            intent=IntentType.POST_PUBLISHED,
            project="moltbook",
            priority=_INTENT_PRIORITY[IntentType.POST_PUBLISHED],
            payload={
                "agent": agent_name,
                "submolt": submolt,
                "title": title,
                "karma_before": karma_before,
                "summary": f"Agent {agent_name} published '{title}' in s/{submolt}",
            },
        )
    )


async def moltbook_karma_laundered(
    nexus: NexusWorldModel,
    flagship: str,
    burners_used: int,
    post_id: str,
) -> bool:
    """Called after a karma laundering cycle completes."""
    return await nexus.mutate(
        WorldMutation(
            origin=DomainOrigin.MOLTBOOK,
            intent=IntentType.KARMA_LAUNDERED,
            project="moltbook",
            priority=_INTENT_PRIORITY[IntentType.KARMA_LAUNDERED],
            payload={
                "flagship": flagship,
                "burners_used": burners_used,
                "post_id": post_id,
                "summary": f"Karma laundered: {burners_used} burners → post {post_id}",
            },
        )
    )


async def moltbook_shadowban_alert(
    nexus: NexusWorldModel,
    agent_name: str,
    evidence: str,
) -> bool:
    """Called when shadowban detection triggers. CRITICAL priority."""
    return await nexus.mutate(
        WorldMutation(
            origin=DomainOrigin.MOLTBOOK,
            intent=IntentType.SHADOWBAN_DETECTED,
            project="moltbook",
            confidence=0.5,
            priority=Priority.CRITICAL,
            payload={
                "agent": agent_name,
                "evidence": evidence,
                "summary": f"⚠️ SHADOWBAN suspected on {agent_name}: {evidence}",
            },
        )
    )


async def sap_anomaly_detected(
    nexus: NexusWorldModel,
    module: str,
    severity: str,
    description: str,
) -> bool:
    """Called by SAP Audit engine. CRITICAL priority."""
    return await nexus.mutate(
        WorldMutation(
            origin=DomainOrigin.SAP_AUDIT,
            intent=IntentType.ANOMALY_DETECTED,
            project="sap-audit",
            confidence=0.9,
            priority=Priority.CRITICAL,
            payload={
                "module": module,
                "severity": severity,
                "description": description,
                "summary": f"SAP anomaly [{severity}] in {module}: {description}",
            },
        )
    )
