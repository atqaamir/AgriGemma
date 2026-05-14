from abc import ABC, abstractmethod
from typing import Iterator


class AIModelProvider(ABC):
    """
    Contract that every AI backend must satisfy.
    Swap Gemma for any other model by creating a new class that
    implements this interface and registering it in create_app().
    """

    @abstractmethod
    def complete(self, prompt: str) -> str:
        """
        Send a prompt to the model and return the raw text response.
        Raises on network / model error — callers handle the exception.
        """

    def stream_complete(self, prompt: str) -> Iterator[str]:
        """Yield response tokens one at a time. Default: single-chunk fallback."""
        yield self.complete(prompt)

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name used in logs."""
