"""BigQuery streaming telemetry exporter module.

Streams transformed sensor telemetry records directly into Google Cloud BigQuery.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("bigquery_exporter")


class BigQueryExportError(RuntimeError):
    """Raised when BigQuery streaming insert encounters errors."""

    pass


class BigQueryExporter:
    """Manages streaming data export into Google Cloud BigQuery."""

    DEFAULT_BATCH_SIZE = 500

    def __init__(
        self,
        project_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        table_id: Optional[str] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        client: Optional[Any] = None,
    ):
        """Initialize BigQuery exporter configuration."""
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.dataset_id = dataset_id or os.getenv("BIGQUERY_DATASET")
        self.table_id = table_id or os.getenv("BIGQUERY_TABLE")
        self.batch_size = max(1, batch_size)
        self._client = client

    def get_client(self) -> Any:
        """Lazily initialize and return the BigQuery client."""
        if self._client is None:
            try:
                from google.cloud import bigquery
            except ImportError as err:
                raise ImportError(
                    "google-cloud-bigquery is required for BigQueryExporter. "
                    "Install it via pip install google-cloud-bigquery."
                ) from err
            self._client = bigquery.Client(project=self.project_id)
        return self._client

    @property
    def table_reference(self) -> str:
        """Construct full table reference string."""
        if not (self.project_id and self.dataset_id and self.table_id):
            raise ValueError(
                "Missing BigQuery configuration: project_id, dataset_id, and table_id are all required."
            )
        return f"{self.project_id}.{self.dataset_id}.{self.table_id}"

    def format_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and format a record to match the BigQuery telemetry schema."""
        return {
            "record_id": int(record["record_id"]),
            "device_name": str(record["device_name"]),
            "status": str(record["status"]),
            "temp_celsius": float(record["temp_celsius"]),
            "temp_fahrenheit": float(record["temp_fahrenheit"]),
            "processed_at": str(record["processed_at"]),
        }

    def _insert_batch_with_retry(
        self,
        client: Any,
        table_ref: str,
        batch: List[Dict[str, Any]],
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> List[Any]:
        """Insert a batch of rows with retry logic for transient errors."""
        last_exception = None
        for attempt in range(max_retries):
            try:
                errors = client.insert_rows_json(table_ref, batch)
                return errors
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Transient error inserting batch (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries,
                    exc,
                )
                if attempt < max_retries - 1:
                    time.sleep(backoff_factor * (2**attempt))

        raise BigQueryExportError(
            f"Failed to insert batch after {max_retries} attempts: {last_exception}"
        ) from last_exception

    def export_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stream transformed records to BigQuery in batches."""
        if not records:
            logger.info("No records provided to export.")
            return {"status": "SUCCESS", "records_exported": 0, "batches": 0}

        table_ref = self.table_reference
        client = self.get_client()

        formatted_records = [self.format_record(r) for r in records]
        total_records = len(formatted_records)
        all_errors = []
        batch_count = 0

        for i in range(0, total_records, self.batch_size):
            batch = formatted_records[i:i + self.batch_size]
            batch_count += 1
            logger.info("Streaming batch %d (%d rows) to %s...", batch_count, len(batch), table_ref)

            errors = self._insert_batch_with_retry(client, table_ref, batch)
            if errors:
                logger.error("BigQuery row insertion errors in batch %d: %s", batch_count, errors)
                all_errors.extend(errors)

        if all_errors:
            raise BigQueryExportError(
                f"BigQuery streaming insert failed with {len(all_errors)} row error(s): {all_errors}"
            )

        logger.info("Successfully exported %d records across %d batch(es).", total_records, batch_count)
        return {
            "status": "SUCCESS",
            "records_exported": total_records,
            "batches": batch_count,
            "table": table_ref,
        }
