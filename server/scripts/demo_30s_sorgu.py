"""Kiha — 30 Saniye Kayıt + İnteraktif Sorgu Demo.

Kullanım:
    python scripts/demo_30s_sorgu.py              # webcam
    python scripts/demo_30s_sorgu.py --dosya v.mp4   # video dosyası
    python scripts/demo_30s_sorgu.py --sure 60       # 60 saniye kayıt

Gereksinimler:
    - YOLOv8:  pip install ultralytics
    - Ollama:  curl -fsSL https://ollama.com/install.sh | sh
               ollama pull llava:7b
    - .env'de OLLAMA_URL ve OLLAMA_MODEL (opsiyonel, varsayılanlar çalışır)
"""

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import cv2

from domain.models.base import Frame, InferenceResult
from infrastructure.ai.frame_search_service import FrameSearchService
from infrastructure.ai.inference_engine import YoloInferenceEngine
from infrastructure.ai.ollama_vision import OllamaVisionService
from infrastructure.ai.query_parser import QueryParser
from infrastructure.ai.scene_memory import SceneMemory

# ── Terminal renkleri ─────────────────────────────────────────────────────────
G = "\033[92m"
C = "\033[96m"
Y = "\033[93m"
R = "\033[91m"
B = "\033[1m"
D = "\033[2m"
X = "\033[0m"

DEVICE_ID  = "demo-gozluk"
FRAMES_DIR = Path(__file__).parent / "kayit_kareleri"


def _banner() -> None:
    print(f"\n{G}{B}")
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║  🎥  Kiha — 30s Kayıt + İnteraktif Sorgu Demo  ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print(f"{X}")


def _setup_dirs() -> None:
    FRAMES_DIR.mkdir(exist_ok=True)
    for f in FRAMES_DIR.glob("*.jpg"):
        f.unlink()


