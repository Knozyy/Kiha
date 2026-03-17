# KIHA PROJECT — MASTER SYSTEM PROMPT (v1.0)
# TÜBİTAK Destekli AI Tabanlı Akıllı Gözlük Projesi

---

## I. PROJE KİMLİĞİ

- **Proje Adı:** Kiha — AI-Powered Smart Glasses
- **Mimari Model:** İstemci-Sunucu (Thin Client)
- **Gözlük Rolü:** Yalnızca kameradan görüntü yakalar ve sunucuya iletir. Cihaz üzerinde inference YAPILMAZ.
- **Sunucu Rolü:** Gelen video akışını AI modelleriyle işler, sonuçları mobil uygulamaya döner.
- **Dil Protokolü:** Tüm yanıtlar ve açıklamalar Türkçe olmalıdır. Kod yorumları İngilizce olabilir.

---

## II. TEKNOLOJİ YIĞINI (STACK LOCK)

Bu yığın **KESİNDİR**. Onay almadan dışına çıkılamaz.

| Katman | Teknoloji | Dil |
|---|---|---|
| **Gözlük (Client)** | ESP32-S3 + ESP-IDF | C |
| **Aktarım Protokolü** | Raw UDP + DTLS 1.3 (Şifreli) | — |
| **Relay Gateway** | Flutter Mobil Uygulama | Dart |
| **Sunucu API** | FastAPI + asyncio | Python 3.12+ |
| **AI Inference** | YOLOv8 + TensorRT / ONNX Runtime | C++ |
| **Kuyruk Sistemi** | ZeroMQ (ipc) | — |
| **Sonuç Dönüşü** | WebSocket (TLS 1.3) | — |
| **Veritabanı** | PostgreSQL + Redis (cache) | — |
| **CI/CD** | GitHub Actions | — |
| **Konteyner** | Docker + Docker Compose | — |

---

## III. MİMARİ KURALLARI

### A. Gözlük Tarafı (ESP32-S3 / C)

1. **Donanımsal JPEG Sıkıştırma:** Frame'ler CPU yerine ESP32'nin donanım JPEG encoder'ı ile sıkıştırılmalıdır.
2. **Adaptif Kare Hızı:** Sabit 30fps kullanılmaz. Sahne değişimi algılanmadığında (frame diff < threshold) kare hızı 10fps'e düşer, hareket algılandığında 30fps'e çıkar.
3. **Deep Sleep Yönetimi:** Kullanıcı aktif değilken cihaz deep sleep moduna geçmelidir. Wake-up kaynağı: IMU (hareket sensörü) veya GPIO butonu.
4. **Bellek Disiplini:** Dinamik bellek tahsisi (`malloc`) minimize edilmeli, mümkünse statik buffer'lar (`static uint8_t buffer[MAX_FRAME_SIZE]`) tercih edilmelidir.
5. **Watchdog Timer:** Sistem kilitlenmelerine karşı hardware watchdog aktif olmalıdır.

### B. İletişim Katmanı

1. **Protokol:** UDP üzerinden özel lightweight paket formatı:
[frame_id: 4B] [timestamp: 4B] [fragment_info: 2B] [HMAC: 32B] [payload: variable]
2. **Kayıp Frame Politikası:** Retransmission YOKTUR. Eski frame'ler drop edilir — real-time inference için geçmiş frame'in değeri sıfırdır.
3. **Şifreleme:** Tüm UDP trafiği DTLS 1.3 (AES-128-GCM) ile şifrelenir. ESP32'nin donanımsal AES hızlandırması kullanılır.
4. **Kimlik Doğrulama:** Pre-Shared Key (PSK) tabanlı mutual authentication. Her cihaza üretimde benzersiz PSK flash'lanır.

### C. Sunucu Tarafı (Python + C++)

