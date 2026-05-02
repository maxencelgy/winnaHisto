#!/usr/bin/env python3
"""Re-scrape FULL pour les 5 sports 2018-01-01 → 2026-05-02
avec markets étendus (1x2, BTTS, Over/Under multi-thresholds).
Sequential pour ne pas saturer l'API Sofascore."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import sofascore_massive
sofascore_massive.OUT_DIR = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified"
from sofascore_massive import scrape_sport
from datetime import date
from pathlib import Path
import time

Path(sofascore_massive.OUT_DIR).mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(line_buffering=True)

t0 = time.time()
# Sofascore a les cotes depuis ~2018 pour la plupart des sports
targets = [
    ("football",   date(2018, 1, 1), date(2026, 5, 2)),
    ("basketball", date(2018, 1, 1), date(2026, 5, 2)),
    ("ice-hockey", date(2018, 1, 1), date(2026, 5, 2)),
    ("baseball",   date(2018, 1, 1), date(2026, 5, 2)),
    # Tennis : 2018-2026 est énorme mais on le tente, scrape passe ~80M sample est gérable
    ("tennis",     date(2018, 1, 1), date(2026, 5, 2)),
]
for sport, sd, ed in targets:
    try:
        scrape_sport(sport, sd, ed)
    except Exception as e:
        print(f"[{sport}] ERROR: {e}")

print(f"\n========== TOTAL TIME: {(time.time()-t0)/60:.1f} min ==========")
