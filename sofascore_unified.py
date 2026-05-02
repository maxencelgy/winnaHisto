#!/usr/bin/env python3
"""
Sofascore unified scraper — TOUT 2024-01-01 → aujourd'hui pour tous les sports.

Output : /Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified/{sport}.csv
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sofascore_massive import scrape_sport
from datetime import date
from pathlib import Path

OUT = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified"
import sofascore_massive
sofascore_massive.OUT_DIR = OUT


def main():
    Path(OUT).mkdir(parents=True, exist_ok=True)
    sys.stdout.reconfigure(line_buffering=True)
    today = date.today()
    targets = [
        # Sports d'équipe : 2 saisons + actuelle
        ("football",   date(2024, 1, 1), today),
        ("basketball", date(2024, 1, 1), today),
        ("ice-hockey", date(2024, 1, 1), today),
        ("baseball",   date(2024, 1, 1), today),
        # Tennis : juste 2025-2026 (volume trop énorme sinon)
        ("tennis",     date(2025, 1, 1), today),
    ]
    import time
    t0 = time.time()
    for sport, sd, ed in targets:
        scrape_sport(sport, sd, ed, max_workers=40)
    print(f"\n========== TOTAL TIME: {(time.time()-t0)/60:.1f} min ==========")


if __name__ == "__main__":
    main()
