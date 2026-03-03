from cortex.engine.membrane.models import PureEngram
from cortex.engine.membrane.sanitizer import SovereignSanitizer

raw = {
    "type": "decision",
    "source": "ghost",
    "topic": "testing",
    "content": "My email is user@example.com and phone is +34 600 000 000. Path is /Users/borjafernandezangulo/cortex",
    "metadata": {"test": True}
}

engram, log = SovereignSanitizer.digest(raw)
print(engram.json(indent=2))
