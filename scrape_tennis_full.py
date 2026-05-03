#!/usr/bin/env python3
"""Scrape tennis 2018-01-01 → 2025-01-01 (compléter 7 ans manquants).

Le scrape précédent a fait 2025-01-01 → 2026-05-03 (6754 matchs).
Ce scrape ajoute la période 2018-2024 (~50000 matchs estimés).
Output : sofascore_massive/tennis_2018_2024.csv (à merger ensuite).
"""
import sys, os, csv
from datetime import date
from pathlib import Path
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from sofascore_massive import scrape_sport, OUT_DIR

if __name__ == "__main__":
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
    sys.stdout.reconfigure(line_buffering=True)
    start = date(2018, 1, 1)
    end = date(2024, 12, 31)

    # backup current tennis.csv before scrape (sofascore_massive overwrite)
    src = os.path.join(OUT_DIR, "tennis.csv")
    backup = os.path.join(OUT_DIR, "tennis_2025_2026_backup.csv")
    if os.path.exists(src):
        import shutil
        shutil.copy(src, backup)
        print(f"=== Backup tennis.csv → {backup} ===")

    print(f"=== TENNIS 2018-01-01 → 2024-12-31 ({(end-start).days} jours, batch=20) ===", flush=True)
    scrape_sport("tennis", start, end, batch_size=20)

    # Merge : combiner backup (2025-2026) + nouveau scrape (2018-2024)
    new_path = os.path.join(OUT_DIR, "tennis.csv")  # contient 2018-2024 maintenant
    merged_path = os.path.join(OUT_DIR, "tennis_merged.csv")
    rows_seen = set()
    rows_out = []
    fields = None
    for path in [new_path, backup]:
        if not os.path.exists(path):
            continue
        with open(path) as f:
            reader = csv.DictReader(f)
            if fields is None:
                fields = reader.fieldnames
            for r in reader:
                key = (r.get("date"), r.get("home"), r.get("away"))
                if key in rows_seen:
                    continue
                rows_seen.add(key)
                rows_out.append(r)
    rows_out.sort(key=lambda x: x.get("date") or "")
    with open(merged_path, "w") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_out)
    os.replace(merged_path, new_path)
    print(f"=== Merged: {len(rows_out)} matchs total ({backup} + scrape 2018-2024) → {new_path}", flush=True)
    print("=== DONE ===", flush=True)
