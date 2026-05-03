#!/usr/bin/env python3
"""Re-scrape basket + hockey + baseball + tennis 2018-2026 EN PARALLÈLE du foot.
Bootstrap Camoufox indépendant (cookies différents) pour ne pas conflicter."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
import sofascore_massive
sofascore_massive.OUT_DIR = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified"
from sofascore_massive import scrape_sport
from datetime import date
from pathlib import Path

Path(sofascore_massive.OUT_DIR).mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(line_buffering=True)

t0 = time.time()
targets = [
    ("basketball", date(2018, 1, 1), date(2026, 5, 2)),
    ("ice-hockey", date(2018, 1, 1), date(2026, 5, 2)),
    ("baseball",   date(2018, 1, 1), date(2026, 5, 2)),
    ("tennis",     date(2018, 1, 1), date(2026, 5, 2)),
]
for sport, sd, ed in targets:
    try:
        scrape_sport(sport, sd, ed, max_workers=8)
    except Exception as e:
        print(f"[{sport}] ERROR: {e}")

print(f"\n========== TOTAL TIME: {(time.time()-t0)/60:.1f} min ==========")
