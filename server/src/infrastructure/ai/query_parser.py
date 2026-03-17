"""Kiha Server — Natural Language Query Parser.

Parses Turkish user questions into searchable object labels.
Maps Turkish words to YOLO COCO class names (English).

Example:
    'Anahtarlarımı nereye koydum?' → ['key']
    'Ocağın altını kapattım mı?'  → ['oven', 'stove']
    'Telefonumu nerede gördüm?'   → ['cell phone']
"""

import logging
import re

logger = logging.getLogger(__name__)

# Turkish → English YOLO label mapping table
# Covers common everyday objects users would ask about
TURKISH_TO_YOLO: dict[str, list[str]] = {
    # Kişisel eşyalar
    "anahtar": ["key"],
    "anahtarlar": ["key"],
    "anahtarlık": ["key"],
    "telefon": ["cell phone"],
    "telefonum": ["cell phone"],
    "cüzdan": ["handbag", "backpack"],
    "çanta": ["handbag", "backpack", "suitcase"],
    "sırt çantası": ["backpack"],
    "bavul": ["suitcase"],
    "şemsiye": ["umbrella"],
    "gözlük": ["eyeglasses"],
    "saat": ["clock"],
    "kravat": ["tie"],

    # Mutfak / Yemek
    "ocak": ["oven", "microwave"],
    "fırın": ["oven"],
    "mikrodalga": ["microwave"],
    "buzdolabı": ["refrigerator"],
    "lavabo": ["sink"],
    "tost makinesi": ["toaster"],
    "bardak": ["cup", "wine glass"],
    "fincan": ["cup"],
    "tabak": ["bowl"],
    "çatal": ["fork"],
    "bıçak": ["knife"],
    "kaşık": ["spoon"],
    "şişe": ["bottle"],

    # Yiyecekler
    "elma": ["apple"],
    "portakal": ["orange"],
    "muz": ["banana"],
    "sandviç": ["sandwich"],
    "pizza": ["pizza"],
    "kek": ["cake", "donut"],
    "havuç": ["carrot"],
    "brokoli": ["broccoli"],

    # Mobilya / Ev
    "sandalye": ["chair"],
    "koltuk": ["couch"],
    "kanepe": ["couch"],
    "yatak": ["bed"],
    "masa": ["dining table"],
    "televizyon": ["tv"],
    "tv": ["tv"],
    "bilgisayar": ["laptop"],
    "laptop": ["laptop"],
    "klavye": ["keyboard"],
    "fare": ["mouse"],
    "kumanda": ["remote"],
    "tuvalet": ["toilet"],
    "saksı": ["potted plant"],
    "bitki": ["potted plant"],
    "çiçek": ["vase", "potted plant"],
    "vazo": ["vase"],
    "kitap": ["book"],
    "makas": ["scissors"],

    # Araç / Dış mekan
    "araba": ["car"],
    "arabam": ["car"],
    "otobüs": ["bus"],
    "bisiklet": ["bicycle"],
    "motosiklet": ["motorcycle"],
    "kamyon": ["truck"],

    # Canlılar
    "kedi": ["cat"],
    "köpek": ["dog"],
    "kuş": ["bird"],
    "kişi": ["person"],
    "insan": ["person"],

    # Diğer
    "top": ["sports ball"],
    "oyuncak": ["teddy bear"],
    "ayı": ["teddy bear", "bear"],
    "diş fırçası": ["toothbrush"],
    "saç kurutma": ["hair drier"],
}

# Common Turkish question patterns for intent detection
LOCATION_PATTERNS: list[str] = [
    r"nere(?:ye|de|den|si)",
    r"nereye?\s*koy",
    r"nerede?\s*(?:gör|bırak|bul)",
    r"nerede",
    r"nereye",
]

ACTION_CHECK_PATTERNS: list[str] = [
    r"kapat(?:tım|tın|tı)\s*mı",
    r"açık\s*mı",
    r"açtım\s*mı",
    r"kapattım\s*mı",
    r"unuttu[mn]\s*mu",
    r"bıraktım\s*mı",
]

