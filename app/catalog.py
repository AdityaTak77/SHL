import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── Catalog Loading ────────────────────────────────────────────────────────
CATALOG_PATH = Path(__file__).parent.parent / "catalog" / "shl_catalog.json"

def _load_catalog() -> List[Dict]:
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

CATALOG: List[Dict] = _load_catalog()
CATALOG_BY_ID: Dict[str, Dict] = {item["id"]: item for item in CATALOG}
CATALOG_URLS: set = {item["url"] for item in CATALOG}
CATALOG_NAMES: set = {item["name"] for item in CATALOG}


def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    text = unicodedata.normalize("NFKD", text)
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def validate_recommendation(rec: Dict) -> bool:
    """Validate that a recommendation exists in the catalog."""
    return rec.get("url") in CATALOG_URLS or rec.get("name") in CATALOG_NAMES


def get_all_catalog_items() -> List[Dict]:
    return CATALOG


def get_item_by_id(item_id: str) -> Optional[Dict]:
    return CATALOG_BY_ID.get(item_id)


def search_by_name(name: str) -> Optional[Dict]:
    """Fuzzy search by name."""
    norm = normalize_text(name)
    for item in CATALOG:
        if normalize_text(item["name"]) == norm:
            return item
    for item in CATALOG:
        if norm in normalize_text(item["name"]):
            return item
    return None
