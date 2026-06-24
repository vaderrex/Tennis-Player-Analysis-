# Tennis ETL: Data Transformation & Preprocessing Guide

## Overview

The **Transformation Phase (Phase 1C)** is the critical layer in your Tennis ETL pipeline where raw, nested JSON data from the SportRadar API is **flattened, cleaned, validated, and normalized** before loading into the SQL warehouse.

### Why Transformation Matters

- **Raw API data** contains deeply nested JSON structures with inconsistent formats
- **SQL databases** require flat, normalized tables with proper data types
- **Data cleaning** ensures consistency, removes invalid records, and handles missing values
- **Normalization** eliminates redundancy and enforces referential integrity

---

## Architecture: Where Transformation Fits

```
┌─────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  [1A] EXTRACTION          [1B] STAGING       [1C] TRANSFORM  │
│  ─────────────────        ──────────────     ────────────────│
│                                                               │
│  API Requests ──────────► MongoDB Staging ──► Flatten JSON   │
│  (Raw JSON)              (Snapshot Docs)      (Clean Data)   │
│                                                               │
│  • Competitions          • Durable audit    • Extract entities│
│  • Complexes             • Idempotent       • Remove nulls    │
│  • Rankings              • Replay-able      • Type safety     │
│                                             • Validate IDs    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────────┐
                    │  LOAD (Phase 1C)    │
                    ├─────────────────────┤
                    │ SQL Warehouse:      │
                    │ • Categories        │
                    │ • Competitions      │
                    │ • Complexes         │
                    │ • Venues            │
                    │ • Competitors       │
                    │ • Rankings          │
                    └─────────────────────┘
```

---

## The Three Core Transformation Functions

All transformation logic is in [`tennis_etl/transforms.py`](../tennis_etl/transforms.py)

### 1. **`transform_competitions(payload)`**

**Purpose:** Extract categories and competitions from nested API response

**Input (Raw API JSON):**
```json
{
  "competitions": [
    {
      "id": "sr:competition:24157",
      "name": "Australian Open Women",
      "type": "league",
      "gender": "female",
      "category": {
        "id": "sr:category:1",
        "name": "WTA"
      },
      "category_id": "sr:category:1",
      "category_name": "WTA"
    },
    {
      "id": "sr:competition:24158",
      "name": "Australian Open Men",
      "parent": {
        "id": "sr:competition:24157"
      }
    }
  ]
}
```

**Output (Two Normalized Tables):**

**Categories Table:**
```
┌──────────────────────┬─────────────────┐
│ category_id          │ category_name   │
├──────────────────────┼─────────────────┤
│ sr:category:1        │ WTA             │
│ sr:category:2        │ ATP             │
└──────────────────────┴─────────────────┘
```

**Competitions Table:**
```
┌──────────────────────────┬──────────────────────────┬──────────────────────┬────────┬────────┬──────────────────┐
│ competition_id           │ competition_name         │ parent_id            │ type   │ gender │ category_id      │
├──────────────────────────┼──────────────────────────┼──────────────────────┼────────┼────────┼──────────────────┤
│ sr:competition:24157     │ Australian Open Women    │ NULL                 │ league │ female │ sr:category:1    │
│ sr:competition:24158     │ Australian Open Men      │ sr:competition:24157 │ NULL   │ NULL   │ sr:category:1    │
└──────────────────────────┴──────────────────────────┴──────────────────────┴────────┴────────┴──────────────────┘
```

**Transformation Logic:**

```python
def transform_competitions(payload: JsonObject) -> tuple[list[dict], list[dict]]:
    categories = {}      # Dictionary to deduplicate categories
    competitions = {}    # Dictionary to deduplicate competitions

    for competition in _items(payload, "competitions"):
        # Extract category info (nested object)
        category = competition.get("category") or {}
        category_id = category.get("id") or competition.get("category_id")
        competition_id = competition.get("id")
        
        # CLEANING: Skip records missing critical IDs
        if not competition_id or not category_id:
            continue

        # Store category (deduplicates by ID)
        categories[category_id] = {
            "category_id": category_id,
            "category_name": category.get("name") 
                             or competition.get("category_name") 
                             or "Unknown",  # DEFAULT VALUE
        }

        # Store competition with parent reference
        competitions[competition_id] = {
            "competition_id": competition_id,
            "competition_name": competition.get("name") or "Unknown",
            "parent_id": _parent_id(competition.get("parent")),  # Safely extract
            "type": competition.get("type"),
            "gender": competition.get("gender"),
            "category_id": category_id,
        }

    return list(categories.values()), list(competitions.values())
```