1. **Katmanlı Mimari (Clean Architecture):**
src/ ├── domain/ # İş mantığı — hiçbir framework'e bağımlı değil │ ├── models/ # Pydantic data modelleri │ └── services/ # Core business logic ├── infrastructure/ # Dış bağımlılıklar │ ├── ai/ # YOLO/TensorRT inference engine (C++ binding) │ ├── network/ # UDP receiver, WebSocket handler │ ├── database/ # Repository pattern (PostgreSQL/Redis) │ └── security/ # DTLS, token yönetimi ├── application/ # Use case orchestration │ └── usecases/ # Her use case tek dosya ├── api/ # FastAPI router'ları │ ├── routes/ │ └── middleware/ └── config/ # Pydantic Settings, merkezi konfigürasyon
2. **`any` Yasağı:** Python type hint'lerinde `Any` kullanımı KESİNLİKLE YASAKTIR. Her fonksiyon imzası tam tip tanımlı olmalıdır.
3. **Repository Pattern:** Veritabanı sorguları doğrudan servis katmanına yazılmaz. Her entity için ayrı Repository sınıfı oluşturulur.
4. **Dependency Injection:** FastAPI `Depends()` mekanizması ile tüm bağımlılıklar enjekte edilir.
5. **Özel Hatalar:** `Exception` ile genel yakalama YASAKTIR. Domain'e özel hata sınıfları kullanılır:
```python
class FrameDecodeError(KihaBaseError): ...
class InferenceTimeoutError(KihaBaseError): ...
class DeviceAuthenticationError(KihaBaseError): ...
6.Async First: Tüm I/O operasyonları (DB, network, file) async/await ile yapılır. Bloklayıcı çağrılar asyncio.to_thread() ile sarılır.
D. Flutter Mobil Uygulama
State Management: Tek bir çözüm: Riverpod. Alternatif kullanımı yasaktır.
Offline-First: Bağlantı koptuğunda beyaz ekran YASAKTIR. Skeleton screen + son bilinen durum gösterilir.
Certificate Pinning: Sunucu sertifikasının SHA-256 hash'i uygulama içinde sabitlenir.
WebSocket Reconnection: Bağlantı koptuğunda exponential backoff ile otomatik yeniden bağlanma.
IV. GÜVENLİK PROTOKOLÜ
Uçtan Uca Şifreleme: ESP32 → Sunucu arası tüm trafik DTLS 1.3 ile şifrelenir.
API Güvenliği: JWT + Refresh Token. Access token ömrü: 15dk. Refresh token ömrü: 7 gün.
Rate Limiting: Her endpoint için IP bazlı rate limit uygulanır.
Input Sanitization: Hiçbir kullanıcı girdisine GÜVENİLMEZ. Strict validation uygulanır.
Secret Yönetimi: API anahtarları, PSK'lar, DB şifreleri .env dosyasında tutulur. Hardcoded secret KESİNLİKLE YASAKTIR.
MITM Koruması: DTLS + PSK + HMAC-SHA256 üçlüsü ile frame bazında bütünlük doğrulaması yapılır.
V. PERFORMANS HEDEFLERİ
Metrik	Hedef
Uçtan uca gecikme (E2E)	< 100ms
ESP32 → Sunucu gecikme	< 30ms
AI Inference süresi	< 5ms/frame (YOLOv8-nano + TensorRT)
ESP32 güç tüketimi (aktif)	< 800mW
ESP32 güç tüketimi (idle)	< 50mW (deep sleep)
Pil ömrü (1000mAh)	> 3 saat (aktif kullanım)
VI. KOD KALİTESİ KURALLARI
Early Return: İç içe if-else blokları (arrow code) YASAKTIR. Guard clause kullan.
Dead Code: Kullanılmayan import, değişken ve yorum satırı bırakılmaz.
console.log Yasağı: Debugging bittikten sonra tüm print() / console.log kaldırılır. Sadece logging.error() kalır.
TODO İşaretleme: Kaçınılmaz hack'ler // TODO: Refactor - [Sebep] ile işaretlenir.
Commit Mesajları: Conventional Commits formatı: feat:, fix:, docs:, refactor:, perf:, test:.
Test Kapsamı: Kritik iş mantığı fonksiyonları için minimum %80 test coverage hedeflenir.
VII. DOSYA & İSİMLENDİRME KURALLARI
Katman	Kural	Örnek
Python modülleri	snake_case	frame_processor.py
Python sınıfları	PascalCase	FrameProcessor
Python fonksiyonları	snake_case	decode_frame()
Dart/Flutter dosyaları	snake_case	home_screen.dart
Dart sınıfları	PascalCase	HomeScreen
C dosyaları	snake_case	camera_handler.c
C fonksiyonları	snake_case + prefix	kiha_camera_init()
C makroları	UPPER_SNAKE_CASE	MAX_FRAME_SIZE
Ortam değişkenleri	UPPER_SNAKE_CASE	KIHA_API_SECRET
VIII. PLANLAMA DİSİPLİNİ
Kod yazmadan ÖNCE görevi 

.planning/TODO.md
'ye ekle.
Mimari değişiklikleri 

.planning/ROADMAP.md
'de güncelle.
Tamamlanan görevleri .planning/archive/'e taşı.
Her sprint sonunda CHANGELOG.md güncellenir.