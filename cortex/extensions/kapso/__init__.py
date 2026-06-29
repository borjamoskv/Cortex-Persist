"""
KAPSO Extension for CORTEX-Persist
Provides integration with Kapso WhatsApp API.
"""

from .gateway import KapsoGateway
from .types import TextMessage, WhatsAppMessage, WhatsAppTemplate

__all__ = [
    "KapsoGateway",
    "WhatsAppMessage",
    "WhatsAppTemplate",
    "TextMessage"
]