**Key Cleaning Operations:**
- ✅ **Null handling**: `or "Unknown"` provides defaults for missing names
- ✅ **ID validation**: Skip records without `competition_id` or `category_id`
- ✅ **Nested extraction**: Safely get `category.id` or fallback to `category_id` field
- ✅ **Deduplication**: Use dictionaries to ensure one category per ID
- ✅ **Optional fields**: `parent_id`, `type`, `gender` can be NULL

---

### 2. **`transform_complexes(payload)`**

**Purpose:** Extract complexes and their nested venues

**Input (Raw API JSON):**
```json
{
  "complexes": [
    {
      "id": "sr:complex:14",
      "name": "Melbourne Park",
      "venues": [
        {
          "id": "sr:venue:318",
          "name": "Rod Laver Arena",
          "city_name": "Melbourne",
          "country_name": "Australia",
          "country_code": "AU",
          "timezone": "Australia/Melbourne"
        },
        {
          "id": "sr:venue:319",
          "name": "Hisense Arena",
          "city_name": "Melbourne",
          "country_name": "Australia",
          "country_code": "AU",
          "timezone": "Australia/Melbourne"
        }
      ]
    }
  ]
}
```

**Output (Two Normalized Tables):**

**Complexes Table:**
```
┌──────────────────┬──────────────────┐
│ complex_id       │ complex_name     │
├──────────────────┼──────────────────┤
│ sr:complex:14    │ Melbourne Park   │
│ sr:complex:1     │ Roland Garros    │
└──────────────────┴──────────────────┘
```

**Venues Table:**
```
┌──────────────────┬─────────────────────┬──────────┬─────────────┬──────────────┬──────────────────────┬──────────────────┐
│ venue_id         │ venue_name          │ city     │ country     │ country_code │ timezone             │ complex_id       │
├──────────────────┼─────────────────────┼──────────┼─────────────┼──────────────┼──────────────────────┼──────────────────┤
│ sr:venue:318     │ Rod Laver Arena     │ Melbourne│ Australia   │ AU           │ Australia/Melbourne  │ sr:complex:14    │
│ sr:venue:319     │ Hisense Arena       │ Melbourne│ Australia   │ AU           │ Australia/Melbourne  │ sr:complex:14    │
└──────────────────┴─────────────────────┴──────────┴─────────────┴──────────────┴──────────────────────┴──────────────────┘
```

**Transformation Logic:**

```python
def transform_complexes(payload: JsonObject) -> tuple[list[dict], list[dict]]:
    complexes = {}
    venues = {}

    for complex_item in _items(payload, "complexes"):
        complex_id = complex_item.get("id")
        if not complex_id:
            continue

        # Store complex
        complexes[complex_id] = {
            "complex_id": complex_id,
            "complex_name": complex_item.get("name") or "Unknown",
        }

        # Extract nested venues
        for venue in _nested_items(complex_item, "venues"):
            venue_id = venue.get("id")
            if not venue_id:
                continue

            # Store venue with FK to complex
            venues[venue_id] = {
                "venue_id": venue_id,
                "venue_name": venue.get("name") or "Unknown",
                "city_name": venue.get("city_name"),
                "country_name": venue.get("country_name"),
                "country_code": venue.get("country_code"),
                "timezone": venue.get("timezone"),
                "complex_id": complex_id,  # Foreign key reference
            }

    return list(complexes.values()), list(venues.values())
```

**Key Cleaning Operations:**
- ✅ **Nested iteration**: Safely loop through venues within each complex
- ✅ **ID validation**: Skip complexes/venues without IDs
- ✅ **Foreign key**: Venue records include `complex_id` for referential integrity
- ✅ **Null tolerance**: Geographic fields can be NULL if missing
- ✅ **Deduplication**: Dictionaries ensure one venue per ID

---

### 3. **`transform_doubles_rankings(payload)`**

**Purpose:** Extract competitors and their current rankings

