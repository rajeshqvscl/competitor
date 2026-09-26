"""Normalize raw extracted payloads into schema-shaped dicts.

RawPayload (from website/report extractors) → LoadPayload (loader-ready).

Key responsibilities:
- slugify
- fuzzy-map product/brand names onto existing taxonomy hints
- parse pack sizes / prices from free text
- attach confidence + source_url for provenance
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Optional


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "na"


# --- keyword → taxonomy maps (seed taxonomy is fixed: 8 categories / 33 subcategories) ---
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Milk": ("milk",),
    "Fermented Dairy": ("curd", "dahi", "yogurt", "yoghurt", "buttermilk", "lassi", "fermented", "probiotic"),
    "Dairy Fats": ("ghee", "butter", "cream", "fat spread", "white butter"),
    "Fresh Dairy": ("paneer", "cottage cheese", "fresh cheese", "ricotta"),
    "Cheese": ("cheese", "cheddar", "mozzarella", "processed cheese", "cheese slice", "cheese cube", "cheese spread"),
    "Frozen Dairy": ("ice cream", "icecream", "frozen dessert", "kulfi", "gelato"),
    "Dairy Sweets": ("rasgulla", "peda", "gulab jamun", "milk sweet", "kaju", "barfi", "burfi", "sandesh"),
    "Dairy Ingredients": ("milk powder", "skimmed milk powder", "smp", "whey", "casein", "dairy ingredient", "whole milk powder", "wmp"),
}

SUBCATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Full Cream Milk": ("full cream", "full cream milk", "gold milk", "whole milk", "rich milk", "a2 milk"),
    "Toned Milk": ("toned", "toned milk", "duble toned", "double toned"),
    "Double Toned Milk": ("double toned", "double-toned", "duble toned"),
    "Skimmed Milk": ("skimmed", "skim milk", "fat free milk"),
    "UHT Milk": ("uht", "long life", "ambient milk"),
    "A2 Milk": ("a2", "a2 milk", "desi cow"),
    "Flavoured Milk": ("flavoured milk", "flavored milk", "chocolate milk", "badam milk", "kesar milk"),
    "Curd": ("curd", "set curd", "dahi cup"),
    "Dahi": ("dahi",),
    "Yogurt": ("yogurt", "yoghurt", "plain yogurt"),
    "Greek Yogurt": ("greek", "greek yogurt", "greek yoghurt", "hung curd"),
    "Buttermilk": ("buttermilk", "chaas", "matha"),
    "Lassi": ("lassi", "sweet lassi", "salted lassi"),
    "Ghee": ("ghee", "clarified butter", "desi ghee"),
    "Butter": ("butter", "white butter", "makhan", "table butter"),
    "Cream": ("cream", "fresh cream", "whipping cream", "malai", "cooking cream"),
    "Paneer": ("paneer", "cottage cheese block"),
    "Fresh Cheese": ("fresh cheese",),
    "Processed Cheese": ("processed cheese", "cheese block", "cheese process"),
    "Cheddar": ("cheddar",),
    "Mozzarella": ("mozzarella",),
    "Cheese Slices": ("cheese slice", "slices cheese", "sandwich cheese"),
    "Cheese Cubes": ("cheese cube", "cubes cheese"),
    "Cheese Spread": ("cheese spread", "spread cheese"),
    "Ice Cream": ("ice cream", "icecream", "cone", "cup ice cream", "family pack ice"),
    "Frozen Dessert": ("frozen dessert", "frozen desserts"),
    "Kulfi": ("kulfi",),
    "Rasgulla": ("rasgulla",),
    "Peda": ("peda", "mathura peda"),
    "Gulab Jamun": ("gulab jamun",),
    "Milk Powder": ("milk powder", "whole milk powder", "wmp", "dairy whitener"),
    "Skimmed Milk Powder": ("skimmed milk powder", "smp", "skim powder"),
    "Whey": ("whey", "whey powder", "whey protein"),
}


def detect_category(text: str) -> Optional[str]:
    low = (text or "").lower()
    # Longer/more specific keywords first by scoring
    best: Optional[str] = None
    best_len = 0
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in low and len(kw) > best_len:
                best, best_len = cat, len(kw)
    return best


def detect_subcategory(text: str) -> Optional[str]:
    low = (text or "").lower()
    best: Optional[str] = None
    best_len = 0
    for sub, kws in SUBCATEGORY_KEYWORDS.items():
        for kw in kws:
            if kw in low and len(kw) > best_len:
                best, best_len = sub, len(kw)
    return best


_PACK_RE = re.compile(
    r"(?P<size>\d+(?:\.\d+)?)\s*(?P<unit>ml|l|lt|ltr|liter|litre|g|kg|gm|gram|pcs|piece|pack|x)\b",
    re.I,
)
_PRICE_RE = re.compile(r"(?:₹|rs\.?|inr)\s*(?P<p>\d+(?:\.\d{1,2})?)", re.I)
_MRP_RE = re.compile(r"\bmrp\s*[:\-]?\s*(?:₹|rs\.?|inr)?\s*(?P<p>\d+(?:\.\d{1,2})?)", re.I)


def parse_pack(text: str) -> tuple[Optional[float], Optional[str]]:
    m = _PACK_RE.search(text or "")
    if not m:
        return None, None
    size = float(m.group("size"))
    unit_raw = m.group("unit").lower()
    unit_map = {"lt": "l", "ltr": "l", "liter": "l", "litre": "l", "gm": "g", "gram": "g", "pcs": "pcs", "piece": "pcs", "pack": "pack", "x": "pack"}
    unit = unit_map.get(unit_raw, unit_raw)
    if unit == "l":
        # store in ml for consistency with seed data? Seed uses ml for milk, g for solids.
        # Keep as liters only if text explicitly used L — normalize to ml for liquids when integer-ish.
        pass
    return size, unit


def parse_price(text: str) -> tuple[Optional[float], Optional[float]]:
    """Return (mrp, selling_price) best-effort from free text."""
    text = text or ""
    mrp = None
    m = _MRP_RE.search(text)
    if m:
        mrp = float(m.group("p"))
    # All ₹/Rs prices with positions; prefer the last (often the effective/selling price)
    # when MRP was matched separately.
    prices: list[float] = [float(x) for x in _PRICE_RE.findall(text)]
    sell = None
    if prices:
        if mrp is not None:
            # selling = last price that is not the MRP value, else min
            non_mrp = [p for p in prices if abs(p - mrp) > 0.001]
            sell = non_mrp[-1] if non_mrp else min(prices)
        else:
            sell = prices[-1]
            mrp = max(prices)
    if mrp is not None and sell is not None and sell > mrp:
        mrp, sell = sell, mrp
    return mrp, sell


def norm_name(name: str) -> str:
    """Aggressive name normalization for fuzzy matching."""
    s = slugify(name)
    # Strip common filler words for matching.
    drop = {"the", "and", "of", "a", "an"}
    parts = [p for p in s.split("-") if p and p not in drop]
    return "-".join(parts)


def fuzzy_in(name: str, candidates: list[str], strict: bool = False) -> Optional[str]:
    """Return candidate equal to name (normalized), or a close containment match.

    strict=True: exact normalized equality only (safe for brands — avoids
    'Amul Gold' collapsing into 'Amul' via substring).
    """
    if not name:
        return None
    n = norm_name(name)
    nn = n.replace("-", "")
    for c in candidates:
        cn = norm_name(c)
        cn_flat = cn.replace("-", "")
        if n == cn or nn == cn_flat:
            return c
    if strict:
        return None
    for c in candidates:
        cn = norm_name(c)
        cn_flat = cn.replace("-", "")
        # Require substantial overlap: shorter ≥ 6 chars and is ≥65% of longer
        shorter, longer = sorted((nn, cn_flat), key=len)
        if len(shorter) >= 6 and shorter in longer and len(shorter) >= 0.65 * len(longer):
            return c
    return None


# --- Payload dataclasses ---

@dataclass
class RawBrand:
    name: str
    description: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class RawProduct:
    name: str
    brand: Optional[str] = None
    subcategory: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class RawSku:
    product: str
    brand: Optional[str] = None
    variant: Optional[str] = None
    pack_size: Optional[float] = None
    unit: Optional[str] = None
    packaging_type: Optional[str] = None
    mrp: Optional[float] = None
    selling_price: Optional[float] = None
    fat_percent: Optional[float] = None
    protein_percent: Optional[float] = None
    shelf_life_days: Optional[int] = None
    flavour: Optional[str] = None
    status: str = "active"
    source_url: Optional[str] = None


@dataclass
class RawDistributor:
    name: str
    type: Optional[str] = None
    territory: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    channel: Optional[str] = None
    website: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class RawPayload:
    """What an extractor produces for one company run."""
    company_slug: str
    source_type: str  # website | annual_report
    source_url: str
    confidence: str = "medium"  # high | medium | low
    description: Optional[str] = None
    parent_company: Optional[str] = None
    is_listed: Optional[bool] = None
    is_global: Optional[bool] = None
    brands: list[RawBrand] = field(default_factory=list)
    products: list[RawProduct] = field(default_factory=list)
    skus: list[RawSku] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)  # state/region names for company_regions
    distributors: list[RawDistributor] = field(default_factory=list)
    # free-form evidence lines for review_queue / sources
    facts: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any([self.description, self.brands, self.products, self.skus,
                        self.regions, self.distributors, self.parent_company is not None])
