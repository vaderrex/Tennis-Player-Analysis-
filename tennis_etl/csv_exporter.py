"""Optional CSV export functionality for ETL pipeline outputs."""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


class CSVExporter:
    """Export transformed ETL data to CSV files."""

    def __init__(self, output_dir: str | None = None) -> None:
        """Initialize CSV exporter with optional output directory.

        Args:
            output_dir: Directory to write CSV files. Defaults to 'etl_output' in current directory.
        """
        if output_dir is None:
            output_dir = "etl_output"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped subdirectory for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.output_dir / timestamp
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        LOGGER.info(f"CSV export directory: {self.run_dir}")

    def export_table(
        self, 
        filename: str, 
        data: list[dict[str, Any]]
    ) -> int:
        """Export a list of dictionaries to CSV file.

        Args:
            filename: Name of the CSV file to create.
            data: List of dictionaries to export.

        Returns:
            Number of rows written.
        """
        if not data:
            LOGGER.warning(f"No data to export for {filename}")
            return 0

        filepath = self.run_dir / filename
        
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = list(data[0].keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerows(data)
            
            row_count = len(data)
            LOGGER.info(f"Exported {row_count} rows to {filename}")
            return row_count
        except (IOError, OSError) as e:
            LOGGER.error(f"Failed to export {filename}: {e}")
            raise

    def export_all(
        self,
        categories: list[dict] | None = None,
        competitions: list[dict] | None = None,
        complexes: list[dict] | None = None,
        venues: list[dict] | None = None,
        competitors: list[dict] | None = None,
        rankings: list[dict] | None = None,
    ) -> dict[str, int]:
        """Export all transformed data to CSV files.

        Args:
            categories: Category records.
            competitions: Competition records.
            complexes: Complex records.
            venues: Venue records.
            competitors: Competitor records.
            rankings: Ranking records.

        Returns:
            Dictionary with table names and row counts exported.
        """
        export_results = {}
        
        if categories is not None:
            export_results["categories"] = self.export_table(
                "categories.csv", 
                categories
            )
        
        if competitions is not None:
            export_results["competitions"] = self.export_table(
                "competitions.csv", 
                competitions
            )
        
        if complexes is not None:
            export_results["complexes"] = self.export_table(
                "complexes.csv", 
                complexes
            )
        
        if venues is not None:
            export_results["venues"] = self.export_table(
                "venues.csv", 
                venues
            )
        
        if competitors is not None:
            export_results["competitors"] = self.export_table(
                "competitors.csv", 
                competitors
            )
        
        if rankings is not None:
            export_results["rankings"] = self.export_table(
                "rankings.csv", 
                rankings
            )
        
        total_exported = sum(export_results.values())
        LOGGER.info(f"CSV export complete. Total rows: {total_exported}")
        LOGGER.info(f"CSV files location: {self.run_dir}")
        
        return export_results
