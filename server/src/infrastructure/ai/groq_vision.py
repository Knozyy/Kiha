"""Kiha Server — Groq Vision Service.

Uses Groq's ultra-fast inference API with Llama 3.2 Vision model.
Free tier: 30 requests/minute, 14400 tokens/minute.
"""

import base64
import logging

import httpx

logger = logging.getLogger(__name__)

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


class GroqVisionService:
    """Groq API-based Visual Question Answering service."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "meta-llama/llama-4-scout-17b-16e-instruct",
    ) -> None:
        if not api_key:
            raise ValueError("GROQ_API_KEY boş olamaz.")

        self._api_key = api_key
        self._model_name = model_name
        self._client = httpx.AsyncClient(
            base_url="https://api.groq.com/openai/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
        logger.info("GroqVisionService initialized (model: %s)", model_name)

    async def ask_about_image(
        self,
        image_bytes: bytes,
        question: str,
    ) -> str:
        """Ask a question about an image using Groq Vision."""
        if not image_bytes:
            return "Görüntü verisi boş."

        b64_image = base64.b64encode(image_bytes).decode()

        try:
            # Vision models on Groq don't support system messages —
            # embed instructions in the user message instead.
            full_question = f"{KIHA_SYSTEM_PROMPT}\n\nSoru: {question}"

            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": self._model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{b64_image}",
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": full_question,
                                },
                            ],
                        },
                    ],
                    "temperature": 0.3,
                    "max_tokens": 256,
                },
            )

            if response.status_code != 200:
                body = response.text
                logger.error("Groq API %d: %s", response.status_code, body[:500])
                return f"❌ Groq API hatası ({response.status_code}): {body[:200]}"

            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            logger.info("Groq VQA: Q='%s' → A='%s'", question[:50], answer[:80])
            return answer.strip()

        except Exception as err:
            error_msg = f"Groq API hatası: {type(err).__name__}: {err}"
            logger.error(error_msg)
            return f"❌ {error_msg}"

    async def describe_scene(self, image_bytes: bytes) -> str:
        """Get a general description of the scene."""
        return await self.ask_about_image(
            image_bytes=image_bytes,
            question="Bu görüntüdeki sahneyi kısaca açıkla. Nesneleri, insanları ve ortamı belirt.",
        )
