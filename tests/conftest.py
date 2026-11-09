import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "backend"))
sys.path.insert(0, str(RACINE / "matching"))
os.environ.setdefault("APP_ENV", "development")
