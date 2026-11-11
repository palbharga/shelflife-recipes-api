# ShelfLife + Recipes API

A copy of the ShelfLife API that also connects directly to **TheMealDB** (recipes).

A REST API for food shelf life (pantry / fridge / freezer) covering 661 foods from the
**USDA FSIS FoodKeeper** dataset (public domain, CC0). The data is already included in `data/`,
so nothing needs to download.

## Start it (easiest)

- **Mac:** double-click `start-mac.command`
  (first time: right-click it, choose **Open**, then **Open** again, because macOS blocks unknown files)
- **Windows:** double-click `start-windows.bat`
  (if a blue "Windows protected your PC" box appears: **More info**, then **Run anyway**)

The first run takes about a minute to set up, then your browser opens **http://127.0.0.1:8000/docs**.
Leave the black window open while you use the API. Press **Ctrl+C** in it to stop.

You only need Python 3.10+ installed (https://www.python.org/downloads/).

## Start it (manually, e.g. in the VS Code terminal)

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

## Online version (Render)

This repo includes `render.yaml`, so Render can deploy it directly from GitHub (free plan).
Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
Free services sleep after ~15 minutes idle; the first request after that takes ~30-60 seconds.

## Endpoints

| Path | What it does | Example |
|---|---|---|
| `/search?q=` | Find foods (typos OK) | `/search?q=strawberries` |
| `/items/{id}` | One food's full storage info | `/items/113` |
| `/categories` | All 25 categories | `/categories` |
| `/categories/{id}/items` | Foods in a category | `/categories/18/items` |
| `/expiry` | Use-by date, days left, status | `/expiry?q=chicken&location=refrigerator&start_date=2026-11-08` |

`/expiry` options:
- `location`: `pantry`, `refrigerator` (default), `freezer`
- `condition`: `unopened`, `from_purchase_date`, `after_opening`, `after_thawing` (optional)
- `start_date`: purchase/open date `YYYY-MM-DD` (default today)

`status` is `fresh`, `use_soon`, `expired`, or `no_estimate`. With `no_estimate`, the `guidance`
field holds USDA's advice instead of a number, e.g. "Package use-by date", "When Ripe",
"Indefinitely", or "Not Recommended".

### Example: `/expiry?q=chicken`
```json
{"item":{"id":113,"name":"Chicken (whole)"},"location":"refrigerator","condition":"from_purchase_date",
 "start_date":"2026-11-11","use_by_earliest":"2026-11-12","use_by_latest":"2026-11-13",
 "days_left":2,"status":"fresh","tips":null}
```

## TheMealDB endpoints (exact pass-through)

Same endpoint names and parameters as TheMealDB, with `/mealdb` in front. Responses are
TheMealDB's JSON, unchanged, just pretty-printed. Uses the free test key `1`
(set a `MEALDB_KEY` environment variable on Render if you buy a supporter key).

| This API | Calls TheMealDB | What it does |
|---|---|---|
| `/mealdb/search.php?s=Arrabiata` | `search.php?s=Arrabiata` | Search meals by name |
| `/mealdb/search.php?f=a` | `search.php?f=a` | Meals by first letter |
| `/mealdb/lookup.php?i=52772` | `lookup.php?i=52772` | Full meal details by ID |
| `/mealdb/random.php` | `random.php` | One random meal |
| `/mealdb/categories.php` | `categories.php` | Categories with descriptions |
| `/mealdb/list.php?c=list` | `list.php?c=list` | Category names |
| `/mealdb/list.php?a=list` | `list.php?a=list` | Areas / cuisines |
| `/mealdb/list.php?i=list` | `list.php?i=list` | All ingredients |
| `/mealdb/filter.php?i=chicken_breast` | `filter.php?i=chicken_breast` | Meals by main ingredient |
| `/mealdb/filter.php?c=Seafood` | `filter.php?c=Seafood` | Meals by category |
| `/mealdb/filter.php?a=Canadian` | `filter.php?a=Canadian` | Meals by area |

## Use it from your app

```js
const r = await fetch("http://127.0.0.1:8000/expiry?q=eggs&location=refrigerator");
const data = await r.json();   // data.days_left, data.status
```

```python
import requests
requests.get("http://127.0.0.1:8000/search", params={"q": "spinach"}).json()
```

## Tests
```bash
pytest -q
```

Data source: USDA Food Safety and Inspection Service, FoodKeeper
(https://catalog.data.gov/dataset/fsis-foodkeeper-data).
