"""Direct pass-through to TheMealDB API v1 (https://www.themealdb.com/documentation).

Requests are forwarded unchanged and TheMealDB's JSON is returned exactly as received.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request

MEALDB_KEY = os.environ.get("MEALDB_KEY", "1")  # "1" = free test key
MEALDB_BASE = f"https://www.themealdb.com/api/json/v1/{MEALDB_KEY}"
CACHE_SECONDS = 60 * 60
NO_CACHE = {"random.php"}

_cache: dict[str, tuple[float, dict]] = {}


class MealDBError(RuntimeError):
    pass


def call(endpoint: str, params: dict[str, str] | None = None) -> dict:
    query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
    url = f"{MEALDB_BASE}/{endpoint}" + (f"?{query}" if query else "")
    cacheable = endpoint not in NO_CACHE
    hit = _cache.get(url)
    if cacheable and hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    req = urllib.request.Request(url, headers={"User-Agent": "shelflife-api/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8") or "{}")
    except Exception as e:  # network, HTTP, or bad JSON
        raise MealDBError(f"TheMealDB request failed: {e}") from e
    if cacheable:
        _cache[url] = (time.time(), data)
    return data
