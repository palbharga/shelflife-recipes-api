"""Load and normalize the USDA FSIS FoodKeeper dataset (public domain, CC0).

The raw JSON is shaped like:
    {"sheets": [{"name": "Product", "data": [[{"ID": 1}, {"Name": "Butter"}, ...], ...]},
                {"name": "Category", "data": [...]}, ...]}
Each row is a list of single-key dicts, so we merge them into one flat dict.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

FOODKEEPER_URL = "https://www.fsis.usda.gov/shared/data/EN/foodkeeper.json"
DEFAULT_PATH = Path(os.environ.get("FOODKEEPER_PATH", Path(__file__).parent.parent / "data" / "foodkeeper.json"))

# Storage-field prefixes -> (location, condition)
LOCATIONS = {"pantry": "pantry", "refrigerate": "refrigerator", "freeze": "freezer"}
UNIT_DAYS = {"hour": 1 / 24, "day": 1, "week": 7, "month": 30, "year": 365}


def download(path: Path = DEFAULT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        FOODKEEPER_URL,
        headers={"User-Agent": "Mozilla/5.0 (shelflife-api hackathon project)", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        path.write_bytes(r.read())
    return path


def _flatten(row) -> dict:
    if isinstance(row, dict):
        return row
    out: dict = {}
    for cell in row:
        if isinstance(cell, dict):
            out.update(cell)
    return out


def _clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def _parse_prefix(prefix: str) -> tuple[str, str] | None:
    p = prefix.lower()
    loc = next((LOCATIONS[k] for k in LOCATIONS if k in p), None)
    if not loc:
        return None
    if p.startswith("dop_"):
        cond = "from_purchase_date"
    elif "after_opening" in p:
        cond = "after_opening"
    elif "after_thawing" in p:
        cond = "after_thawing"
    else:
        cond = "unopened"
    return loc, cond


def to_days(value, metric: str | None) -> float | None:
    if value is None or not metric:
        return None
    m = metric.lower().rstrip("s")
    for unit, days in UNIT_DAYS.items():
        if m.endswith(unit):
            try:
                return round(float(value) * days, 2)
            except (TypeError, ValueError):
                return None
    return None


@dataclass
class Food:
    id: int
    name: str
    subtitle: str | None
    category_id: int | None
    keywords: list[str]
    storage: list[dict] = field(default_factory=list)
    category: str | None = None
    subcategory: str | None = None

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.subtitle})" if self.subtitle else self.name

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "subtitle": self.subtitle,
            "display_name": self.display_name,
            "category_id": self.category_id,
            "category": self.category,
            "subcategory": self.subcategory,
            "keywords": self.keywords,
            "storage": self.storage,
        }


def _build_storage(row: dict) -> list[dict]:
    out = []
    for key in row:
        if not key.endswith("_Metric"):
            continue
        prefix = key[: -len("_Metric")]
        parsed = _parse_prefix(prefix)
        if not parsed:
            continue
        mn, mx, metric = _clean(row.get(f"{prefix}_Min")), _clean(row.get(f"{prefix}_Max")), _clean(row.get(key))
        tips = _clean(row.get(f"{prefix}_tips") or row.get(f"{prefix}_Tips"))
        if mn is None and mx is None and metric is None and tips is None:
            continue
        loc, cond = parsed
        out.append({
            "location": loc,
            "condition": cond,
            "min": mn,
            "max": mx,
            "unit": metric,
            "min_days": to_days(mn, metric),
            "max_days": to_days(mx if mx is not None else mn, metric),
            "tips": tips,
        })
    order = {"pantry": 0, "refrigerator": 1, "freezer": 2}
    cond_order = {"unopened": 0, "from_purchase_date": 1, "after_opening": 2, "after_thawing": 3}
    out.sort(key=lambda s: (order[s["location"]], cond_order[s["condition"]]))
    return out


class FoodKeeper:
    def __init__(self, raw: dict):
        sheets = {s.get("name"): [_flatten(r) for r in s.get("data", [])] for s in raw.get("sheets", [])}
        self.categories: dict[int, dict] = {}
        for c in sheets.get("Category", []):
            if c.get("ID") is None:
                continue
            self.categories[int(c["ID"])] = {
                "id": int(c["ID"]),
                "name": _clean(c.get("Category_Name")),
                "subcategory": _clean(c.get("Subcategory_Name")),
            }
        self.foods: dict[int, Food] = {}
        for p in sheets.get("Product", []):
            if p.get("ID") is None or not _clean(p.get("Name")):
                continue
            cid = p.get("Category_ID")
            cat = self.categories.get(int(cid)) if cid is not None else None
            kw = _clean(p.get("Keywords")) or ""
            self.foods[int(p["ID"])] = Food(
                id=int(p["ID"]),
                name=_clean(p["Name"]),
                subtitle=_clean(p.get("Name_subtitle")),
                category_id=int(cid) if cid is not None else None,
                keywords=[k.strip() for k in kw.split(",") if k.strip()],
                storage=_build_storage(p),
                category=cat["name"] if cat else None,
                subcategory=cat["subcategory"] if cat else None,
            )

    @classmethod
    def load(cls, path: Path = DEFAULT_PATH, auto_download: bool = True) -> "FoodKeeper":
        path = Path(path)
        if not path.exists():
            if not auto_download:
                raise FileNotFoundError(path)
            download(path)
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def search(self, q: str, limit: int = 10) -> list[tuple[Food, float]]:
        q = q.lower().strip()
        tokens = re.findall(r"[a-z0-9]+", q)
        if not tokens:
            return []
        results = []
        for food in self.foods.values():
            hay_name = food.display_name.lower()
            hay_all = " ".join([hay_name, *(k.lower() for k in food.keywords)])
            if q == food.name.lower():
                score = 1.0
            elif all(t in hay_all for t in tokens):
                score = 0.75 + 0.2 * (sum(t in hay_name for t in tokens) / len(tokens))
            else:
                score = max(
                    0.72 * SequenceMatcher(None, q, food.name.lower()).ratio(),
                    0.68 * max(SequenceMatcher(None, q, w).ratio() for w in [hay_name, *(k.lower() for k in food.keywords)]),
                )
            if score >= 0.5:
                results.append((food, round(score, 3)))
        results.sort(key=lambda x: (-x[1], x[0].id))  # lower ID = USDA's base/most common item
        return results[:limit]
