from pathlib import Path

import pytest

SAMPLE = Path(__file__).resolve().parents[2] / "sample_data" / "sales.csv"


@pytest.fixture
def sample_bytes() -> bytes:
    return SAMPLE.read_bytes()
