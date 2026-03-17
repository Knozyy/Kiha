"""Kiha Server — VLM Output Parser.

VLM'in serbest metin ciktisini yapilandirilmis veriye donusturur.
Renk, konum, nesne adi ve mekansal iliskileri cikarir.
"""

import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Turkce renk sozcukleri
COLORS = {
    "kirmizi", "kırmızı", "siyah", "beyaz", "mavi", "yesil", "yeşil",
    "kahverengi", "gri", "turuncu", "pembe", "sari", "sarı", "mor",
    "lacivert", "bej", "krem", "altin", "altın", "gumus", "gümüş",
}

# Konum iliskileri (Turkce)
LOCATION_PREDICATES = {
    "ustunde": "üstünde", "üstünde": "üstünde", "uzerinde": "üzerinde",
    "üzerinde": "üzerinde", "altinda": "altında", "altında": "altında",
    "yaninda": "yanında", "yanında": "yanında", "icinde": "içinde",
    "içinde": "içinde", "onunde": "önünde", "önünde": "önünde",
    "arkasinda": "arkasında", "arkasında": "arkasında",
    "kosesinde": "köşesinde", "köşesinde": "köşesinde",
    "kenarinda": "kenarında", "kenarında": "kenarında",
    "uzerinde": "üzerinde", "onünde": "önünde",
}

# YOLO label -> Turkce karsiligi
YOLO_TO_TURKISH = {
    "person": "kişi", "bicycle": "bisiklet", "car": "araba",
    "motorcycle": "motosiklet", "bus": "otobüs", "truck": "kamyon",
    "traffic light": "trafik lambası", "stop sign": "dur işareti",
    "bench": "bank", "bird": "kuş", "cat": "kedi", "dog": "köpek",
    "backpack": "sırt çantası", "umbrella": "şemsiye", "handbag": "el çantası",
    "suitcase": "bavul", "tie": "kravat",
    "bottle": "şişe", "wine glass": "kadeh", "cup": "fincan",
    "fork": "çatal", "knife": "bıçak", "spoon": "kaşık",
    "bowl": "kase", "banana": "muz", "apple": "elma",
    "sandwich": "sandviç", "orange": "portakal", "pizza": "pizza",
    "donut": "donut", "cake": "kek", "chair": "sandalye",
    "couch": "kanepe", "potted plant": "saksı bitkisi",
    "bed": "yatak", "dining table": "masa", "toilet": "tuvalet",
    "tv": "televizyon", "laptop": "laptop", "mouse": "fare",
    "remote": "kumanda", "keyboard": "klavye", "cell phone": "telefon",
    "microwave": "mikrodalga", "oven": "fırın", "toaster": "tost makinesi",
    "sink": "lavabo", "refrigerator": "buzdolabı", "book": "kitap",
    "clock": "saat", "vase": "vazo", "scissors": "makas",
    "teddy bear": "oyuncak ayı", "toothbrush": "diş fırçası",
    "key": "anahtar",
}

# Sahne tipleri
SCENE_KEYWORDS = {
    "mutfak": ["mutfak", "tezgah", "ocak", "fırın", "buzdolabı", "lavabo", "kitchen"],
    "salon": ["salon", "kanepe", "koltuk", "televizyon", "tv", "living"],
    "yatak_odasi": ["yatak", "yastık", "çarşaf", "bedroom"],
    "banyo": ["banyo", "duş", "lavabo", "tuvalet", "bathroom"],
    "ofis": ["masa", "bilgisayar", "laptop", "klavye", "office", "monitor"],
    "dis_mekan": ["araba", "ağaç", "yol", "sokak", "park", "outdoor"],
}


@dataclass
class ParsedObject:
    """Tek bir nesnenin parse edilmis bilgileri."""
    turkish_name: str
    yolo_label: str = ""
    color: str = ""
    location_desc: str = ""
    material: str = ""
    state: str = ""


@dataclass
class ParsedRelation:
    """Iki nesne arasindaki mekansal iliski."""
    subject: str       # "anahtar"
    predicate: str     # "üstünde"
    object_ref: str    # "masa"


@dataclass
class ParsedScene:
    """VLM ciktisinin tam parse sonucu."""
    description: str
    scene_type: str = "bilinmiyor"
    lighting: str = ""
    objects: list[ParsedObject] = field(default_factory=list)
    relations: list[ParsedRelation] = field(default_factory=list)


