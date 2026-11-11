"""Checks against the real USDA file in data/ (skipped if it's missing)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.data import FoodKeeper

DATA = Path(__file__).parent.parent / "data" / "foodkeeper.json"
pytestmark = pytest.mark.skipif(not DATA.exists(), reason="no real data file")


@pytest.fixture(scope="module")
def client():
    fk = FoodKeeper.load(DATA, auto_download=False)
    main.app.dependency_overrides = {}
    orig = main.db
    main.db = lambda: fk
    yield TestClient(main.app)
    main.db = orig


def test_loads_everything(client):
    assert client.get("/").json()["items"] > 600
    assert len(client.get("/categories").json()) > 20


@pytest.mark.parametrize("q,expected", [
    ("milk", "Milk (plain or flavored)"), ("eggs", "Eggs (in shell)"), ("ground beef", "Beef (ground)"),
    ("tomato", "Tomatoes"), ("yogurt", "Yogurt"), ("mlik", "Milk (plain or flavored)"),
])
def test_search(client, q, expected):
    assert client.get("/search", params={"q": q}).json()["results"][0]["display_name"] == expected


def test_expiry_examples(client):
    milk = client.get("/expiry", params={"q": "milk"}).json()
    assert milk["status"] == "no_estimate" and milk["guidance"] == "Package use-by date"
    eggs = client.get("/expiry", params={"q": "eggs"}).json()
    assert eggs["condition"] == "from_purchase_date" and eggs["days_left"] == 35  # 3-5 weeks
    beef = client.get("/expiry", params={"q": "ground beef", "location": "freezer"}).json()
    assert beef["days_left"] > 0


def test_every_food_has_valid_expiry_response(client):
    for fid in list(main.db().foods)[:]:
        for loc in ("pantry", "refrigerator", "freezer"):
            assert client.get("/expiry", params={"item_id": fid, "location": loc}).status_code == 200
