import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def anyio_backend():
    return "asyncio"
