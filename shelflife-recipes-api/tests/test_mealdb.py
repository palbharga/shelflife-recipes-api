"""TheMealDB pass-through: correct upstream URL, response returned unchanged, pretty-printed."""
import json
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from app import main, recipes

SAMPLE = {"meals": [{"idMeal": "52772", "strMeal": "Teriyaki Chicken Casserole", "strIngredient1": "soy sauce"}]}


class FakeResp:
    def __init__(self, body): self.body = body
    def read(self): return json.dumps(self.body).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False


@pytest.fixture
def calls():
    recipes._cache.clear()
    seen = []
    def fake(req, timeout=0):
        seen.append(req.full_url)
        return FakeResp(SAMPLE)
    with mock.patch("urllib.request.urlopen", fake):
        yield seen


client = TestClient(main.app)
BASE = "https://www.themealdb.com/api/json/v1/1/"


@pytest.mark.parametrize("path,upstream", [
    ("/mealdb/search.php?s=Arrabiata", "search.php?s=Arrabiata"),
    ("/mealdb/search.php?f=a", "search.php?f=a"),
    ("/mealdb/lookup.php?i=52772", "lookup.php?i=52772"),
    ("/mealdb/random.php", "random.php"),
    ("/mealdb/categories.php", "categories.php"),
    ("/mealdb/list.php?c=list", "list.php?c=list"),
    ("/mealdb/list.php?a=list", "list.php?a=list"),
    ("/mealdb/list.php?i=list", "list.php?i=list"),
    ("/mealdb/filter.php?i=chicken_breast", "filter.php?i=chicken_breast"),
    ("/mealdb/filter.php?c=Seafood", "filter.php?c=Seafood"),
    ("/mealdb/filter.php?a=Canadian", "filter.php?a=Canadian"),
])
def test_forwards_exactly(calls, path, upstream):
    r = client.get(path)
    assert r.status_code == 200
    assert calls == [BASE + upstream]
    assert r.json() == SAMPLE            # unchanged
    assert r.text.startswith('{\n  "meals"')  # pretty-printed


def test_needs_exactly_one_param(calls):
    assert client.get("/mealdb/search.php").status_code == 400
    assert client.get("/mealdb/filter.php?i=x&c=y").status_code == 400
    assert calls == []


def test_upstream_down():
    recipes._cache.clear()
    with mock.patch("urllib.request.urlopen", side_effect=OSError("no network")):
        r = client.get("/mealdb/lookup.php?i=1")
    assert r.status_code == 502 and "TheMealDB" in r.json()["error"]


def test_random_not_cached(calls):
    client.get("/mealdb/random.php"); client.get("/mealdb/random.php")
    client.get("/mealdb/lookup.php?i=5"); client.get("/mealdb/lookup.php?i=5")
    assert len(calls) == 3
