"""Kiha Server — AI Pipeline Demo Script.

Tests the complete image processing pipeline:
    Image file → YOLO Inference → SceneMemory → Query → Turkish Response

Usage:
    python scripts/demo_pipeline.py
    python scripts/demo_pipeline.py --image path/to/image.jpg
    python scripts/demo_pipeline.py --webcam
"""

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
import numpy as np

from domain.models.base import Frame
from infrastructure.ai.inference_engine import YoloInferenceEngine
from infrastructure.ai.scene_memory import SceneMemory
from infrastructure.ai.query_parser import QueryParser
from infrastructure.ai.frame_search_service import FrameSearchService

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("demo")


# ═══════════════════════════════════════════════════
# ANSI Colors for terminal output
# ═══════════════════════════════════════════════════
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_header() -> None:
    """Print Kiha demo header."""
    print(f"\n{GREEN}{BOLD}")
    print("  ╔══════════════════════════════════════════╗")
    print("  ║     🔬 Kiha AI Pipeline — Demo           ║")
    print("  ║     YOLOv8 + SceneMemory + QueryParser  ║")
    print("  ╚══════════════════════════════════════════╝")
    print(f"{RESET}\n")


def print_detections(detections: list[object]) -> None:
    """Print detection results in a formatted table."""
    if not detections:
        print(f"  {DIM}Hiçbir nesne tespit edilmedi.{RESET}")
        return

    print(f"  {CYAN}{BOLD}{'Nesne':<20} {'Güven':>8} {'Konum':>12}{RESET}")
    print(f"  {'─' * 42}")

    for det in detections:
        label = getattr(det, "label", "?")
        confidence = getattr(det, "confidence", 0.0)
        bbox = getattr(det, "bbox", None)

        conf_str = f"%{int(confidence * 100)}"
        conf_color = GREEN if confidence > 0.7 else (YELLOW if confidence > 0.4 else RED)

        if bbox:
            x_center = (bbox.x_min + bbox.x_max) / 2
            y_center = (bbox.y_min + bbox.y_max) / 2
            pos_str = f"({x_center:.2f}, {y_center:.2f})"
        else:
            pos_str = "(?)"

        print(f"  {label:<20} {conf_color}{conf_str:>8}{RESET} {DIM}{pos_str:>12}{RESET}")


def create_test_frame_from_image(image_path: str, frame_id: int = 1) -> Frame:
    """Load an image file and create a Frame object."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    height, width = image.shape[:2]

    # Encode to JPEG bytes
    success, jpeg_bytes = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not success:
        raise ValueError("Failed to encode image to JPEG")

    return Frame(
        frame_id=frame_id,
        timestamp=datetime.now(),
        device_id="demo-device",
        data=jpeg_bytes.tobytes(),
        width=width,
        height=height,
    )


def create_test_frame_from_webcam(frame_id: int = 1) -> Frame | None:
    """Capture a single frame from webcam."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(f"  {RED}Webcam açılamadı!{RESET}")
        return None

    ret, image = cap.read()
    cap.release()

    if not ret or image is None:
        print(f"  {RED}Webcam'den kare alınamadı!{RESET}")
        return None

    height, width = image.shape[:2]
    success, jpeg_bytes = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not success:
        return None

    return Frame(
        frame_id=frame_id,
        timestamp=datetime.now(),
        device_id="demo-device",
        data=jpeg_bytes.tobytes(),
        width=width,
        height=height,
    )


def create_synthetic_test_frame(frame_id: int = 1) -> Frame:
    """Create a synthetic test frame with solid color (for testing without image).

    YOLO won't detect anything on a solid color, but
    this validates the pipeline flow.
    """
    # Create a 640x480 gradient image
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    image[:, :, 0] = np.linspace(0, 100, 640, dtype=np.uint8)  # Blue gradient
    image[:, :, 1] = np.linspace(50, 150, 480, dtype=np.uint8).reshape(-1, 1)  # Green
    image[:, :, 2] = 80  # Red constant

    # Add some text
    cv2.putText(
        image,
        "Kiha Test Frame",
        (150, 250),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (0, 230, 111),
        3,
    )

    success, jpeg_bytes = cv2.imencode(".jpg", image)
    if not success:
        raise ValueError("Synthetic frame encoding failed")

    return Frame(
        frame_id=frame_id,
        timestamp=datetime.now(),
        device_id="demo-device",
        data=jpeg_bytes.tobytes(),
        width=640,
        height=480,
    )