TIME_PATTERNS: list[str] = [
    r"en\s*son",
    r"son\s*(?:kez|olarak|defa)",
    r"ne\s*zaman",
    r"kaç(?:ta|te)",
    r"(?:bu|dün|geçen)\s*(?:gün|sabah|akşam)",
]


class ParsedQuery:
    """Result of parsing a user's natural language question."""

    def __init__(
        self,
        original_query: str,
        target_labels: list[str],
        query_type: str,
        turkish_keywords: list[str],
    ) -> None:
        self.original_query = original_query
        self.target_labels = target_labels  # YOLO label names (English)
        self.query_type = query_type  # 'location', 'action_check', 'time', 'general'
        self.turkish_keywords = turkish_keywords  # Matched Turkish words

    def __repr__(self) -> str:
        return (
            f"ParsedQuery(labels={self.target_labels}, "
            f"type={self.query_type}, "
            f"keywords={self.turkish_keywords})"
        )


class QueryParser:
    """Parse Turkish user questions into searchable queries.

    Keyword-based approach for v1.
    Future: integrate LLM for better NLU.
    """

    def __init__(self) -> None:
        # Build reverse index: normalized word → yolo labels
        self._word_index: dict[str, list[str]] = {}
        for tr_word, yolo_labels in TURKISH_TO_YOLO.items():
            normalized = self._normalize(tr_word)
            self._word_index[normalized] = yolo_labels

    def parse(self, question: str) -> ParsedQuery:
        """Parse a Turkish question into a structured query.

        Steps:
        1. Normalize the question text
        2. Detect query type (location/action/time/general)
        3. Extract target object keywords
        4. Map to YOLO labels
        """
        normalized = self._normalize(question)
        query_type = self._detect_query_type(question)
        matched_labels, matched_keywords = self._extract_labels(normalized)

        if not matched_labels:
            logger.error(
                "No YOLO labels matched for query: '%s'",
                question,
            )

        return ParsedQuery(
            original_query=question,
            target_labels=matched_labels,
            query_type=query_type,
            turkish_keywords=matched_keywords,
        )

    def _extract_labels(
        self,
        normalized_text: str,
    ) -> tuple[list[str], list[str]]:
        """Extract YOLO labels from normalized text.

        Tries longest match first (e.g., 'sırt çantası' before 'çanta').
        """
        found_labels: list[str] = []
        found_keywords: list[str] = []

        # Sort by length descending for longest match first
        sorted_words = sorted(
            self._word_index.keys(),
            key=len,
            reverse=True,
        )

        for word in sorted_words:
            if word in normalized_text:
                labels = self._word_index[word]
                for lbl in labels:
                    if lbl not in found_labels:
                        found_labels.append(lbl)
                found_keywords.append(word)
                # Remove matched word to prevent sub-matches
                normalized_text = normalized_text.replace(word, " ")

        return found_labels, found_keywords

    def _detect_query_type(self, question: str) -> str:
        """Detect the intent type of the question."""
        lower = question.lower()

        for pattern in ACTION_CHECK_PATTERNS:
            if re.search(pattern, lower):
                return "action_check"

        for pattern in TIME_PATTERNS:
            if re.search(pattern, lower):
                return "time"

        for pattern in LOCATION_PATTERNS:
            if re.search(pattern, lower):
                return "location"

        return "general"

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize Turkish text for matching.

        Lowercase, strip suffixes (basic stemming),
        remove punctuation.
        """
        # Turkish-aware lowercase (Python's str.lower() mishandles İ → i̇)
        text = text.replace("İ", "i").replace("I", "ı").replace("Ğ", "ğ") \
                   .replace("Ş", "ş").replace("Ç", "ç").replace("Ö", "ö") \
                   .replace("Ü", "ü")
        text = text.lower().strip()
        # Remove common Turkish question suffixes
        text = re.sub(r'[?!.,;:"\']', '', text)
        # Remove possessive suffixes: -ım, -im, -um, -üm, -ımı, -ini, etc.
        text = re.sub(r'(?:lar|ler)(?:ım|im|um|üm|ın|in|un|ün)(?:ı|i|u|ü)?', '', text)
        text = re.sub(r'(?:ım|im|um|üm)(?:ı|i|u|ü)?', '', text)
        return text
