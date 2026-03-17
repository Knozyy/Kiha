"""Kiha Server — Ollama Vision Service.

Locally running vision LLM (LLaVA / llama3.2-vision) via Ollama.
No API key required — fully offline.

Kurulum (Ubuntu):
    curl -fsSL https://ollama.com/install.sh | sh
    ollama pull llava:7b

Ortam değişkenleri (.env):
    OLLAMA_URL=http://localhost:11434   (varsayılan)
    OLLAMA_MODEL=llava:7b               (varsayılan)
"""

import base64
import logging

import httpx

logger = logging.getLogger(__name__)

DEFAULT_URL   = "http://localhost:11434"
DEFAULT_MODEL = "llava:7b"

SYSTEM_PROMPT = (
    "Sen Kiha Vision AI asistanısın. "
    "Akıllı gözlüklerden gelen görüntüleri analiz ediyorsun. "
    "Her zaman Türkçe yanıt ver. "
    "Kısa ve net ol (1-3 cümle). "
    "Renk, konum ve çevredeki nesneleri belirt. "
    "Görmediğin şeyleri uydurmak yerine 'görüntüde tespit edilemedi' de."
)


class OllamaVisionService:
    """Ollama tabanlı yerel vision LLM servisi.

    Ollama'nın /api/generate endpoint'ini kullanır.
    LLaVA veya llama3.2-vision modeliyle çalışır.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_URL,
        timeout: float = 60.0,
    ) -> None:
        self.model    = model
        self.base_url = base_url.rstrip("/")
        self.timeout  = timeout
        logger.error("OllamaVisionService başlatıldı: %s @ %s", model, base_url)

    async def ask_about_image(
        self,
        image_bytes: bytes,
        question: str,
    ) -> str:
        """Görüntü hakkında Türkçe soru sor, Türkçe yanıt al."""
        if not image_bytes:
            return "❌ Görüntü verisi boş."

        image_b64 = base64.b64encode(image_bytes).decode()
        full_prompt = f"{SYSTEM_PROMPT}\n\nSoru: {question}"

        payload = {
            "model":  self.model,
            "prompt": full_prompt,
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 200,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                answer = data.get("response", "").strip()
                if not answer:
                    return "Yanıt alınamadı."
                logger.error("Ollama VQA: '%s' → '%s'", question[:50], answer[:80])
                return answer

        except httpx.ConnectError:
            msg = (
                f"❌ Ollama'ya bağlanılamadı ({self.base_url}). "
                "Ollama çalışıyor mu? 'ollama serve' komutunu deneyin."
            )
            logger.error(msg)
            return msg
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                msg = (
                    f"❌ Model '{self.model}' bulunamadı. "
                    f"'ollama pull {self.model}' ile indirin."
                )
            else:
                msg = f"❌ Ollama HTTP hatası: {e.response.status_code}"
            logger.error(msg)
            return msg
        except Exception as exc:
            msg = f"❌ Ollama hatası: {type(exc).__name__}: {exc}"
            logger.error(msg)
            return msg

    async def describe_scene(self, image_bytes: bytes) -> str:
        """Sahneyi kısaca Türkçe açıkla."""
        return await self.ask_about_image(
            image_bytes=image_bytes,
            question=(
                "Bu görüntüdeki sahneyi kısaca açıkla. "
                "Nesneleri, renkleri, ortamı ve önemli detayları belirt."
            ),
        )

    async def check_object_state(
        self,
        image_bytes: bytes,
        object_name: str,
    ) -> str:
        """Belirli bir nesnenin durumunu kontrol et."""
        return await self.ask_about_image(
            image_bytes=image_bytes,
            question=(
                f"Görüntüde '{object_name}' var mı? "
                f"Varsa konumunu, rengini ve durumunu belirt."
            ),
        )

    async def ping(self) -> bool:
        """Ollama çalışıyor mu kontrol et."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
