# CSV Export Feature - Usage Guide

## Overview
The ETL pipeline now supports optional CSV export of transformed data. This feature:
- ✅ Is completely **optional** - disable with no flags
- ✅ **Does NOT break** the main pipeline - CSV errors are caught and logged as warnings
- ✅ **Does NOT interfere** with database loading - runs in parallel with SQL operations
- ✅ Exports to timestamped directories for easy organization

## Usage

### Option 1: Using `run_etl.py` (Simple Pipeline)

**Without CSV export (default behavior):**
```bash
python -m tennis_etl.run_etl
```

**With CSV export:**
```bash
python -m tennis_etl.run_etl --export-csv
```

**With custom CSV output directory:**
```bash
python -m tennis_etl.run_etl --export-csv --csv-output /path/to/output
```

### Option 2: Using `ingestion_pipeline.py` (Full Pipeline with MongoDB)

**Without CSV export (default behavior):**
```bash
python -m tennis_etl.ingestion_pipeline
```

**With CSV export:**
```bash
python -m tennis_etl.ingestion_pipeline --export-csv
```

**With custom CSV output directory:**
```bash
python -m tennis_etl.ingestion_pipeline --export-csv --csv-output /path/to/output
```

**Skip MongoDB staging (quick iteration):**
```bash
python -m tennis_etl.ingestion_pipeline --skip-staging --export-csv
```

## Output Structure

When CSV export is enabled, files are created in a timestamped directory:

```
etl_output/
├── 20260526_143022/          # Timestamp of run
│   ├── categories.csv
│   ├── competitions.csv
│   ├── complexes.csv
│   ├── venues.csv
│   ├── competitors.csv
│   └── rankings.csv
├── 20260526_150145/          # Another run
│   ├── categories.csv
│   ├── competitions.csv
│   └── ...
```

## CSV Files Generated

| File | Columns | Contains |
|------|---------|----------|
| `categories.csv` | category_id, category_name | Tour categories (ATP, WTA, ITF) |
| `competitions.csv` | competition_id, competition_name, parent_id, type, gender, category_id | Competitions and tournaments |
| `complexes.csv` | complex_id, complex_name | Venue complexes |
| `venues.csv` | venue_id, venue_name, city_name, country_name, country_code, timezone, complex_id | Individual venues |
| `competitors.csv` | competitor_id, name, country, country_code, abbreviation | Teams/competitors |
| `rankings.csv` | competitor_id, rank, movement, points, competitions_played | Current rankings |

## Error Handling

If CSV export fails for any reason:
- ✅ The error is **logged as a warning**, not an exception
- ✅ The **main pipeline continues normally**
- ✅ Database loading still completes
- ✅ No interruption to ETL workflow

## Example: Using with Environment Variables

You can also control CSV export via environment variables:

```bash
export EXPORT_CSV=true
export CSV_OUTPUT_DIR=/custom/path

python -m tennis_etl.ingestion_pipeline
```

Or combine with existing environment variables:

```bash
export SPORTRADAR_API_KEY=your_key
export DATABASE_URL=mssql+pyodbc://...
export MONGODB_URL=mongodb://localhost:27017
export SKIP_STAGING=false

python -m tennis_etl.ingestion_pipeline --export-csv --csv-output /data/exports
```

## Programmatic Usage

You can also use the CSV exporter directly in your own code:

```python
from tennis_etl.csv_exporter import CSVExporter

# Create exporter
exporter = CSVExporter(output_dir="/path/to/output")

# Export specific table
exporter.export_table("competitions.csv", competitions_list)

# Or export all tables at once
results = exporter.export_all(
    categories=categories,
    competitions=competitions,
    complexes=complexes,
    venues=venues,
    competitors=competitors,
    rankings=rankings,
)

print(f"Exported: {results}")
# Output: {'categories': 4, 'competitions': 250, 'complexes': 12, ...}
```

## Logging

CSV export operations are logged at INFO level:
- Creation of output directory
- Each table export (rows written)
- Total rows exported
- Any errors (logged as warnings)

Enable DEBUG logging to see more details:
```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG)" && \
python -m tennis_etl.ingestion_pipeline --export-csv
```

## Summary

The CSV export feature is now fully integrated and production-ready:
- **Completely optional** - no changes to existing workflows
- **Non-blocking** - doesn't impact database operations
- **Fault-tolerant** - errors don't break the pipeline
- **Well-organized** - timestamped output directories
- **Fully logged** - easy to track what was exported