def _show_image(path: Path) -> None:
    if not path.exists():
        return
    img = cv2.imread(str(path))
    if img is None:
        return
    h, w = img.shape[:2]
    if max(h, w) > 900:
        scale = 900 / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    cv2.imshow("Kiha — Tespit Karesi  [kapat: herhangi bir tuş]", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def _context_labels(
    frame_id: int,
    target_label: str,
    inference_store: dict[int, InferenceResult],
) -> list[str]:
    """Aynı karede hedef dışındaki diğer nesneleri döndür."""
    result = inference_store.get(frame_id)
    if not result:
        return []
    return [d.label for d in result.detections if d.label != target_label]


def _fallback_response(
    target_label: str,
    frame_id: int,
    inference_store: dict[int, InferenceResult],
    timestamp: datetime,
    x_center: float,
    y_center: float,
) -> str:
    """VLM olmadığında bağlam nesnelerini kullanarak Türkçe yanıt üret."""
    zaman = timestamp.strftime("%H:%M:%S")

    # Pozisyon
    h = "solda" if x_center < 0.33 else ("sağda" if x_center > 0.66 else "ortada")
    v = "üstte" if y_center < 0.33 else ("altta" if y_center > 0.66 else "merkezde")

    # Aynı karedeki diğer nesneler
    others = _context_labels(frame_id, target_label, inference_store)

    base = f"🔍 '{target_label}' saat {zaman}'de görüntünün {v}, {h} kısmında tespit edildi."

    if others:
        yaninda = ", ".join(f"'{o}'" for o in others[:4])
        return f"{base} Yakınında: {yaninda}."
    return base


# ── Kayıt aşaması ─────────────────────────────────────────────────────────────
async def _record(
    source: int | str,
    duration: int,
) -> tuple[SceneMemory, dict[int, Path], dict[int, InferenceResult]]:
    print(f"  {C}[1/2] YOLOv8 yükleniyor...{X}")
    engine = YoloInferenceEngine(model_path="yolov8n.pt", device="cpu", confidence_threshold=0.30)
    engine.load_model()
    scene_memory = SceneMemory()
    print(f"  {G}✓ YOLOv8 hazır{X}\n")

    print(f"  {C}[2/2] {duration}s kayıt başlıyor...{X}")
    print(f"  {D}  Çıkmak için Ctrl+C{X}\n")

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"  {R}✗ Kaynak açılamadı: {source}{X}")
        sys.exit(1)

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))  or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

    frame_id        = 0
    processed       = 0
    start_time      = time.time()
    last_proc_time  = -999.0
    INTERVAL        = 0.5   # her 0.5s'de bir kare analiz et

    frame_paths: dict[int, Path]                = {}
    inference_store: dict[int, InferenceResult] = {}
    all_labels: dict[str, int]                  = {}

    try:
        while True:
            elapsed = time.time() - start_time
            if elapsed >= duration:
                break

            ret, img = cap.read()
            if not ret:
                break

            frame_id += 1
            if elapsed - last_proc_time < INTERVAL:
                continue
            last_proc_time = elapsed

            ok, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ok:
                continue

            frame = Frame(
                frame_id=frame_id,
                timestamp=datetime.now(),
                device_id=DEVICE_ID,
                data=jpeg.tobytes(),
                width=width,
                height=height,
            )

            result = await engine.run_inference(frame)
            processed += 1

            scene_memory.add_inference_result(DEVICE_ID, result)
            inference_store[frame_id] = result

            frame_path = FRAMES_DIR / f"frame_{frame_id:05d}.jpg"
            cv2.imwrite(str(frame_path), img)
            frame_paths[frame_id] = frame_path

            for det in result.detections:
                all_labels[det.label] = all_labels.get(det.label, 0) + 1

            # İlerleme çubuğu
            bar_n   = int((elapsed / duration) * 25)
            bar     = "█" * bar_n + "░" * (25 - bar_n)
            labels_ = [d.label for d in result.detections]
            det_str = ", ".join(labels_[:5]) if labels_ else "—"
            print(
                f"\r  [{bar}] {elapsed:4.0f}s  "
                f"kare #{processed:3d}  "
                f"{result.inference_time_ms:4.0f}ms  "
                f"{det_str:<40}",
                end="", flush=True,
            )

    except KeyboardInterrupt:
        print(f"\n  {Y}⚠ Durduruldu.{X}")
    finally:
        cap.release()

    elapsed_total = time.time() - start_time
    print(f"\n\n  {G}✓ Kayıt tamamlandı: {elapsed_total:.1f}s — {processed} kare{X}\n")

    if all_labels:
        print(f"  {B}Tespit Edilen Nesneler:{X}")
        for lbl, cnt in sorted(all_labels.items(), key=lambda x: -x[1]):
            print(f"    {lbl:<22} {cnt:>3}x  {D}{'▓' * min(cnt,30)}{X}")
        print()
    else:
        print(f"  {Y}Hiçbir nesne tespit edilmedi.{X}\n")

    return scene_memory, frame_paths, inference_store


