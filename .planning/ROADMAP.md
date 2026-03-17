# KIHA — PROJE YOL HARİTASI

## Faz 1: Altyapı & İskelet (Mevcut)
- Proje dizin yapısı (Clean Architecture)
- FastAPI sunucu iskeleti + Pydantic Settings
- ESP32-S3 firmware iskeleti (ESP-IDF)
- Docker Compose (PostgreSQL, Redis, Server)
- CI/CD pipeline (GitHub Actions)

## Faz 2: İletişim Katmanı
- ESP32 → Sunucu: UDP + DTLS 1.3 bağlantısı
- Özel paket formatı implementasyonu
- HMAC-SHA256 frame doğrulama
- PSK tabanlı mutual authentication
- Sunucu → Mobil: WebSocket (TLS 1.3)

## Faz 3: AI Pipeline
- YOLOv8-nano model entegrasyonu
- TensorRT / ONNX Runtime binding (C++)
- ZeroMQ ipc kuyruk sistemi
- Frame decode → Inference → Sonuç pipeline
- Hedef: < 5ms/frame inference süresi

## Faz 4: Mobil Uygulama (Flutter)
- Riverpod state management
- Chat/sohbet arayüzü (AI ile konuşma)
- Ayarlar ekranı (gözlük durumu, pil, bağlantı)
- Offline-First (skeleton screen)
- Certificate Pinning + WebSocket reconnection

## Faz 5: Entegrasyon & Optimizasyon
- Uçtan uca entegrasyon
- Performans optimizasyonu (E2E < 100ms)
- Güvenlik audit + penetrasyon testi
- Kullanıcı kabul testleri
- TÜBİTAK raporlama