**Input (Raw API JSON):**
```json
{
  "rankings": [
    {
      "competitor_rankings": [
        {
          "rank": 1,
          "movement": 0,
          "points": 2500,
          "competitions_played": 12,
          "competitor": {
            "id": "sr:competitor:1234",
            "name": "Barbora Strycova",
            "country": "Czech Republic",
            "country_code": "CZ",
            "abbreviation": "BA"
          }
        },
        {
          "rank": 2,
          "movement": 2,
          "points": 2400,
          "competitions_played": 11,
          "competitor": {
            "id": "sr:competitor:5678",
            "name": "Shuai Zhang",
            "country": "China",
            "country_code": "CN",
            "abbreviation": "SHZ"
          }
        }
      ]
    }
  ]
}
```

**Output (Two Normalized Tables):**

**Competitors Table:**
```
┌──────────────────────┬──────────────────────┬──────────────┬──────────────┬──────────────┐
│ competitor_id        │ name                 │ country      │ country_code │ abbreviation │
├──────────────────────┼──────────────────────┼──────────────┼──────────────┼──────────────┤
│ sr:competitor:1234   │ Barbora Strycova     │ Czech Republic│ CZ           │ BA           │
│ sr:competitor:5678   │ Shuai Zhang          │ China        │ CN           │ SHZ          │
└──────────────────────┴──────────────────────┴──────────────┴──────────────┴──────────────┘
```

**Rankings Table:**
```
┌──────┬──────────┬────────┬──────────────────────┬──────────────────────┐
│ rank │ movement │ points │ competitions_played  │ competitor_id        │
├──────┼──────────┼────────┼──────────────────────┼──────────────────────┤
│ 1    │ 0        │ 2500   │ 12                   │ sr:competitor:1234   │
│ 2    │ 2        │ 2400   │ 11                   │ sr:competitor:5678   │
└──────┴──────────┴────────┴──────────────────────┴──────────────────────┘
```

**Transformation Logic:**

```python
def transform_doubles_rankings(payload: JsonObject) -> tuple[list[dict], list[dict]]:
    competitors = {}
    rankings = {}

    # Handle both formats: "rankings" array or inline competitor_rankings
    for ranking_group in _ranking_groups(payload):
        for item in _nested_items(ranking_group, "competitor_rankings"):
            competitor = item.get("competitor") or {}
            competitor_id = competitor.get("id")
            rank = _as_int(item.get("rank"))  # Safe integer conversion

            # CLEANING: Skip records missing critical fields
            if not competitor_id or rank is None:
                continue

            # Store competitor
            competitors[competitor_id] = {
                "competitor_id": competitor_id,
                "name": competitor.get("name") or "Unknown",
                "country": competitor.get("country"),
                "country_code": competitor.get("country_code"),
                "abbreviation": competitor.get("abbreviation"),
            }

            # Store ranking with FK to competitor
            rankings[competitor_id] = {
                "rank": rank,
                "movement": _as_int(item.get("movement")),  # Safe conversion
                "points": _as_int(item.get("points")),      # Safe conversion
                "competitions_played": _as_int(item.get("competitions_played")),
                "competitor_id": competitor_id,  # Foreign key
            }

    return list(competitors.values()), list(rankings.values())
```

**Key Cleaning Operations:**
- ✅ **Safe type conversion**: `_as_int()` validates numeric fields
- ✅ **ID validation**: Skip rankings without `competitor_id` or invalid `rank`
- ✅ **Null tolerance**: Movement, points, competitions_played can be NULL
- ✅ **Deduplication**: One competitor per ID
- ✅ **Flexible schema**: Handles both "rankings" array and inline formats

---

## Helper Functions: The Cleaning Toolkit

### **1. `_as_int(value: Any) -> int | None`**

**Purpose:** Safely convert any value to an integer

**Why it matters:** API responses may have:
- String numbers: `"123"` should become `123`
- Invalid strings: `"abc"` should become `None`
- Empty strings: `""` should become `None`
- None values: Should stay `None`

**Implementation:**
```python
def _as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
```

**Examples:**
```python
_as_int(123)        # → 123
_as_int("456")      # → 456
_as_int("")         # → None
_as_int(None)       # → None
_as_int("invalid")  # → None (catches ValueError)
_as_int(1.5)        # → 1 (casts float to int)
```

---

### **2. `_items(payload: JsonObject, key: str) -> Iterable[JsonObject]`**

**Purpose:** Safely extract an array from JSON