# ── Soru-cevap döngüsü ────────────────────────────────────────────────────────
async def _interactive_loop(
    scene_memory: SceneMemory,
    frame_paths: dict[int, Path],
    inference_store: dict[int, InferenceResult],
) -> None:
    query_parser   = QueryParser()
    search_service = FrameSearchService(scene_memory=scene_memory, query_parser=query_parser)
    loop           = asyncio.get_event_loop()

    # Ollama VLM kurulumu
    ollama_url   = os.environ.get("OLLAMA_URL",   "http://localhost:11434")
    ollama_model = os.environ.get("OLLAMA_MODEL", "llava:7b")
    vlm = OllamaVisionService(model=ollama_model, base_url=ollama_url)

    print(f"  {C}Ollama kontrol ediliyor ({ollama_url})...{X}")
    if await vlm.ping():
        print(f"  {G}✓ Ollama aktif — model: {ollama_model}{X}")
        print(f"  {D}  (model ilk sorguda yükleniyorsa biraz bekleyin){X}\n")
    else:
        print(
            f"  {Y}⚠ Ollama çalışmıyor veya ulaşılamıyor.{X}\n"
            f"  {D}  Yedek mod: koordinat + bağlam nesne yanıtları kullanılacak.{X}\n"
            f"  {D}  Ollama başlatmak için: ollama serve{X}\n"
        )
        vlm = None  # type: ignore[assignment]

    print(f"  {G}{B}══════════════════════════════════════════════════{X}")
    print(f"  {B}💬 İnteraktif Sorgu Modu{X}")
    print(f"  {D}  Örnekler:{X}")

    # Kayıtta ne gördüysek onu göster
    all_objects = scene_memory.get_all_objects(DEVICE_ID)
    if all_objects:
        ornekler = [f"'{o}' nerede?" for o in all_objects[:3]]
        for o in ornekler:
            print(f"    {D}• {o}{X}")
    print(f"  {D}  Çıkış: 'çıkış' veya Ctrl+C{X}")
    print(f"  {G}{B}══════════════════════════════════════════════════{X}\n")

    while True:
        try:
            soru = await loop.run_in_executor(None, lambda: input(f"  {B}Siz:{X} "))
        except (KeyboardInterrupt, EOFError):
            print(f"\n  {Y}Çıkış yapıldı.{X}")
            break

        soru = soru.strip()
        if not soru:
            continue
        if soru.lower() in ("çıkış", "cikis", "exit", "quit", "q"):
            print(f"\n  {Y}Çıkış yapıldı.{X}")
            break

        # ── Arama ──
        parsed = query_parser.parse(soru)
        result = search_service.search_with_context(DEVICE_ID, soru)

        if not parsed.target_labels:
            print(
                f"\n  {Y}Kiha:{X} Sorunuzdaki nesneyi tanıyamadım. "
                f"Şunları sormayı deneyin: {', '.join(f'{o}?' for o in all_objects[:3])}\n"
            )
            continue

        if not result.found:
            print(
                f"\n  {R}Kiha:{X} '{', '.join(parsed.target_labels)}' "
                f"bu kayıtta tespit edilmedi.\n"
            )
            continue

        sighting = result.last_sighting

        # ── VLM ile yanıt ──
        cevap = ""
        if vlm and sighting:
            frame_path = frame_paths.get(sighting.frame_id)
            if frame_path and frame_path.exists():
                try:
                    print(f"  {D}[Ollama analiz ediyor...]{X}", end="", flush=True)
                    image_bytes = frame_path.read_bytes()
                    vlm_cevap = await vlm.ask_about_image(
                        image_bytes=image_bytes,
                        question=(
                            f"Bu görüntüde '{sighting.label}' nesnesini bul. "
                            f"Tam konumunu, renkleri ve yakınındaki nesneleri "
                            f"Türkçe 1-2 cümleyle açıkla."
                        ),
                    )
                    print(f"\r  {' '*35}\r", end="")   # "analiz ediliyor" satırını temizle
                    zaman = sighting.timestamp.strftime("%H:%M:%S")
                    cevap = f"🔍 {vlm_cevap}\n     (Saat {zaman}, kare #{sighting.frame_id})"
                except Exception as e:
                    print(f"\r  {D}[VLM hatası: {e}]{X}")

        # VLM çalışmadıysa yedek yanıt
        if not cevap and sighting:
            cevap = _fallback_response(
                sighting.label, sighting.frame_id, inference_store,
                sighting.timestamp, sighting.x_center, sighting.y_center,
            )

        print(f"\n  {G}Kiha:{X} {cevap}\n")

        # ── Fotoğraf teklifi ──
        if sighting:
            frame_path = frame_paths.get(sighting.frame_id)
            if frame_path and frame_path.exists():
                try:
                    goster = await loop.run_in_executor(
                        None, lambda: input(f"  {D}Fotoğrafı görmek ister misiniz? [E/h]: {X}")
                    )
                except (KeyboardInterrupt, EOFError):
                    break
                if goster.strip().lower() in ("", "e", "evet", "y", "yes"):
                    _show_image(frame_path)
                print()


# ── Ana fonksiyon ─────────────────────────────────────────────────────────────
async def main(source: int | str, duration: int) -> None:
    _banner()
    _setup_dirs()

    scene_memory, frame_paths, inference_store = await _record(source, duration)

    if scene_memory.total_records == 0:
        print(f"  {Y}Hiç nesne tespit edilmedi — sorgu yapılacak kayıt yok.{X}\n")
        return

    await _interactive_loop(scene_memory, frame_paths, inference_store)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kiha 30s Demo")
    parser.add_argument("--dosya", type=str, default=None, help="Video/görüntü dosyası")
    parser.add_argument("--sure",  type=int, default=30,   help="Kayıt süresi (saniye)")
    args = parser.parse_args()

    kaynak: int | str = args.dosya if args.dosya else 0
    asyncio.run(main(source=kaynak, duration=args.sure))
