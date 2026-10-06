"""Project paths, defined once."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
NOTES = ROOT / "notes"
RESULTS = ROOT / "results"
CACHE = ROOT / ".cache"