def parse_vlm_output(vlm_text: str, yolo_labels: list[str] | None = None) -> ParsedScene:
    """VLM ciktisini parse et.

    1. JSON parse dene
    2. Basarisizsa serbest metin parse et
    3. Renk, konum, iliski cikar
    """
    if not vlm_text or not vlm_text.strip():
        return ParsedScene(description="", scene_type="bilinmiyor")

    description = vlm_text.strip()

    # JSON parse dene
    objects = _try_parse_json(vlm_text)

    # Basarisizsa serbest metin parse
    if not objects:
        objects = _parse_freetext(vlm_text)

    # YOLO labellerinden eksik nesneleri ekle
    if yolo_labels:
        existing_yolo = {o.yolo_label for o in objects if o.yolo_label}
        for label in yolo_labels:
            if label not in existing_yolo:
                tr_name = YOLO_TO_TURKISH.get(label, label)
                objects.append(ParsedObject(
                    turkish_name=tr_name,
                    yolo_label=label,
                ))

    # Iliskileri cikar
    relations = _extract_relations(vlm_text, objects)

    # Sahne tipini belirle
    scene_type = _detect_scene_type(vlm_text, yolo_labels or [])

    return ParsedScene(
        description=description,
        scene_type=scene_type,
        objects=objects,
        relations=relations,
    )


def _try_parse_json(text: str) -> list[ParsedObject]:
    """JSON formatinda VLM ciktisi parse et."""
    objects = []

    # JSON array bul
    json_match = re.search(r'\[[\s\S]*?\]', text)
    if not json_match:
        return objects

    try:
        items = json.loads(json_match.group())
        for item in items:
            if isinstance(item, dict):
                name = item.get("nesne", item.get("name", ""))
                if not name:
                    continue
                obj = ParsedObject(
                    turkish_name=name,
                    color=item.get("renk", item.get("color", "")),
                    location_desc=item.get("konum", item.get("location", "")),
                    state=item.get("durum", item.get("state", "")),
                    material=item.get("malzeme", item.get("material", "")),
                )
                # Turkce isimden YOLO label bul
                for yolo, tr in YOLO_TO_TURKISH.items():
                    if tr in name.lower() or name.lower() in tr:
                        obj.yolo_label = yolo
                        break
                objects.append(obj)
    except (json.JSONDecodeError, TypeError):
        pass

    return objects


def _parse_freetext(text: str) -> list[ParsedObject]:
    """Serbest metin VLM ciktisini satirlara ayirip parse et."""
    objects = []
    lines = text.split("\n")

    for line in lines:
        line = line.strip().lstrip("- •*").strip()
        if len(line) < 5:
            continue

        obj = ParsedObject(turkish_name="")

        # Renk bul
        line_lower = line.lower()
        for color in COLORS:
            if color in line_lower:
                obj.color = color
                break

        # Konum bul
        for key, normalized in LOCATION_PREDICATES.items():
            if key in line_lower:
                # Konumun tam ifadesini cikar: "masanin ustunde"
                pattern = rf'(\w+(?:\s+\w+)?)\s+{re.escape(key)}'
                match = re.search(pattern, line_lower)
                if match:
                    obj.location_desc = f"{match.group(1)} {normalized}"
                else:
                    obj.location_desc = normalized
                break

        # Nesne adini bul — YOLO_TO_TURKISH'ten esle
        for yolo_label, tr_name in YOLO_TO_TURKISH.items():
            if tr_name.lower() in line_lower:
                obj.turkish_name = tr_name
                obj.yolo_label = yolo_label
                break

        # Hala isim bulunamadiysa satirin basini al
        if not obj.turkish_name:
            words = line.split()
            # Renk sozcugunu atla
            name_words = [w for w in words[:3] if w.lower() not in COLORS]
            if name_words:
                obj.turkish_name = name_words[0].strip(".,;:")

        if obj.turkish_name:
            objects.append(obj)

    return objects


def _extract_relations(text: str, objects: list[ParsedObject]) -> list[ParsedRelation]:
    """Metinden mekansal iliskileri cikar."""
    relations = []
    text_lower = text.lower()

    for key, normalized in LOCATION_PREDICATES.items():
        if key not in text_lower:
            continue

        # "X masanin ustunde" pattern
        pattern = rf'(\w+)\s+(\w+(?:nın|nin|nun|nün|ın|in|un|ün)?)\s+{re.escape(key)}'
        for match in re.finditer(pattern, text_lower):
            subject = match.group(1)
            surface = match.group(2)
            # "nın/nin" ekini temizle
            surface = re.sub(r'(?:nın|nin|nun|nün|ın|in|un|ün)$', '', surface)

            relations.append(ParsedRelation(
                subject=subject,
                predicate=normalized,
                object_ref=surface,
            ))

    return relations


def _detect_scene_type(text: str, yolo_labels: list[str]) -> str:
    """Sahne tipini belirle."""
    text_lower = text.lower()
    all_text = f"{text_lower} {' '.join(yolo_labels)}"

    scores: dict[str, int] = {}
    for scene_type, keywords in SCENE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in all_text)
        if score > 0:
            scores[scene_type] = score

    if scores:
        return max(scores, key=scores.get)
    return "bilinmiyor"
