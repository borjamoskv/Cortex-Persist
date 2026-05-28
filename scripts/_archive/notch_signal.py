import json
import os
from datetime import datetime

RELAY_BUFFER = os.path.expanduser("~/.cortex/relay_buffer.jsonl")


def send_signal(stream, message, source="agent:gemini"):
    event = {
        "stream": stream,
        "source": source,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    with open(RELAY_BUFFER, "a") as f:
        f.write(json.dumps(event) + "\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python notch_signal.py <stream> <message>")
        sys.exit(1)

    send_signal(sys.argv[1], sys.argv[2])