async def run_demo(image_path: str | None = None, use_webcam: bool = False) -> None:
    """Run the complete AI pipeline demo."""
    print_header()

    # ─── Step 1: Initialize components ───
    print(f"  {CYAN}[1/5] Bileşenler yükleniyor...{RESET}")

    engine = YoloInferenceEngine(
        model_path="yolov8n.pt",
        device="cpu",
        confidence_threshold=0.25,
    )

    scene_memory = SceneMemory()
    query_parser = QueryParser()
    search_service = FrameSearchService(
        scene_memory=scene_memory,
        query_parser=query_parser,
    )

    print(f"  {GREEN}✓ YoloInferenceEngine hazır{RESET}")
    print(f"  {GREEN}✓ SceneMemory hazır{RESET}")
    print(f"  {GREEN}✓ QueryParser hazır ({len(query_parser._word_index)} kelime){RESET}")
    print(f"  {GREEN}✓ FrameSearchService hazır{RESET}")

    # ─── Step 2: Load/create test frame ───
    print(f"\n  {CYAN}[2/5] Test frame hazırlanıyor...{RESET}")

    if image_path:
        frame = create_test_frame_from_image(image_path)
        print(f"  {GREEN}✓ Görüntü yüklendi: {image_path}{RESET}")
    elif use_webcam:
        frame = create_test_frame_from_webcam()
        if frame is None:
            print(f"  {YELLOW}Webcam kullanılamadı, sentetik frame oluşturuluyor...{RESET}")
            frame = create_synthetic_test_frame()
        else:
            print(f"  {GREEN}✓ Webcam karesi alındı{RESET}")
    else:
        frame = create_synthetic_test_frame()
        print(f"  {YELLOW}Sentetik test frame oluşturuldu (gerçek görüntü için --image kullanın){RESET}")

    print(f"  {DIM}Frame: {frame.width}x{frame.height}, "
          f"{len(frame.data)} bytes, ID={frame.frame_id}{RESET}")

    # ─── Step 3: Run YOLO inference ───
    print(f"\n  {CYAN}[3/5] YOLOv8 inference çalıştırılıyor...{RESET}")

    start = time.perf_counter()
    engine.load_model()
    load_time = (time.perf_counter() - start) * 1000
    print(f"  {DIM}Model yüklenme süresi: {load_time:.0f}ms{RESET}")

    result = await engine.run_inference(frame)
    print(f"  {GREEN}✓ Inference tamamlandı: {result.inference_time_ms:.1f}ms{RESET}")
    print(f"  {GREEN}✓ {len(result.detections)} nesne tespit edildi{RESET}")
    print()
    print_detections(result.detections)

    # ─── Step 4: Store in SceneMemory ───
    print(f"\n  {CYAN}[4/5] SceneMemory'ye kaydediliyor...{RESET}")

    added = scene_memory.add_inference_result(
        device_id="demo-device",
        result=result,
    )
    print(f"  {GREEN}✓ {added} kayıt eklendi{RESET}")

    all_objects = scene_memory.get_all_objects("demo-device")
    if all_objects:
        print(f"  {DIM}Hafızadaki nesneler: {', '.join(all_objects)}{RESET}")

    # ─── Step 5: Test queries ───
    print(f"\n  {CYAN}[5/5] Sorgu testleri çalıştırılıyor...{RESET}\n")

    test_queries = [
        "Anahtarlarımı nereye koydum?",
        "Ocağın altını kapattım mı?",
        "Telefonumu en son nerede gördüm?",
        "Arabamı nereye park ettim?",
    ]

    for query in test_queries:
        parsed = query_parser.parse(query)
        response = search_service.generate_response_text(
            query=query,
            device_id="demo-device",
        )

        print(f"  {BOLD}Q: {query}{RESET}")
        print(f"  {DIM}   Eşleşen label'lar: {parsed.target_labels}{RESET}")
        print(f"  {DIM}   Sorgu tipi: {parsed.query_type}{RESET}")
        print(f"  {GREEN}A: {response}{RESET}")
        print()

    # ─── Summary ───
    print(f"  {GREEN}{BOLD}{'═' * 42}{RESET}")
    summary = scene_memory.get_object_summary("demo-device")
    print(f"  {BOLD}Özet:{RESET}")
    print(f"  {DIM}Toplam kayıt: {scene_memory.total_records}{RESET}")
    if summary:
        for obj, count in summary.items():
            print(f"    • {obj}: {count} tespit")
    print(f"\n  {GREEN}{BOLD}Demo tamamlandı! ✓{RESET}\n")


def main() -> None:
    """Entry point for the demo script."""
    parser = argparse.ArgumentParser(
        description="Kiha AI Pipeline Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
    python scripts/demo_pipeline.py                         # Sentetik frame ile test
    python scripts/demo_pipeline.py --image photo.jpg       # Gerçek görüntü ile test
    python scripts/demo_pipeline.py --webcam                # Webcam ile test
        """,
    )
    parser.add_argument(
        "--image",
        type=str,
        help="Test edilecek görüntü dosyasının yolu",
    )
    parser.add_argument(
        "--webcam",
        action="store_true",
        help="Webcam'den kare yakala ve test et",
    )

    args = parser.parse_args()
    asyncio.run(run_demo(image_path=args.image, use_webcam=args.webcam))


if __name__ == "__main__":
    main()
