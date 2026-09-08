# Antigravity Governance Sandbox

A modular Python data pipeline with authentication handling, automated tests, and GitHub Actions CI workflow.

## Structure

- [`auth.py`](file:///Users/jrudd/Documents/antigravity-governance-sandbox/auth.py): Credential management, environment variable loading, and API request header generation.
- [`main.py`](file:///Users/jrudd/Documents/antigravity-governance-sandbox/main.py): Pipeline entry point orchestrating extraction, transformation, and loading (ETL).
- [`requirements.txt`](file:///Users/jrudd/Documents/antigravity-governance-sandbox/requirements.txt): Core runtime and development dependencies.
- [`tests/`](file:///Users/jrudd/Documents/antigravity-governance-sandbox/tests/): Unit test suite covering authentication and pipeline transformations.
- [`.github/workflows/ci.yml`](file:///Users/jrudd/Documents/antigravity-governance-sandbox/.github/workflows/ci.yml): Multi-version Python CI matrix workflow (3.10, 3.11, 3.12) running flake8 linting and pytest.

## Getting Started

### 1. Set Up Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the Data Pipeline
```bash
python main.py --output output.json --limit 10
```

### 3. Run Tests and Linting
```bash
pytest -v
flake8 .
```
