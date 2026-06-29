from typing import Any, Optional

from pydantic import BaseModel, Field


class TextMessage(BaseModel):
    body: str

class WhatsAppTemplateLanguage(BaseModel):
    code: str

class WhatsAppTemplate(BaseModel):
    name: str
    language: WhatsAppTemplateLanguage
    components: Optional[list[dict[str, Any]]] = None

class WhatsAppMessage(BaseModel):
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str = Field(..., description="Message type: text, template, interactive, etc.")
    text: Optional[TextMessage] = None
    template: Optional[WhatsAppTemplate] = None
