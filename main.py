"""Main entrypoint for the data pipeline.

Extracts data using AuthManager credentials, transforms and validates records,
and outputs structured results.
"""

import argparse
import datetime
import json
import logging
import sys
from typing import Any, Dict, List, Optional

from auth import AuthManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("data_pipeline")


def extract_data(auth: AuthManager, limit: int = 10) -> List[Dict[str, Any]]:
    """Simulate extracting data from an external authenticated source."""
    logger.info("Extracting data with authenticated headers...")
    headers = auth.get_headers()

    # In production, this would make an authenticated HTTP request using headers
    # Here we simulate fetching upstream records
    logger.info("Authenticated using User-Agent: %s", headers.get("User-Agent"))

    sample_records = [
        {"id": i, "name": f"Sensor-{i}", "reading": 20.0 + (i * 1.5), "status": "active" if i % 2 == 0 else "idle"}
        for i in range(1, limit + 1)
    ]
    logger.info("Extracted %d records.", len(sample_records))
    return sample_records


def transform_data(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform and enrich raw records."""
    logger.info("Transforming %d records...", len(records))
    transformed = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for item in records:
        reading_celsius = item.get("reading", 0.0)
        reading_fahrenheit = round((reading_celsius * 9 / 5) + 32, 2)
        transformed_item = {
            "record_id": item["id"],
            "device_name": item["name"].lower(),
            "status": item["status"].upper(),
            "temp_celsius": reading_celsius,
            "temp_fahrenheit": reading_fahrenheit,
            "processed_at": now,
        }
        transformed.append(transformed_item)

    logger.info("Transformation complete.")
    return transformed


def load_data(records: List[Dict[str, Any]], output_path: str) -> None:
    """Save transformed records to output file or print summary."""
    logger.info("Loading %d records to %s...", len(records), output_path)
    output_payload = {
        "metadata": {
            "total_records": len(records),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        "data": records,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    logger.info("Successfully loaded data to %s", output_path)


def run_pipeline(
    output_path: str = "pipeline_output.json",
    limit: int = 5,
    exporter: str = "file",
    bq_project: Optional[str] = None,
    bq_dataset: Optional[str] = None,
    bq_table: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute end-to-end data pipeline."""
    logger.info("Starting Data Pipeline execution...")
    auth = AuthManager()
    raw_data = extract_data(auth, limit=limit)
    transformed_data = transform_data(raw_data)

    if exporter == "bigquery":
        from exporters.bigquery_exporter import BigQueryExporter

        bq_exp = BigQueryExporter(
            project_id=bq_project,
            dataset_id=bq_dataset,
            table_id=bq_table,
        )
        export_details = bq_exp.export_records(transformed_data)
        logger.info("Pipeline completed successfully with BigQuery export.")
        return {
            "status": "SUCCESS",
            "exporter": "bigquery",
            "record_count": len(transformed_data),
            "details": export_details,
        }

    load_data(transformed_data, output_path)
    logger.info("Pipeline completed successfully.")
    return {
        "status": "SUCCESS",
        "output_path": output_path,
        "record_count": len(transformed_data),
    }


def main() -> None:
    """Parse arguments and start pipeline."""
    parser = argparse.ArgumentParser(description="Antigravity Python Data Pipeline")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="pipeline_output.json",
        help="Path for destination JSON file (default: pipeline_output.json)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=5,
        help="Number of records to generate/process (default: 5)",
    )
    parser.add_argument(
        "--exporter",
        "-e",
        type=str,
        choices=["file", "bigquery"],
        default="file",
        help="Target exporter for processed data (default: file)",
    )
    parser.add_argument(
        "--gcp-project",
        type=str,
        default=None,
        help="Google Cloud project ID for BigQuery export (fallback: GCP_PROJECT_ID)",
    )
    parser.add_argument(
        "--bq-dataset",
        type=str,
        default=None,
        help="BigQuery dataset ID (fallback: BIGQUERY_DATASET)",
    )
    parser.add_argument(
        "--bq-table",
        type=str,
        default=None,
        help="BigQuery table ID (fallback: BIGQUERY_TABLE)",
    )
    args = parser.parse_args()
    run_pipeline(
        output_path=args.output,
        limit=args.limit,
        exporter=args.exporter,
        bq_project=args.gcp_project,
        bq_dataset=args.bq_dataset,
        bq_table=args.bq_table,
    )


if __name__ == "__main__":
    main()
