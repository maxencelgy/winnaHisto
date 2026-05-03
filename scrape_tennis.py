#!/usr/bin/env python3
"""Scrape tennis 2025-01-01 → today via sofascore_massive (light: batch 20)."""
import sys, os
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from sofascore_massive import scrape_sport, OUT_DIR

if __name__ == "__main__":
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
    sys.stdout.reconfigure(line_buffering=True)
    start = date(2025, 1, 1)  # réduit de 2024 → 2025 pour alléger
    end = date.today()
    print(f"=== TENNIS {start} → {end} ({(end-start).days} jours, batch_size=20 light) ===", flush=True)
    scrape_sport("tennis", start, end, batch_size=20)  # batch réduit pour moins de RAM
    print("=== DONE ===", flush=True)