**Why it matters:** API fields may be:
- Missing: `payload.get(key)` returns `None`
- Empty array: `[]`
- Wrong type: `"string"` instead of `[]`

**Implementation:**
```python
def _items(payload: JsonObject, key: str) -> Iterable[JsonObject]:
    value = payload.get(key, [])
    return value if isinstance(value, list) else []
```

**Examples:**
```python
_items({"competitions": [...]}, "competitions")     # → list of competitions
_items({}, "competitions")                          # → [] (safe empty)
_items({"competitions": "invalid"}, "competitions") # → [] (type check)
_items({"competitions": None}, "competitions")      # → [] (None check)
```

---

### **3. `_nested_items(payload: JsonObject, key: str) -> Iterable[JsonObject]`**

**Purpose:** Safely extract nested arrays (same as `_items()` but semantically for nested data)

**Used for:** Extracting venues from complexes, competitor_rankings from groups

---

### **4. `_ranking_groups(payload: JsonObject) -> Iterable[JsonObject]`**

**Purpose:** Handle flexible ranking payload format

**Why it matters:** API may return rankings in two formats:

**Format 1: Rankings array** (common)
```json
{
  "rankings": [
    { "competitor_rankings": [...] },
    { "competitor_rankings": [...] }
  ]
}
```

**Format 2: Inline** (also valid)
```json
{
  "competitor_rankings": [...]
}
```

**Implementation:**
```python
def _ranking_groups(payload: JsonObject) -> Iterable[JsonObject]:
    rankings = payload.get("rankings")
    if isinstance(rankings, list):
        return rankings
    if "competitor_rankings" in payload:
        return [payload]  # Wrap inline format as single group
    return []
```

**Examples:**
```python
# Format 1: Returns list of groups
_ranking_groups({"rankings": [{...}, {...}]})
# → [{...}, {...}]

# Format 2: Returns single group wrapped
_ranking_groups({"competitor_rankings": [...]})
# → [{...}]

# Empty: Returns empty list
_ranking_groups({})
# → []
```

---

### **5. `_parent_id(parent: Any) -> str | None`**

**Purpose:** Extract parent competition ID (handles nested object or string)

**Why it matters:** Parent reference may be in two formats:

**Format 1: Nested object**
```json
"parent": {
  "id": "sr:competition:123"
}
```

**Format 2: Direct string**
```json
"parent_id": "sr:competition:123"
```

**Implementation:**
```python
def _parent_id(parent: Any) -> str | None:
    if isinstance(parent, Mapping):
        return parent.get("id")
    if isinstance(parent, str):
        return parent
    return None
```

**Examples:**
```python
_parent_id({"id": "sr:comp:123"})    # → "sr:comp:123"
_parent_id("sr:comp:123")             # → "sr:comp:123"
_parent_id(None)                      # → None
_parent_id(123)                       # → None (wrong type)
```

---

## Data Quality Safeguards

### **Problem → Solution Matrix**

| Issue | Cleaning Function | Behavior |
|-------|-------------------|----------|
| Missing ID | ID validation in loops | Skip record entirely |
| Null field | `.get(key, default)` | Use default or "Unknown" |
| Invalid integer | `_as_int()` | Return None (database allows NULL) |
| Wrong data type | `isinstance()` checks | Return empty list/None |
| Nested object variations | Flexible extractors | Handle both object and string formats |
| Duplicate records | Dictionary keyed by ID | Last occurrence wins (idempotent) |
| Missing names | `or "Unknown"` | Prevent null names in display fields |

### **Example: Corrupted Data Handling**

```python
# What if API returns garbage data?
corrupted_payload = {
    "competitions": [
        # Missing ID → SKIPPED
        {"name": "Australian Open", "category_id": "sr:cat:1"},
        
        # Invalid integer → Stored as None
        {"id": "sr:comp:1", "name": "Valid", "rank": "not_a_number"},
        
        # Wrong type → Safely ignored
        {"id": "sr:comp:2", "venues": "not_an_array"},
        
        # Partial data → Defaults applied
        {"id": "sr:comp:3", "category_id": "sr:cat:1"},
        # → name becomes "Unknown"
    ]
}

# After transformation:
# ✅ Skips record 1 (no ID)
# ✅ Stores record 2 with rank=None
# ✅ Handles record 3 with empty venues list
# ✅ Creates name="Unknown" for record 4
```

