"""Fixtures compartidos para tests de analytics.

Aísla TODOS los tests de escribir en data/taxonomias_pendientes.json real.
"""
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _patch_taxonomias_path(tmp_path):
    """Patch _TAXONOMIAS_PATH para que ningún test escriba al JSON real."""
    fake_path = str(tmp_path / "taxonomias_pendientes.json")
    with patch("analytics._propuestas._TAXONOMIAS_PATH", fake_path):
        yield
