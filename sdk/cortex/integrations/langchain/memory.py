import logging


from langchain_core.chat_history import BaseChatMessageHistory  # pyright: ignore[reportMissingImports]
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict  # pyright: ignore[reportMissingImports]

# Attempt to import CortexClient; fallback gracefully if not installed
try:
    from cortex.client import CortexClient  # pyright: ignore[reportMissingImports]
except ImportError:
    CortexClient = None

logger = logging.getLogger(__name__)


class CortexChatMessageHistory(BaseChatMessageHistory):
    """
    Chat message history that stores history in the CORTEX-Persist memory layer.

    This enables O(1) memory retrieval and deterministic state across LangChain
    agents utilizing the ZeroCopyRingBuffer substrate.
    """

    def __init__(
        self,
        session_id: str,
        api_key: str = None,  # pyright: ignore[reportArgumentType]
        cortex_url: str = "http://localhost:8000",
    ):
        if CortexClient is None:
            raise ImportError(
                "Could not import cortex client. "
                "Please install it with `pip install cortex-persist`."
            )
        self.session_id = session_id
        self.client = CortexClient(api_key=api_key, base_url=cortex_url)

    @property
    def messages(self) -> list[BaseMessage]:
        """Retrieve the deterministic message sequence from Cortex."""
        try:
            raw_messages = self.client.get_memory(self.session_id)
            if not raw_messages:
                return []

            # Reconstruct LangChain BaseMessages from Cortex JSON payload
            return messages_from_dict(raw_messages)
        except Exception as e:
            logger.error(f"Error fetching from Cortex: {e}")
            return []

    def add_message(self, message: BaseMessage) -> None:
        """Append the message to the CORTEX state asynchronously."""
        try:
            message_dict = message_to_dict(message)
            # Utilizing Cortex's background thread/Rust substrate for zero-latency append
            self.client.store_memory(session_id=self.session_id, payload=message_dict)
        except Exception as e:
            logger.error(f"Error writing to Cortex: {e}")

    def clear(self) -> None:
        """Annihilate session memory from Cortex (Entropy Reset)."""
        self.client.clear_memory(self.session_id)
