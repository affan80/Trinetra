"""Compatibility path for the legacy services.shared imports."""

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parents[1] / "storage" / "shared")]
