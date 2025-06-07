import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
# parent of tests directory
ROOT = ROOT_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
