"""Kiha Server — Moondream2 VLM Demo.

Tests the completely local Vision Language Model workflow.
Image → Moondream2 → Turkish Response structure.

Usage:
    python scripts/moondream_demo.py
    python scripts/moondream_demo.py --image path/to/image.jpg
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2
from infrastructure.ai.local_vlm import MoondreamVisionService


# Terminal Colors
C = "\033[96m"
G = "\033[92m"
Y = "\033[93m"
B = "\033[1m"
D = "\033[2m"
X = "\033[0m"


async def run_demo(image_path: str | None = None) -> None:
    print(f"\n{C}{B}")
    print("  ╔═══════════════════════════════════════════╗")
    print("  ║    🧠  Kiha — Moondream2 VLM Demo         ║")
    print("  ║    Tamamen Lokal Görsel Soru-Cevap        ║")
    print("  ╚═══════════════════════════════════════════╝")
    print(f"{X}\n")

    print(f"  {C}[1/3] Moondream2 Modeli Yükleniyor...{X}")
    print(f"  {D}  (İlk çalışmada model indirilebilir, lütfen bekleyin ~3.5GB){X}")
    start = time.perf_counter()
    
    # Initialize VLM
    vlm = MoondreamVisionService()
    load_ms = (time.perf_counter() - start) * 1000
    
    print(f"  {G}✓ Model yüklendi ({vlm.device} üzerinde) - {load_ms:.0f}ms{X}\n")

    print(f"  {C}[2/3] Görüntü Yükleniyor...{X}")
    if image_path:
        path = image_path
    else:
        path = "test_bus.jpg"
        if not Path(path).exists():
            import urllib.request
            print(f"  {D}  Örnek görüntü indiriliyor (bus.jpg)...{X}")
            urllib.request.urlretrieve("https://ultralytics.com/images/bus.jpg", path)

    img = cv2.imread(path)
    if img is None:
        print(f"  {Y}✗ Görüntü okunamadı: {path}{X}")
        return

    ok, jpeg = cv2.imencode(".jpg", img)
    image_bytes = jpeg.tobytes()
    print(f"  {G}✓ Görüntü yüklendi: {path} ({img.shape[1]}x{img.shape[0]}){X}\n")

    print(f"  {C}[3/3] Soru & Cevap Testi{X}\n")

    test_queries = [
        "Bu görüntüdeki olay ne, kısaca özetle.",
        "İnsanların üstündeki kıyafetler ne renk?",
        "Otobüsün rengi ne, üzerinde yazı var mı?",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"  {B}Soru {i}:{X} {query}")
        
        q_start = time.perf_counter()
        answer = await vlm.ask_about_image(image_bytes, query)
        q_ms = (time.perf_counter() - q_start) * 1000
        
        print(f"  {G}Cevap:{X} {answer}")
        print(f"  {D}  ({q_ms:.0f}ms){X}\n")

    print(f"  {G}{B}Demo tamamlandı! ✓{X}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kiha VLM Demo")
    parser.add_argument("--image", type=str, help="Test edilecek görüntü")
    args = parser.parse_args()

    asyncio.run(run_demo(args.image))
