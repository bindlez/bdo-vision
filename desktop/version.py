"""Read the shipped VERSION file so source, installed and frozen builds agree."""
from pathlib import Path
import sys

_release_root = (Path(sys.executable).resolve().parent.parent
                 if getattr(sys, 'frozen', False)
                 else Path(__file__).resolve().parents[1])
try:
    APP_VERSION = (_release_root / 'VERSION').read_text(encoding='utf-8').strip()
except OSError:
    APP_VERSION = 'unknown'
