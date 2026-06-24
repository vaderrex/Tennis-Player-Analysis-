# SportRadar Tennis API Smart Guide

Project guide for **Game Analytics: Unlocking Tennis Data with SportRadar API**.

## 1. What the PDF Requires

The supplied PDF describes an end-to-end sports analytics project using Python, SQL, SportRadar Tennis API feeds, and Streamlit.

Core requirements:

- Collect data from three SportRadar Tennis endpoints:
  - Competitions
  - Complexes
  - Doubles Competitor Rankings
- Transform nested JSON into a normalized SQL schema.
- Store the data in six tables:
  - Categories
  - Competitions
  - Complexes
  - Venues
  - Competitors
  - Competitor_Rankings
- Write analytical SQL queries for competitions, venues, and competitors.
- Build a Streamlit dashboard with filters, charts, tables, competitor details, country analysis, and leaderboards.
- Upload code, SQL queries, README, and documentation to GitHub.

## 2. Official SportRadar Endpoint Patterns

Use Tennis API v3 with JSON format.

| Feed | Endpoint pattern | Purpose |
|---|---|---|
| Competitions | `GET https://api.sportradar.com/tennis/{access_level}/v3/{language_code}/competitions.{format}` | Returns all competitions. |
| Complexes | `GET https://api.sportradar.com/tennis/{access_level}/v3/{language_code}/complexes.{format}` | Returns complexes and nested venues. |
| Doubles Competitor Rankings | `GET https://api.sportradar.com/tennis/{access_level}/v3/{language_code}/double_competitors_rankings.{format}` | Returns top 500 ATP/WTA doubles rankings. |

Recommended environment variables:

```powershell
$env:SPORTRADAR_API_KEY = "your-key"
$env:SPORTRADAR_ACCESS_LEVEL = "trial"
$env:SPORTRADAR_LANGUAGE_CODE = "en"
$env:DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/tennis_rankings"
```

## 3. Python API Request Pattern

```python
import os
import requests

BASE_URL = "https://api.sportradar.com/tennis"
API_KEY = os.getenv("SPORTRADAR_API_KEY")
ACCESS_LEVEL = os.getenv("SPORTRADAR_ACCESS_LEVEL", "trial")
LANGUAGE = os.getenv("SPORTRADAR_LANGUAGE_CODE", "en")


def get_feed(endpoint: str) -> dict:
    if not API_KEY:
        raise ValueError("SPORTRADAR_API_KEY is missing")

    url = f"{BASE_URL}/{ACCESS_LEVEL}/v3/{LANGUAGE}/{endpoint}.json"
    response = requests.get(
        url,
        headers={"x-api-key": API_KEY},
        timeout=20,
    )

    if response.status_code == 429:
        raise RuntimeError("Rate limit reached; wait before retrying")

    response.raise_for_status()
    return response.json()


competitions = get_feed("competitions")
complexes = get_feed("complexes")
rankings = get_feed("double_competitors_rankings")
```

## 4. ETL Workflow

1. Fetch `competitions`, `complexes`, and `double_competitors_rankings`.
2. Validate each JSON response.
3. Flatten nested objects into SQL-ready rows.
4. Load tables in foreign-key order:
   - Categories before Competitions
   - Complexes before Venues
   - Competitors before Competitor_Rankings
5. Use upsert logic so reruns do not duplicate records.
6. Query SQL tables into Pandas DataFrames.
7. Render Streamlit dashboard views from DataFrames.

## 5. Image-Based Analysis Extension

The PDF does not require image analysis, but it can be added as an innovation layer while staying local/free.

Suggested features:

| Feature | Local implementation | Streamlit output |
|---|---|---|
| Upload court/player image | `st.file_uploader` plus Pillow/OpenCV | Preview, dimensions, aspect ratio, brightness, blur score |
| OCR screenshots | Tesseract/local OCR if installed | Extract names/ranks from screenshots |
| Dashboard screenshot QA | Local image checks | Detect blank or broken chart screenshots |
| Image enrichment | Optional `images` SQL table | Competitor profile image and alt text |

Optional schema:

```sql
CREATE TABLE images (
    image_id SERIAL PRIMARY KEY,
    entity_type VARCHAR(40) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    image_path TEXT NOT NULL,
    source_url TEXT,
    alt_text TEXT,
    width_px INT,
    height_px INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Streamlit workflow:

1. Add a sidebar link called `Image Analysis`.
2. Upload PNG/JPG files with `st.file_uploader`.
3. Use Pillow to calculate image dimensions, brightness, and sharpness.
4. Show warnings for blurry or too-small images.
5. Optionally match OCR-detected text to competitors in the database.

## 6. Testing and Rate-Limit Safety

- Cache API responses during development.
- Test transforms with saved sample JSON before repeated live calls.
- Handle `401`, `429`, and `5xx` errors clearly.
- Keep API keys out of code and GitHub.
- Use local image processing tools instead of paid image APIs.

## 7. Execution Checklist

1. Create a SportRadar account and get an API key.
2. Set environment variables.
3. Create the SQL schema.
4. Run the ETL.
5. Confirm row counts in all six tables.
6. Run analytical query functions.
7. Start Streamlit.
8. Verify all dashboard views.
9. Add the optional image-analysis page.
10. Upload code, SQL, README, and documentation to GitHub.

## Sources

- PDF: `Game Analytics_ Unlocking Tennis Data with SportRadar API (1)-2 (1).pdf`
- SportRadar Competitions: https://developer.sportradar.com/tennis/reference/competitions
- SportRadar Complexes: https://developer.sportradar.com/tennis/reference/complexes
- SportRadar Doubles Competitor Rankings: https://developer.sportradar.com/tennis/reference/doubles-competitor-rankings
- SportRadar signup: https://console.sportradar.com/signup
- Streamlit API reference: https://docs.streamlit.io/library/api-reference
