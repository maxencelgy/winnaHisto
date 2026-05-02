#!/usr/bin/env python3
"""
Tableau simple : pour chaque cote exacte, % de fois où elle passe sur le marché.

Source : 30 CSV football-data.co.uk (Top 5 leagues × 6 saisons = ~10k matchs)
         × 6 cotes par match (1x2 home/draw/away + over/under 2.5 + BTTS)
         = ~50k observations cotes ↔ résultats.

Usage :
    python3 cote_table.py                       # tableau complet
    python3 cote_table.py --min-n 100           # cotes avec n ≥ 100
    python3 cote_table.py --min 1.10 --max 1.50 # tranche
    python3 cote_table.py --csv export.csv      # exporter en CSV
"""

import argparse
import csv
import glob
import os
from collections import defaultdict

DATA_DIR = "/Users/maxenceleguay/Sites/winnaHisto/datasets/fd"


def fnum(s):
    try:
        return float((s or "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def round_cote(o, step=0.01):
    return round(round(o / step) * step, 2)


def collect():
    """Renvoie cote → [n, won]."""
    g = defaultdict(lambda: [0, 0])
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.csv"))):
        try:
            with open(path, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
        except Exception:
            continue
        for r in rows:
            ftr = r.get("FTR")
            fthg = fnum(r.get("FTHG"))
            ftag = fnum(r.get("FTAG"))
            if ftr is None or fthg is None or ftag is None:
                continue

            # 1x2 — Pinnacle puis Bet365
            for col, won in (("PSH", ftr == "H"), ("PSD", ftr == "D"), ("PSA", ftr == "A"),
                             ("B365H", ftr == "H"), ("B365D", ftr == "D"), ("B365A", ftr == "A")):
                c = fnum(r.get(col))
                if c and c > 1:
                    k = round_cote(c)
                    g[k][0] += 1
                    if won:
                        g[k][1] += 1

            # Over/Under 2.5
            total = fthg + ftag
            for col, won in (("P>2.5", total > 2.5), ("P<2.5", total < 2.5),
                             ("B365>2.5", total > 2.5), ("B365<2.5", total < 2.5)):
                c = fnum(r.get(col))
                if c and c > 1:
                    k = round_cote(c)
                    g[k][0] += 1
                    if won:
                        g[k][1] += 1
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-n", type=int, default=30)
    ap.add_argument("--min", type=float, default=1.01, dest="cmin")
    ap.add_argument("--max", type=float, default=10.0, dest="cmax")
    ap.add_argument("--csv", default=None, help="Exporter le tableau dans un CSV")
    args = ap.parse_args()

    g = collect()
    total_obs = sum(n for n, _ in g.values())
    print(f"Dataset : 30 fichiers football-data.co.uk")
    print(f"Observations : {total_obs} cotes × résultats")
    print(f"Cotes uniques : {len(g)}")
    print()

    rows = []
    for cote, (n, w) in g.items():
        if n < args.min_n or cote < args.cmin or cote > args.cmax:
            continue
        wr = w / n
        ev = wr * cote - 1
        rows.append((cote, n, w, wr, ev))
    rows.sort(key=lambda r: r[0])  # par cote ascendante

    print(f"{'cote':>5}  {'n':>5}  {'gagne':>5}  {'wr':>7}  {'EV':>7}")
    print("-" * 45)
    for cote, n, w, wr, ev in rows:
        print(f"{cote:>5.2f}  {n:>5}  {w:>5}  {wr*100:>6.1f}%  {ev*100:>+6.1f}%")

    if args.csv:
        with open(args.csv, "w", encoding="utf-8") as f:
            wcsv = csv.writer(f)
            wcsv.writerow(["cote", "n", "gagne", "wr", "ev"])
            for cote, n, w, wr, ev in rows:
                wcsv.writerow([f"{cote:.2f}", n, w, f"{wr:.4f}", f"{ev:.4f}"])
        print(f"\nExporté → {args.csv}")


if __name__ == "__main__":
    main()
