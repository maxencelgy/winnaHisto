#!/usr/bin/env python3
"""Re-scrape foot 2024-01-01 → 2026-05-02 avec Over/Under multi-thresholds."""
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
scrape_sport("football", date(2024, 1, 1), date(2026, 5, 2))
print(f"\nTotal time: {(time.time()-t0)/60:.1f} min")
