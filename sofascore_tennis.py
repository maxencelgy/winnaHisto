#!/usr/bin/env python3
"""Scrape Sofascore tennis 2024 toutes catégories (ATP/WTA/Challenger/ITF)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sofascore_massive import scrape_sport, OUT_DIR
from datetime import date
from pathlib import Path

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
    scrape_sport("tennis", date(2024, 1, 1), date(2024, 12, 31))
