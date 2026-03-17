"""Kiha Server — Local Vision Language Model (Moondream2).

Integrates vikhyatk/moondream2 for local, offline Visual Question Answering.
Runs fully locally on CPU or GPU without needing any API keys.

YOLO → Object Detection
Moondream2 → Visual Question Answering (VQA)
"""

import logging
from typing import Protocol

import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoTokenizer

from infrastructure.ai.gemini_vision import VisionServiceProtocol

logger = logging.getLogger(__name__)

# Model definition
MOONDREAM_MODEL_ID = "vikhyatk/moondream2"
MOONDREAM_REVISION = "2024-08-26"


class MoondreamVisionService:
    """Local VLM logic using Moondream2.

    Initializes the model in memory. Target device is auto-detected
    (uses CUDA if available via PyTorch, otherwise CPU).
    Implements VisionServiceProtocol.
    """

    def __init__(self, device: str | None = None) -> None:
        """Initialize Moondream2 model.

        Args:
            device: 'cuda', 'cpu', 'mps'. If None, detects automatically.
        """
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Initializing Moondream2 on device: {self.device}...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            MOONDREAM_MODEL_ID,
            revision=MOONDREAM_REVISION,
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            MOONDREAM_MODEL_ID,
            revision=MOONDREAM_REVISION,
            trust_remote_code=True,
            attn_implementation="flash_attention_2" if self.device == "cuda" else None,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
        ).to(device=self.device)

        # Optimization for inference
        self.model.eval()
        logger.info("Moondream2 initialization complete.")

    async def ask_about_image(
        self,
        image_bytes: bytes,
        question: str,
    ) -> str:
        """Ask a question about an image using Moondream2.

        Takes mostly English queries for optimal performance,
        but we can try Turkish or use translation.
        """
        if not image_bytes:
            return "❌ Görüntü verisi boş."

        from io import BytesIO
        try:
            pil_image = Image.open(BytesIO(image_bytes))

            # Add context for Turkish responses
            # Moondream is English-native, so we force it to answer in Turkish with a prompt prefix.
            augmented_question = f"Answer in Turkish only. {question}"
            
            import asyncio
            # Run inference in a threadpool to not block the asyncio event loop
            answer = await asyncio.to_thread(
                self._run_inference_sync,
                pil_image,
                augmented_question,
            )

            logger.error(
                "Moondream VQA: Q='%s' → A='%s'",
                question[:50],
                answer[:80],
            )
            return answer

        except Exception as err:
            error_msg = f"Moondream inference hatası: {type(err).__name__}: {err}"
            logger.error(error_msg)
            return f"❌ {error_msg}"

    def _run_inference_sync(self, image: Image.Image, question: str) -> str:
        """Sync inference function to run via to_thread."""
        with torch.no_grad():
            enc_image = self.model.encode_image(image)
            answer = self.model.answer_question(enc_image, question, self.tokenizer)
        return answer

    async def describe_scene(self, image_bytes: bytes) -> str:
        """Get a concise description of the scene."""
        return await self.ask_about_image(
            image_bytes=image_bytes,
            question="Describe this image in detail.",
        )

    async def check_object_state(
        self,
        image_bytes: bytes,
        object_name: str,
    ) -> str:
        """Check the state of a specific object."""
        return await self.ask_about_image(
            image_bytes=image_bytes,
            question=f"Where is the {object_name} and what is its state?",
        )

# Type verification
_service: VisionServiceProtocol = MoondreamVisionService(device="cpu")
