"""Kiha — Video Simülatörü.

Bir video dosyasını veya webcam'i frame'lere bölerek sunucuya gönderir.
Gözlüğün olmadığı durumlarda test için kullanılır.

Kullanım:
    # Video dosyasıyla
    python scripts/simulate_video.py --video ornek.mp4 --server http://82.26.94.210:8000

    # Webcam ile (canlı)
    python scripts/simulate_video.py --webcam --server http://82.26.94.210:8000

    # Sadece 30 saniye kaydet
    python scripts/simulate_video.py --webcam --duration 30 --server http://82.26.94.210:8000
"""

import argparse
import sys
import time
import urllib.request
from pathlib import Path

try:
    import cv2
except ImportError:
    print("Hata: opencv-python kurulu değil.")
    print("  pip install opencv-python")
    sys.exit(1)


def send_frame(server_url: str, device_id: str, jpeg_bytes: bytes) -> dict | None:
    """Bir JPEG frame'i sunucuya gönder."""
    url = f"{server_url}/api/v1/chat/frame/{device_id}"
    req = urllib.request.Request(
        url,
        data=jpeg_bytes,
        headers={"Content-Type": "image/jpeg"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            import json
            return json.loads(resp.read().decode())
    except Exception as err:
        print(f"  [!] Gönderim hatası: {err}")
        return None


def simulate(
    source: str | int,
    server_url: str,
    device_id: str,
    fps: int,
    duration: int | None,
    quality: int,
) -> None:
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Hata: Kaynak açılamadı: {source}")
        sys.exit(1)

    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30
    # Kaç karede bir gönderileceğini hesapla
    skip = max(1, int(source_fps / fps))

    print(f"\n{'='*50}")
    print(f"  Kiha Video Simülatörü")
    print(f"{'='*50}")
    print(f"  Kaynak  : {source}")
    print(f"  Sunucu  : {server_url}")
    print(f"  Cihaz   : {device_id}")
    print(f"  Hedef   : {fps} fps  (kaynak: {source_fps:.1f} fps, skip: {skip})")
    print(f"  Süre    : {'Sınırsız' if duration is None else f'{duration}s'}")
    print(f"  Kalite  : {quality}%")
    print(f"{'='*50}\n")
    print("Başlamak için Enter'a basın, durdurmak için Ctrl+C...")
    input()

    frame_idx = 0
    sent = 0
    errors = 0
    start_time = time.time()
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                # Video bitti, başa sar
                if isinstance(source, str):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                break

            frame_idx += 1

            # Süreden fazla geçtiyse dur
            elapsed = time.time() - start_time
            if duration and elapsed >= duration:
                break

            # fps kontrolü — gerekmeyen kareleri atla
            if frame_idx % skip != 0:
                continue

            # JPEG encode
            ok, buf = cv2.imencode(".jpg", frame, encode_params)
            if not ok:
                continue
            jpeg_bytes = buf.tobytes()

            # Sunucuya gönder
            result = send_frame(server_url, device_id, jpeg_bytes)
            if result:
                sent += 1
                labels = result.get("labels", [])
                ms = result.get("inference_ms", 0)
                print(
                    f"  [{elapsed:6.1f}s] Kare #{result.get('frame_id', sent):4d} | "
                    f"{ms:5.0f}ms | {', '.join(labels) if labels else '(nesne yok)'}"
                )
            else:
                errors += 1

            # Gerçek zamanlı simülasyon için bekle
            time.sleep(1 / fps)

    except KeyboardInterrupt:
        print("\n\n[!] Kullanıcı durdurdu.")

    finally:
        cap.release()
        elapsed = time.time() - start_time
        print(f"\n{'='*50}")
        print(f"  Tamamlandı!")
        print(f"  Gönderilen kare : {sent}")
        print(f"  Hata            : {errors}")
        print(f"  Geçen süre      : {elapsed:.1f}s")
        print(f"{'='*50}\n")

        if sent > 0:
            print("Artık sunucuya soru sorabilirsiniz. Örnek:")
            print(f'  python scripts/ask.py --server {server_url} --question "İnsan nerede?"')
            print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Kiha Video Simülatörü")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--video", metavar="DOSYA", help="Video dosyası yolu (.mp4, .avi, ...)")
    source_group.add_argument("--webcam", action="store_true", help="Webcam kullan (kamera 0)")

    parser.add_argument("--server", default="http://82.26.94.210:8000", help="Sunucu URL")
    parser.add_argument("--device-id", default="simulated-device", help="Cihaz kimliği")
    parser.add_argument("--fps", type=int, default=1, help="Saniyede kaç frame gönderilsin (varsayılan: 1)")
    parser.add_argument("--duration", type=int, default=None, help="Kaç saniye gönderilsin (varsayılan: sınırsız)")
    parser.add_argument("--quality", type=int, default=85, help="JPEG kalitesi 1-100 (varsayılan: 85)")

    args = parser.parse_args()
    source: str | int = 0 if args.webcam else args.video

    if isinstance(source, str) and not Path(source).exists():
        print(f"Hata: Dosya bulunamadı: {source}")
        sys.exit(1)

    simulate(
        source=source,
        server_url=args.server.rstrip("/"),
        device_id=args.device_id,
        fps=args.fps,
        duration=args.duration,
        quality=args.quality,
    )


if __name__ == "__main__":
    main()
