"""Kiha Server — Ask Question Use Case."""

from domain.models.base import ChatMessage
from domain.services.chat_service import ChatService


class AskQuestionUseCase:
    """Orchestrates answering user questions about recorded footage.

    The user asks: 'Where did I put my keys?' and this use case
    searches through stored frame inference results to find the answer.
    """

    def __init__(self, chat_service: ChatService) -> None:
        self._chat_service = chat_service

    async def execute(
        self,
        session_id: str,
        device_id: str,
        question: str,
    ) -> ChatMessage:
        """Process a user question and return an AI response."""
        if not question.strip():
            from domain.exceptions import ChatSessionError
            raise ChatSessionError("Empty question is not allowed")

        return await self._chat_service.process_question(
            session_id=session_id,
            device_id=device_id,
            question=question,
        )
