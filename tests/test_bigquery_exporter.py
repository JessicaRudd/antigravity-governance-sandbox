"""Unit tests for BigQuery streaming telemetry exporter."""

from unittest.mock import MagicMock, patch
import pytest
from exporters.bigquery_exporter import BigQueryExporter, BigQueryExportError
from main import run_pipeline


@pytest.fixture
def sample_records():
    """Return sample transformed records for testing."""
    return [
        {
            "record_id": 1,
            "device_name": "sensor-1",
            "status": "ACTIVE",
            "temp_celsius": 21.5,
            "temp_fahrenheit": 70.7,
            "processed_at": "2026-09-08T19:00:00Z",
        },
        {
            "record_id": 2,
            "device_name": "sensor-2",
            "status": "IDLE",
            "temp_celsius": 23.0,
            "temp_fahrenheit": 73.4,
            "processed_at": "2026-09-08T19:00:00Z",
        },
        {
            "record_id": 3,
            "device_name": "sensor-3",
            "status": "ACTIVE",
            "temp_celsius": 24.5,
            "temp_fahrenheit": 76.1,
            "processed_at": "2026-09-08T19:00:00Z",
        },
    ]


def test_bigquery_exporter_missing_config():
    """Test ValueError is raised when configuration is incomplete."""
    exporter = BigQueryExporter(project_id="test-proj", dataset_id="test-ds", table_id=None)
    with pytest.raises(ValueError, match="Missing BigQuery configuration"):
        _ = exporter.table_reference


def test_bigquery_exporter_table_reference():
    """Test full table reference formatting."""
    exporter = BigQueryExporter(
        project_id="my-gcp-project",
        dataset_id="telemetry_dataset",
        table_id="sensor_readings",
    )
    assert exporter.table_reference == "my-gcp-project.telemetry_dataset.sensor_readings"


def test_bigquery_exporter_success_single_batch(sample_records):
    """Test successful export with single batch."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = []

    exporter = BigQueryExporter(
        project_id="my-proj",
        dataset_id="telemetry_ds",
        table_id="sensor_table",
        batch_size=10,
        client=mock_client,
    )

    result = exporter.export_records(sample_records)

    assert result["status"] == "SUCCESS"
    assert result["records_exported"] == 3
    assert result["batches"] == 1
    assert result["table"] == "my-proj.telemetry_ds.sensor_table"

    mock_client.insert_rows_json.assert_called_once()
    called_table, called_rows = mock_client.insert_rows_json.call_args[0]
    assert called_table == "my-proj.telemetry_ds.sensor_table"
    assert len(called_rows) == 3
    assert called_rows[0]["record_id"] == 1
    assert called_rows[0]["device_name"] == "sensor-1"
    assert called_rows[0]["status"] == "ACTIVE"
    assert called_rows[0]["temp_celsius"] == 21.5
    assert called_rows[0]["temp_fahrenheit"] == 70.7


def test_bigquery_exporter_batching(sample_records):
    """Test payload batching across multiple insert calls."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = []

    exporter = BigQueryExporter(
        project_id="my-proj",
        dataset_id="telemetry_ds",
        table_id="sensor_table",
        batch_size=2,
        client=mock_client,
    )

    result = exporter.export_records(sample_records)

    assert result["status"] == "SUCCESS"
    assert result["records_exported"] == 3
    assert result["batches"] == 2
    assert mock_client.insert_rows_json.call_count == 2


def test_bigquery_exporter_row_errors(sample_records):
    """Test handling of BigQuery row-level insertion errors."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = [
        {"index": 0, "errors": [{"reason": "invalid", "message": "Field required"}]}
    ]

    exporter = BigQueryExporter(
        project_id="my-proj",
        dataset_id="telemetry_ds",
        table_id="sensor_table",
        client=mock_client,
    )

    with pytest.raises(BigQueryExportError, match="BigQuery streaming insert failed with 1 row error"):
        exporter.export_records(sample_records)


def test_bigquery_exporter_retry_success(sample_records):
    """Test retry logic succeeds after transient network exception."""
    mock_client = MagicMock()
    mock_client.insert_rows_json.side_effect = [
        ConnectionError("Transient network failure"),
        [],
    ]

    exporter = BigQueryExporter(
        project_id="my-proj",
        dataset_id="telemetry_ds",
        table_id="sensor_table",
        client=mock_client,
    )

    result = exporter.export_records(sample_records)
    assert result["status"] == "SUCCESS"
    assert mock_client.insert_rows_json.call_count == 2


def test_bigquery_exporter_empty_records():
    """Test exporting empty record list."""
    mock_client = MagicMock()
    exporter = BigQueryExporter(
        project_id="my-proj",
        dataset_id="telemetry_ds",
        table_id="sensor_table",
        client=mock_client,
    )
    result = exporter.export_records([])
    assert result["status"] == "SUCCESS"
    assert result["records_exported"] == 0
    assert result["batches"] == 0
    mock_client.insert_rows_json.assert_not_called()


def test_pipeline_with_bigquery_exporter():
    """Test running end-to-end pipeline with BigQuery exporter."""
    with patch("google.cloud.bigquery.Client") as mock_bigquery_class:
        mock_instance = MagicMock()
        mock_instance.insert_rows_json.return_value = []
        mock_bigquery_class.return_value = mock_instance

        result = run_pipeline(
            limit=4,
            exporter="bigquery",
            bq_project="test-project-id",
            bq_dataset="sensor_dataset",
            bq_table="sensor_telemetry",
        )

        assert result["status"] == "SUCCESS"
        assert result["exporter"] == "bigquery"
        assert result["record_count"] == 4
        assert result["details"]["records_exported"] == 4
        assert mock_instance.insert_rows_json.called
