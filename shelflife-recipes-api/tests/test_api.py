"""Tests run against a tiny made-up fixture with the same shape as foodkeeper.json."""
import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import main
from app.data import FoodKeeper

FIXTURE = {
    "sheets": [
        {"name": "Category", "data": [
            [{"ID": 1}, {"Category_Name": "Dairy Products & Eggs"}, {"Subcategory_Name": None}],
            [{"ID": 2}, {"Category_Name": "Produce"}, {"Subcategory_Name": "Fresh Fruits"}],
        ]},
        {"name": "Product", "data": [
            [{"ID": 10}, {"Category_ID": 1}, {"Name": "Milk"}, {"Name_subtitle": "plain or flavored"},
             {"Keywords": "Milk,dairy"}, {"Pantry_Min": None}, {"Pantry_Max": None}, {"Pantry_Metric": None},
             {"Refrigerate_Min": 1}, {"Refrigerate_Max": 1}, {"Refrigerate_Metric": "Weeks"},
             {"Refrigerate_tips": "Keep cold"}, {"Freeze_Min": 3}, {"Freeze_Max": 3}, {"Freeze_Metric": "Months"},
             {"Refrigerate_After_Opening_Min": 7}, {"Refrigerate_After_Opening_Max": 7},
             {"Refrigerate_After_Opening_Metric": "Days"}],
            [{"ID": 11}, {"Category_ID": 2}, {"Name": "Bananas"}, {"Name_subtitle": None},
             {"Keywords": "Bananas,fruit"}, {"Pantry_Min": None}, {"Pantry_Max": None},
             {"Pantry_Metric": "When Ripe"}, {"Pantry_tips": "Store at room temp"},
             {"DOP_Refrigerate_Min": 3}, {"DOP_Refrigerate_Max": 5}, {"DOP_Refrigerate_Metric": "Days"}],
        ]},
    ]
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    p = tmp_path / "fk.json"
    p.write_text(json.dumps(FIXTURE))
    fk = FoodKeeper.load(p, auto_download=False)
    main.db.cache_clear()
    monkeypatch.setattr(main, "db", lambda: fk)
    return TestClient(main.app)


def test_parse_storage():
    fk = FoodKeeper(FIXTURE)
    milk = fk.foods[10]
    assert milk.category == "Dairy Products & Eggs"
    conds = {(s["location"], s["condition"]): s for s in milk.storage}
    assert conds[("refrigerator", "unopened")]["max_days"] == 7
    assert conds[("freezer", "unopened")]["max_days"] == 90
    assert conds[("refrigerator", "after_opening")]["min_days"] == 7
    banana = fk.foods[11]
    assert {(s["location"], s["condition"]) for s in banana.storage} == {
        ("pantry", "unopened"), ("refrigerator", "from_purchase_date")}


def test_search(client):
    r = client.get("/search", params={"q": "milk"}).json()
    assert r["results"][0]["name"] == "Milk"
    assert client.get("/search", params={"q": "banana"}).json()["results"][0]["name"] == "Bananas"
    assert client.get("/search", params={"q": "mlik"}).json()["results"][0]["name"] == "Milk"  # typo


def test_item_and_categories(client):
    assert client.get("/items/10").json()["display_name"] == "Milk (plain or flavored)"
    assert client.get("/items/999").status_code == 404
    assert len(client.get("/categories").json()) == 2
    assert client.get("/categories/2/items").json()["count"] == 1


def test_expiry(client):
    start = date.today() - timedelta(days=2)
    r = client.get("/expiry", params={"q": "milk", "location": "refrigerator", "start_date": str(start)}).json()
    assert r["use_by_latest"] == str(start + timedelta(days=7))
    assert r["days_left"] == 5 and r["status"] == "fresh"
    r = client.get("/expiry", params={"item_id": 10, "location": "freezer"}).json()
    assert r["days_left"] == 90
    r = client.get("/expiry", params={"q": "banana", "location": "pantry"}).json()
    assert r["estimate"] is None and r["guidance"] == "When Ripe"
