#!/usr/bin/env python3
"""Re-scrape un seul sport 2018-2026. Usage: python rescrape_one_sport.py <sport>"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
import sofascore_massive
sofascore_massive.OUT_DIR = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified"
from sofascore_massive import scrape_sport
from datetime import date
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python rescrape_one_sport.py <sport>")
    sys.exit(1)

sport = sys.argv[1]
workers = int(sys.argv[2]) if len(sys.argv) > 2 else 12

Path(sofascore_massive.OUT_DIR).mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(line_buffering=True)
t0 = time.time()
scrape_sport(sport, date(2018, 1, 1), date(2026, 5, 2), max_workers=workers)
print(f"\n{sport} done : {(time.time()-t0)/60:.1f} min")
