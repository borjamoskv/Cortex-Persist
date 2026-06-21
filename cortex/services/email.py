# [C5-REAL] Exergy-Maximized
import logging

logger = logging.getLogger(__name__)


def send_reengagement_email(email: str, cluster: str) -> bool:
    """
    Mock implementation of email service.
    TODO: Integrate with Mailgun / SendGrid in C5-REAL mode.
    """
    logger.info("Enviando email de re-engagement a %s (Cluster: %s)", email, cluster)
    return True
