#!/usr/bin/env python3
"""Re-scrape FOOT ONLY 2018-2026."""
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
scrape_sport("football", date(2018, 1, 1), date(2026, 5, 2), max_workers=8)
print(f"\nFoot done : {(time.time()-t0)/60:.1f} min")
