"""Kiha Server — 30 Saniye Webcam Testi.

Webcam'den 30 saniye boyunca kare yakalar,
her kareyi YOLOv8 ile analiz eder ve SceneMemory'ye kaydeder.
Sonunda Türkçe sorgularla sonuçları test eder.

Kullanım:
    python scripts/webcam_test.py
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2

from domain.models.base import Frame
from infrastructure.ai.inference_engine import YoloInferenceEngine
from infrastructure.ai.scene_memory import SceneMemory
from infrastructure.ai.query_parser import QueryParser
from infrastructure.ai.frame_search_service import FrameSearchService


# ─── Terminal renkleri ───
G = "\033[92m"   # Green
C = "\033[96m"   # Cyan
Y = "\033[93m"   # Yellow
R = "\033[91m"   # Red
B = "\033[1m"    # Bold
D = "\033[2m"    # Dim
X = "\033[0m"    # Reset

RECORD_DURATION = 30        # saniye
PROCESS_INTERVAL_SEC = 1.0  # her 1 saniyede bir kare analiz et


async def main() -> None:
    print(f"\n{G}{B}")
    print("  ╔═══════════════════════════════════════════╗")
    print("  ║  🎥  Kiha — 30 Saniye Webcam Testi        ║")
    print("  ║  YOLOv8 + SceneMemory + Sorgu Testi       ║")
    print("  ╚═══════════════════════════════════════════╝")
    print(f"{X}\n")

    # ── 1. Bileşenleri yükle ──
    print(f"  {C}[1/4] Bileşenler yükleniyor...{X}")
    engine = YoloInferenceEngine(
        model_path="yolov8n.pt",
        device="cpu",
        confidence_threshold=0.30,
    )
    engine.load_model()
    scene_memory = SceneMemory()
    query_parser = QueryParser()
    search_service = FrameSearchService(scene_memory=scene_memory, query_parser=query_parser)
    print(f"  {G}✓ Tüm bileşenler hazır{X}\n")

    # ── 2. Webcam aç ──
    print(f"  {C}[2/4] Webcam açılıyor...{X}")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(f"  {R}✗ Webcam açılamadı! Lütfen kameranızı kontrol edin.{X}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    print(f"  {G}✓ Webcam açıldı: {width}x{height} @ {fps}fps{X}\n")

    # ── 3. 30 saniyelik kayıt + analiz ──
    print(f"  {C}[3/4] {RECORD_DURATION} saniye kayıt + analiz başlıyor...{X}")
    print(f"  {D}  (Her ~{PROCESS_INTERVAL_SEC}s'de bir kare analiz edilecek){X}\n")

    frame_id = 0
    processed_count = 0
    all_detections: dict[str, int] = {}
    start_time = time.time()
    last_process_time = 0.0

    while True:
        elapsed = time.time() - start_time
        if elapsed >= RECORD_DURATION:
            break

        ret, img = cap.read()
        if not ret:
            break

        frame_id += 1
        remaining = RECORD_DURATION - elapsed

        # Her PROCESS_INTERVAL_SEC saniyede bir kare analiz et
        if elapsed - last_process_time >= PROCESS_INTERVAL_SEC:
            last_process_time = elapsed

            # JPEG encode
            ok, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ok:
                continue

            frame = Frame(
                frame_id=frame_id,
                timestamp=datetime.now(),
                device_id="webcam-test",
                data=jpeg.tobytes(),
                width=width,
                height=height,
            )

            # YOLO inference
            result = await engine.run_inference(frame)
            processed_count += 1

            # SceneMemory'ye kaydet
            scene_memory.add_inference_result(device_id="webcam-test", result=result)

            # Tespit edilen nesneleri topla
            for det in result.detections:
                label = det.label
                all_detections[label] = all_detections.get(label, 0) + 1

            # Terminal çıktısı
            det_names = [f"{d.label}({int(d.confidence*100)}%)" for d in result.detections]
            det_str = ", ".join(det_names) if det_names else "—"
            bar_len = int((elapsed / RECORD_DURATION) * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(
                f"\r  [{bar}] {elapsed:4.0f}s/{RECORD_DURATION}s | "
                f"Kare #{processed_count:3d} | "
                f"{result.inference_time_ms:5.0f}ms | "
                f"{det_str[:60]:<60}",
                end="",
                flush=True,
            )

    cap.release()
    total_elapsed = time.time() - start_time
    print(f"\n\n  {G}✓ Kayıt tamamlandı: {total_elapsed:.1f}s, {processed_count} kare analiz edildi{X}\n")

    # ── 4. Sonuçları raporla ve sorgula ──
    print(f"  {C}[4/4] Sonuçlar ve sorgu testleri{X}\n")

    # Tespit edilen nesneler tablosu
    if all_detections:
        print(f"  {B}Tespit Edilen Nesneler:{X}")
        print(f"  {'─' * 36}")
        sorted_dets = sorted(all_detections.items(), key=lambda x: x[1], reverse=True)
        for label, count in sorted_dets:
            bar = "▓" * min(count, 30)
            print(f"  {label:<20} {count:>4}x {D}{bar}{X}")
        print()
    else:
        print(f"  {Y}Hiçbir nesne tespit edilmedi.{X}\n")

    # Sorgu testleri
    print(f"  {B}Sorgu Testleri:{X}")
    print(f"  {'─' * 50}\n")

    test_queries = [
        "Anahtarlarımı nereye koydum?",
        "Ocağın altını kapattım mı?",
        "Telefonumu en son nerede gördüm?",
        "Arabamı nereye park ettim?",
        "Kediyi en son ne zaman gördüm?",
        "Bilgisayarım nerede?",
    ]

    for q in test_queries:
        parsed = query_parser.parse(q)
        response = search_service.generate_response_text(query=q, device_id="webcam-test")
        found = "🟢" if "bulunamadı" not in response and "❌" not in response else "🔴"
        print(f"  {found} {B}S:{X} {q}")
        print(f"     {D}Labels: {parsed.target_labels} | Tip: {parsed.query_type}{X}")
        print(f"     {G}C: {response}{X}\n")

    # Özet
    summary = scene_memory.get_object_summary("webcam-test")
    print(f"  {G}{B}{'═' * 50}{X}")
    print(f"  {B}📊 Genel Özet:{X}")
    print(f"     Toplam analiz edilen kare: {processed_count}")
    print(f"     Toplam tespit sayısı: {scene_memory.total_records}")
    print(f"     Benzersiz nesne türü: {len(summary)}")
    print(f"     Ortalama inference: ~{(total_elapsed / max(processed_count, 1) * 1000):.0f}ms/kare")
    print(f"\n  {G}{B}Test tamamlandı! ✓{X}\n")


if __name__ == "__main__":
    asyncio.run(main())
