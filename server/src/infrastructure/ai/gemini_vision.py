"""Kiha Server — Gemini Vision Service.

Integrates Google Gemini API for Visual Question Answering (VQA).
Complements YOLO object detection with rich, natural language
understanding of image content.

YOLO → "burada bir insan var"
Gemini VQA → "saçı kahverengi, mavi tişört giyiyor, elinde anahtar tutuyor"

Usage requires GEMINI_API_KEY environment variable.
"""

import base64
import logging
from typing import Protocol

try:
    from google import genai
    from google.genai import types
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False
    genai = None
    types = None

logger = logging.getLogger(__name__)

# System prompt for Kiha Vision AI
KIHA_SYSTEM_PROMPT = """Sen Kiha Vision AI asistanısın. Akıllı gözlüklerden gelen görüntüleri analiz ediyorsun.

Kurallar:
1. SADECE Türkçe yanıt ver.
2. TAM OLARAK 1 kısa cümle yaz, başka hiçbir şey ekleme.
3. Cümle şu kalıpla başlasın: "[Nesne adı] [konumu]."
   Örnek: "Anahtar kahverengi masanın üstünde duruyor."
   Örnek: "Kişi odanın sol köşesinde, beyaz duvarın önünde ayakta."
4. Renk, yüzey, yan yana olan nesneleri mutlaka belirt.
5. Eğer sorulan nesne görüntüde yoksa sadece şunu yaz: "Görüntüde tespit edilemedi."
6. Asla açıklama, başlık, madde işareti veya emoji ekleme."""


class VisionServiceProtocol(Protocol):
    """Interface for visual question answering services."""

    async def ask_about_image(
        self,
        image_bytes: bytes,
        question: str,
    ) -> str:
        """Ask a question about an image, return natural language answer."""
        ...


class GeminiVisionService:
    """Google Gemini API-based Visual Question Answering service.

    Sends image + question to Gemini and returns a Turkish
    natural language response.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.0-flash",
    ) -> None:
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY boş olamaz. "
                ".env dosyasında GEMINI_API_KEY tanımlayın."
            )

        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

        logger.error(
            "GeminiVisionService initialized (model: %s)",
            model_name,
        )

    async def ask_about_image(
        self,
        image_bytes: bytes,
        question: str,
    ) -> str:
        """Ask a question about an image using Gemini Vision.

        Args:
            image_bytes: JPEG-encoded image data
            question: User's question in Turkish

        Returns:
            Turkish natural language answer
        """
        if not image_bytes:
            return "❌ Görüntü verisi boş."

        try:
            # Build multimodal content
            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/jpeg",
            )

            response = self._client.models.generate_content(
                model=self._model_name,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            image_part,
                            types.Part.from_text(text=question),
                        ],
                    ),
                ],
                config=types.GenerateContentConfig(
                    system_instruction=KIHA_SYSTEM_PROMPT,
                    temperature=0.3,
                    max_output_tokens=256,
                ),
            )

            answer = response.text or "Yanıt oluşturulamadı."

            logger.error(
                "Gemini VQA: Q='%s' → A='%s'",
                question[:50],
                answer[:80],
            )

            return answer.strip()

        except Exception as err:
            error_msg = f"Gemini API hatası: {type(err).__name__}: {err}"
            logger.error(error_msg)
            return f"❌ {error_msg}"

    async def describe_scene(self, image_bytes: bytes) -> str:
        """Get a general description of the scene in the image."""
        return await self.ask_about_image(
            image_bytes=image_bytes,
            question=(
                "Bu görüntüdeki sahneyi kısaca açıkla. "
                "Nesneleri, insanları, ortamı ve önemli detayları belirt."
            ),
        )

    async def check_object_state(
        self,
        image_bytes: bytes,
        object_name: str,
    ) -> str:
        """Check state of a specific object (e.g., is the stove on?)."""
        return await self.ask_about_image(
            image_bytes=image_bytes,
            question=(
                f"Görüntüde '{object_name}' var mı? "
                f"Varsa durumunu (açık/kapalı, konumu, rengi vb.) belirt."
            ),
        )


# Protocol compliance
_service: VisionServiceProtocol
