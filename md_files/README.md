# Tennis Rankings Explorer - Phases 1-4

Phase 1 contains the backend ETL and relational schema for the SportRadar
Tennis v3 feeds:

- `competitions.json` for categories and competitions
- `complexes.json` for complexes and nested venues
- `double_competitors_rankings.json` for doubles competitors and rankings

The SQLAlchemy models create the required six tables:
`categories`, `competitions`, `complexes`, `venues`, `competitors`, and
`competitor_rankings`. SportRadar IDs are stored as primary keys so reruns can
upsert the same API entities. The ranking table uses the required auto-increment
`rank_id` and a unique `competitor_id` because this six-table Phase 1 schema
stores the current doubles ranking row per competitor.

## Phase 1 Architecture

The Phase 1 ingestion pipeline implements a three-layer architecture:

1. **API Extraction**: SportRadar Tennis v3 endpoints (Competitions, Complexes, Rankings)
2. **MongoDB Staging**: Raw JSON documents stored for durability and audit trail
3. **SQL Warehouse**: Normalized relational schema (6 tables) for analytics
## GitHub / Team Onboarding

This repository is prepared for collaborative development.

- Use `.env.example` to create a local `.env` file and keep secrets out of source control.
- Run tests locally before opening pull requests.
- Keep branches focused and use descriptive names such as `feature/` or `bugfix/`.
- A GitHub Actions workflow is configured in `.github/workflows/python-app.yml` to validate installs and run tests on push and pull request.

### Local setup for new team members

```powershell
git clone <repo-url>
cd Tennis
copy .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python test_ingestion_pipeline.py
```

### Recommended branch workflow

```powershell
git checkout -b feature/your-feature-name
git add .
git commit -m "Add <short description>"
git push origin feature/your-feature-name
```

### Run tests

```powershell
python test_ingestion_pipeline.py
```

### Run the pipeline

```powershell
python -m tennis_etl.ingestion_pipeline
```

### Streamlit dashboard

```powershell
streamlit run streamlit_app.py
```
### Configure

Install dependencies and set environment variables from `.env.example`.

#### Step 1: Create PostgreSQL Database

```sql
CREATE DATABASE tennis_rankings;
```

#### Step 2: Set Environment Variables

PostgreSQL example:

```powershell
$env:SPORTRADAR_API_KEY = "your-api-key-here"
$env:DATABASE_URL = "postgresql+psycopg://tennis_user:tennis_password@localhost:5432/tennis_rankings"
$env:MONGODB_URL = "mongodb://localhost:27017"
```

MySQL example:

```powershell
$env:SPORTRADAR_API_KEY = "your-api-key-here"
$env:DATABASE_URL = "mysql+pymysql://tennis_user:tennis_password@localhost:3306/tennis_rankings"
$env:MONGODB_URL = "mongodb://localhost:27017"
```

#### Step 3: Install Dependencies

```powershell
pip install -r requirements.txt
```

#### Step 4: Run the Full Ingestion Pipeline

The `ingestion_pipeline.py` orchestrates the complete three-layer flow:

```powershell
python -m tennis_etl.ingestion_pipeline
```

This command:
- Fetches raw data from SportRadar Tennis API (3 endpoints)
- Stages raw JSON responses into MongoDB (`tennis_staging` database)
- Extracts, flattens, and transforms nested structures
- Initializes SQL schema and loads normalized data with upserts

#### Alternative: Quick Test (Skip MongoDB Staging)

To iterate quickly without MongoDB:

```powershell
$env:SKIP_STAGING = "true"
python -m tennis_etl.ingestion_pipeline
```

### Technical Details

#### MongoDB Staging Layer

Raw API payloads are stored as single snapshot documents in MongoDB:
- Database: `tennis_staging`
- Collections: `raw_competitions`, `raw_complexes`, `raw_rankings`
- Storage: Each endpoint response stored with `_id: "current_snapshot"` for idempotent reruns
- Benefits: Audit trail, recovery capability, decoupled API and warehouse operations

#### SQL Warehouse Schema

Six normalized tables with foreign-key relationships:
- `categories` - Tour categories (ATP, WTA, ITF)
- `competitions` - Competition hierarchy
- `complexes` - Venue complexes
- `venues` - Nested venue details (city, country, timezone)
- `competitors` - Competitor/team information
- `competitor_rankings` - Current ranking snapshot per competitor

#### ETL Transforms

Raw nested API objects are flattened:
- Competitors array → Individual competitor + ranking rows
- Venues array nested in complexes → Individual venue rows with complex_id FK
- Hierarchical competitions → Flat rows with parent_id self-reference
- Type conversions: String numbers → integers, null handling

#### SQLAlchemy Upserts

Dialect-aware upsert strategy:
- **PostgreSQL**: `ON CONFLICT DO UPDATE` (efficient)
- **MySQL**: `ON DUPLICATE KEY UPDATE` (efficient)
- **Other**: Merge/lookup fallback (slower, for development)

All upserts use SportRadar IDs as primary keys for idempotent retries.

### Direct Schema Creation (Advanced)

To create tables without running the pipeline:

```powershell
python -m tennis_etl.create_schema
```

To skip MongoDB staging and run direct API→SQL ETL:

```powershell
python -m tennis_etl.run_etl
```

Raw DDL equivalents live in `sql/postgresql_schema.sql` and
`sql/mysql_schema.sql`.

## Analytical Queries

Phase 2 query wrappers live in `tennis_etl/queries.py`. Each function executes
parameterized SQL and returns a Pandas DataFrame for Streamlit:

```python
from tennis_etl.queries import (
    competitions_by_category,
    highest_points_current_week,
    venues_by_country,
)

itf_men = competitions_by_category("ITF Men")
french_venues = venues_by_country("France")
points_leaders = highest_points_current_week()
```

Functions accept an optional SQLAlchemy engine or database URL when a dashboard
should reuse a connection target explicitly. Without one, they read
`DATABASE_URL`. The Phase 1 schema does not include a ranking week column, so
`highest_points_current_week()` reports the highest points in the currently
loaded ranking snapshot.

## Streamlit Dashboard

Phase 3 introduces the dark Streamlit shell and the Home Dashboard:

```powershell
streamlit run streamlit_app.py
```

The Streamlit app uses Phase 2 DataFrame query wrappers for competitions and
current competitor rankings. It renders sidebar filters, Quick Links
navigation, the Home Dashboard, paginated filtered rankings, competitor
details, country-wise analysis, and leaderboard podiums with transparent dark
Plotly surfaces.

The six-table Phase 1 schema does not store player age, turned-pro date, career
titles, win/loss record, or 52 weekly rank snapshots. Phase 4 shows those
profile fields as not captured and anchors the rank-history chart to the
current loaded snapshot until a history/profile feed is added to the ETL.
