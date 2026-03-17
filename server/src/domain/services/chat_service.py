"""Kiha Server — Chat Service.

Core business logic for the AI chat interface.
Users ask questions about recorded footage and the service
searches through stored inference results to provide contextual answers.
"""

from typing import Protocol

from domain.models.base import ChatMessage, ChatSession


class ChatRepositoryProtocol(Protocol):
    """Interface for chat data persistence."""

    async def get_session(self, session_id: str) -> ChatSession | None:
        """Retrieve a chat session by ID."""
        ...

    async def save_session(self, session: ChatSession) -> None:
        """Persist a chat session."""
        ...

    async def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Add a message to an existing session."""
        ...


class FrameSearchProtocol(Protocol):
    """Interface for searching through recorded frames."""

    async def search_frames(
        self,
        device_id: str,
        query: str,
    ) -> list[int]:
        """Search recorded frames by natural language query.

        Returns a list of matching frame IDs.
        """
        ...


class ResponseGeneratorProtocol(Protocol):
    """Interface for generating Turkish natural language responses."""

    def generate_response_text(
        self,
        query: str,
        device_id: str,
    ) -> str:
        """Generate a response for a user query."""
        ...


class ChatService:
    """Core business logic for the AI chat interface.

    Users ask questions about recorded footage (e.g., 'Where did I put
    my keys?') and the service searches through stored inference results
    to provide contextual answers.
    """

    def __init__(
        self,
        chat_repository: ChatRepositoryProtocol,
        frame_search: FrameSearchProtocol,
        response_generator: ResponseGeneratorProtocol | None = None,
    ) -> None:
        self._chat_repository = chat_repository
        self._frame_search = frame_search
        self._response_generator = response_generator

    async def process_question(
        self,
        session_id: str,
        device_id: str,
        question: str,
    ) -> ChatMessage:
        """Process a user question about recorded footage.

        1. Search stored frames for relevant detections
        2. Generate a contextual AI response (Turkish)
        3. Persist the conversation
        """
        # Search recorded frames for relevant content
        matching_frame_ids = await self._frame_search.search_frames(
            device_id=device_id,
            query=question,
        )

        # Generate response using the response generator if available
        if self._response_generator:
            response_content = self._response_generator.generate_response_text(
                query=question,
                device_id=device_id,
            )
        else:
            response_content = self._build_fallback_response(
                question,
                matching_frame_ids,
            )

        confidence = 0.85 if matching_frame_ids else 0.2

        response = ChatMessage(
            id=f"msg_{session_id}_{len(matching_frame_ids)}",
            role="assistant",
            content=response_content,
            referenced_frames=matching_frame_ids,
            confidence=confidence,
        )

        await self._chat_repository.add_message(session_id, response)
        return response

    @staticmethod
    def _build_fallback_response(
        question: str,
        frame_ids: list[int],
    ) -> str:
        """Fallback response when no response generator is available."""
        if not frame_ids:
            return (
                "Kayıtlarda bu konuyla ilgili bir bilgi bulamadım. "
                "Gözlüğünüzün aktif olduğundan emin misiniz?"
            )

        return (
            f"Kayıtlarda {len(frame_ids)} ilgili kare buldum. "
            "Detaylı analiz sonuçları hazırlanıyor."
        )
