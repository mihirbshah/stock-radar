"""Single-symbol data-source connectivity diagnostic; uses no paid API key."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scanner import download, download_yahoo

for name, fetch in (("Yahoo", download_yahoo), ("Stooq", download)):
    try:
        rows = fetch("NVDA")
        print("%s: OK, %d bars, latest=%s" % (name, len(rows), rows[-1]["date"]))
        sys.exit(0)
    except Exception as exc:
        print("%s: FAILED: %s" % (name, exc), file=sys.stderr)
sys.exit("No free data source available on this GitHub runner")
