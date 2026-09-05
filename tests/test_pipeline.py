"""Unit tests for main.py."""

import json
from auth import AuthManager
from main import extract_data, load_data, run_pipeline, transform_data


def test_extract_data():
    """Test data extraction returns requested record limit."""
    auth = AuthManager()
    records = extract_data(auth, limit=3)
    assert len(records) == 3
    assert records[0]["id"] == 1
    assert "reading" in records[0]


def test_transform_data():
    """Test data transformation converts temperatures and normalizes fields."""
    raw = [
        {"id": 1, "name": "Sensor-A", "reading": 0.0, "status": "active"},
        {"id": 2, "name": "Sensor-B", "reading": 100.0, "status": "idle"},
    ]
    transformed = transform_data(raw)
    assert len(transformed) == 2

    # Check first record (0 C -> 32 F)
    assert transformed[0]["record_id"] == 1
    assert transformed[0]["device_name"] == "sensor-a"
    assert transformed[0]["status"] == "ACTIVE"
    assert transformed[0]["temp_celsius"] == 0.0
    assert transformed[0]["temp_fahrenheit"] == 32.0
    assert "processed_at" in transformed[0]

    # Check second record (100 C -> 212 F)
    assert transformed[1]["temp_fahrenheit"] == 212.0


def test_load_data(tmp_path):
    """Test data loading writes valid JSON output."""
    output_file = tmp_path / "test_output.json"
    data = [{"record_id": 1, "device_name": "sensor-1"}]
    load_data(data, str(output_file))

    assert output_file.exists()
    with open(output_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["metadata"]["total_records"] == 1
    assert loaded["data"] == data


def test_run_pipeline_end_to_end(tmp_path):
    """Test complete pipeline execution."""
    output_file = tmp_path / "pipeline_run.json"
    result = run_pipeline(output_path=str(output_file), limit=4)

    assert result["status"] == "SUCCESS"
    assert result["record_count"] == 4
    assert output_file.exists()