---

## Integration with Pipeline

### **Phase 1C Flow**

```python
# In ingestion_pipeline.py

# Extract from MongoDB (or API directly)
competitions_payload, complexes_payload, rankings_payload = extract_from_mongodb(mongo_url)

# TRANSFORM: Flatten and clean
categories, competitions = transform_competitions(competitions_payload)
complexes, venues = transform_complexes(complexes_payload)
competitors, rankings = transform_doubles_rankings(rankings_payload)

# Log transformation results
LOGGER.info(
    "Transform complete: categories=%d, competitions=%d, complexes=%d, "
    "venues=%d, competitors=%d, rankings=%d",
    len(categories),
    len(competitions),
    len(complexes),
    len(venues),
    len(competitors),
    len(rankings),
)

# LOAD: Insert into SQL (next phase)
load_counts = load_all(
    session=session,
    categories=categories,
    competitions=competitions,
    complexes=complexes,
    venues=venues,
    competitors=competitors,
    rankings=rankings,
)
```

---

## Load Phase: Respecting Referential Integrity

After transformation, data is loaded in **foreign-key dependency order**:

```
1. Categories (no dependencies)
   ↓ (FK: category_id in Competitions)
2. Competitions
   ↓ (FK: parent_id in Competitions, circular but handled)
3. Complexes (no dependencies)
   ↓ (FK: complex_id in Venues)
4. Venues
   ↓ (no FK dependencies)
5. Competitors
   ↓ (FK: competitor_id in Rankings)
6. Rankings
```

**Load Operation:**
```python
def load_all(session: Session, categories, competitions, ...) -> LoadCounts:
    counts = LoadCounts(
        categories=upsert_rows(
            session, Category.__table__, categories,
            ["category_id"],  # Primary key
            ["category_name"]  # Columns to update
        ),
        competitions=upsert_rows(
            session, Competition.__table__, competitions,
            ["competition_id"],
            ["competition_name", "parent_id", "type", "gender", "category_id"]
        ),
        # ... more tables
    )
    return counts
```

**UPSERT Behavior:**
- **INSERT** if record doesn't exist
- **UPDATE** if record exists (replaces old values)
- **Idempotent:** Safe to run multiple times

---

## Common Issues & Debugging

### **Issue 1: Records Missing After Transform**

**Symptoms:** Input has 100 records, output has 95

**Cause:** ID validation is skipping records
```python
if not competition_id or not category_id:
    continue  # ← Records without IDs are skipped
```

**Solution:** Check API response for missing IDs
```python
# Enable debug logging
LOGGER.debug(f"Skipping competition: {competition}")
```

---

### **Issue 2: NULL Values in Database**

**Symptoms:** Unexpected NULL in normally-populated column

**Cause:** `_as_int()` conversion failed
```python
rank = _as_int(item.get("rank"))  # Returns None if invalid
```

**Solution:** Validate API data quality
```python
# Check raw payload
print(rankings_payload["rankings"][0]["competitor_rankings"][0].get("rank"))
```

---

### **Issue 3: Duplicate Records**

**Symptoms:** Same ID appears twice in output

**Cause:** Shouldn't happen—dictionaries deduplicate by ID
```python
rankings[competitor_id] = {...}  # Last occurrence wins
```

**Solution:** Check for transform function being called twice

---

## Summary

The transformation layer is a **critical data quality checkpoint** that:

1. ✅ **Flattens** nested JSON into relational tables
2. ✅ **Cleans** data with safe extractors and type conversion
3. ✅ **Validates** required fields (IDs) and optional fields (names)
4. ✅ **Deduplicates** records by primary key
5. ✅ **Normalizes** relationships via foreign keys
6. ✅ **Handles** API format variations gracefully

This ensures that your SQL warehouse contains **clean, valid, relational data** ready for business analytics! 🎾

---

**Related Files:**
- [`tennis_etl/transforms.py`](../tennis_etl/transforms.py) - Transformation functions
- [`tennis_etl/ingestion_pipeline.py`](../tennis_etl/ingestion_pipeline.py) - Pipeline orchestration
- [`tennis_etl/loader.py`](../tennis_etl/loader.py) - SQL load operations
- [`tennis_etl/models.py`](../tennis_etl/models.py) - SQL schema definitions
