#!/usr/bin/env python3
"""
Analyse stat par cote exacte sur dataset football-data.co.uk
(Top 5 leagues, 6 saisons, ~10k matchs).

Pour chaque cote unique observée sur 3 marchés (1x2, over/under 2.5, BTTS) :
- n = nombre de fois où cette cote a été proposée
- wr = winrate réel
- EV = wr × cote − 1
- comparaison avec ton historique perso

Bookmaker de référence : Pinnacle (PSH/PSD/PSA) car closing line = la plus calibrée.
Fallback Bet365 si Pinnacle absent.

Usage :
    python3 cote_stats.py
    python3 cote_stats.py --bk pinnacle  # ou bet365
    python3 cote_stats.py --min-n 30 --tranche 0.02
"""

import argparse
import csv
import glob
import math
import os
from collections import defaultdict
from pathlib import Path

DATA_DIR = "/Users/maxenceleguay/Sites/winnaHisto/datasets/fd"
HIST_DEFAULT = str(Path.home() / "Downloads" / "winamax-history-*.classified.csv")


def fnum(s):
    try:
        return float((s or "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def wilson_lower(won, n, z=1.96):
    if n == 0:
        return 0.0
    p = won / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / denom


def round_cote(o, step=0.01):
    return round(round(o / step) * step, 2)


def collect_observations(bk="pinnacle", step=0.01):
    """Pour chaque match : produit jusqu'à 7 observations (cote, outcome) :
    - 1x2 home/draw/away
    - over 2.5 / under 2.5
    - BTTS yes / no
    Retourne liste de (marché, cote_arrondie, won_bool).
    """
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    obs = []
    if bk == "pinnacle":
        cols_1x2 = ("PSH", "PSD", "PSA")
        cols_ou = ("P>2.5", "P<2.5")
    else:
        cols_1x2 = ("B365H", "B365D", "B365A")
        cols_ou = ("B365>2.5", "B365<2.5")
    cols_btts = ("BFEC", "BFEC")  # rarely standardized; we'll fallback to scan

    for path in files:
        try:
            with open(path, encoding="utf-8-sig") as f:
                r = csv.DictReader(f)
                rows = list(r)
        except Exception:
            continue
        for row in rows:
            ftr = row.get("FTR")  # H/D/A
            fthg = fnum(row.get("FTHG"))
            ftag = fnum(row.get("FTAG"))
            if ftr is None or fthg is None or ftag is None:
                continue

            # 1x2
            ch = fnum(row.get(cols_1x2[0]))
            cd = fnum(row.get(cols_1x2[1]))
            ca = fnum(row.get(cols_1x2[2]))
            if ch and ch > 1: obs.append(("1x2", round_cote(ch, step), ftr == "H"))
            if cd and cd > 1: obs.append(("1x2", round_cote(cd, step), ftr == "D"))
            if ca and ca > 1: obs.append(("1x2", round_cote(ca, step), ftr == "A"))

            # over/under 2.5
            total = fthg + ftag
            cou = fnum(row.get(cols_ou[0]))
            cuu = fnum(row.get(cols_ou[1]))
            if cou and cou > 1: obs.append(("ou25", round_cote(cou, step), total > 2.5))
            if cuu and cuu > 1: obs.append(("ou25", round_cote(cuu, step), total < 2.5))

            # BTTS — chercher colonnes dispos
            btts_yes = fthg > 0 and ftag > 0
            for col_y, col_n in [("B365>BTSY", "B365>BTSN"), ("BTSY", "BTSN")]:
                cy = fnum(row.get(col_y))
                cn = fnum(row.get(col_n))
                if cy and cy > 1:
                    obs.append(("btts", round_cote(cy, step), btts_yes))
                if cn and cn > 1:
                    obs.append(("btts", round_cote(cn, step), not btts_yes))
                if cy or cn:
                    break

    return obs


def aggregate(obs, by_market=False):
    g = defaultdict(lambda: [0, 0])  # key -> [n, won]
    for market, cote, won in obs:
        key = (market, cote) if by_market else cote
        g[key][0] += 1
        if won:
            g[key][1] += 1
    return g


def load_user_hist():
    files = sorted(glob.glob(HIST_DEFAULT), key=os.path.getmtime, reverse=True)
    if not files:
        return defaultdict(lambda: [0, 0])
    with open(files[0], encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("selection_status") in ("Gagné", "Perdu")]
    g = defaultdict(lambda: [0, 0])
    for r in rows:
        o = fnum(r.get("selection_odds"))
        if not o:
            continue
        c = round_cote(o, 0.01)
        g[c][0] += 1
        if r.get("selection_status") == "Gagné":
            g[c][1] += 1
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bk", default="pinnacle", choices=["pinnacle", "bet365"])
    ap.add_argument("--min-n", type=int, default=50)
    ap.add_argument("--step", type=float, default=0.01)
    ap.add_argument("--top", type=int, default=40)
    args = ap.parse_args()

    print(f"Chargement dataset football-data.co.uk (bk={args.bk}, step={args.step})…")
    obs = collect_observations(bk=args.bk, step=args.step)
    print(f"Observations totales : {len(obs)}")

    by_market = defaultdict(lambda: 0)
    for m, _, _ in obs:
        by_market[m] += 1
    print(f"  Décomposition : {dict(by_market)}")

    # Agrégation toutes obs (tous marchés confondus)
    g = aggregate(obs, by_market=False)
    print(f"\nCotes uniques observées : {len(g)} (step={args.step})")

    user_hist = load_user_hist()

    # --- Tableau principal : cotes les plus fréquentes ---
    rows = []
    for cote, (n, w) in g.items():
        if n < args.min_n:
            continue
        wr = w / n
        ev = wr * cote - 1
        wr_lo = wilson_lower(w, n)
        ev_lo = wr_lo * cote - 1
        u = user_hist.get(cote, [0, 0])
        rows.append((cote, n, w, wr, ev, wr_lo, ev_lo, u[0], u[1]))

    print(f"\n{'='*100}")
    print(f"TOP {args.top} cotes par EV (n ≥ {args.min_n})")
    print(f"{'='*100}")
    rows_by_ev = sorted(rows, key=lambda r: -r[4])
    print(f"{'cote':>5} {'n':>5} {'won':>5} {'wr':>7} {'EV':>7} {'wr_lo':>7} {'EV_lo':>7} {'tonN':>5} {'tonW':>5}")
    print("-" * 90)
    for c, n, w, wr, ev, wrl, evl, un, uw in rows_by_ev[:args.top]:
        print(f"{c:>5.2f} {n:>5} {w:>5} {wr*100:>6.1f}% {ev*100:>+6.1f}% {wrl*100:>6.1f}% {evl*100:>+6.1f}% {un:>5} {uw:>5}")

    print(f"\n{'='*100}")
    print(f"TOP {args.top} cotes les plus jouées dans le marché (n décroissant)")
    print(f"{'='*100}")
    rows_by_n = sorted(rows, key=lambda r: -r[1])
    print(f"{'cote':>5} {'n':>5} {'won':>5} {'wr':>7} {'EV':>7} {'wr_lo':>7} {'EV_lo':>7} {'tonN':>5} {'tonW':>5}")
    print("-" * 90)
    for c, n, w, wr, ev, wrl, evl, un, uw in rows_by_n[:args.top]:
        print(f"{c:>5.2f} {n:>5} {w:>5} {wr*100:>6.1f}% {ev*100:>+6.1f}% {wrl*100:>6.1f}% {evl*100:>+6.1f}% {un:>5} {uw:>5}")

    # --- Cross check : tes cotes "perfect match" historiques sont-elles vraiment edge ? ---
    print(f"\n{'='*100}")
    print(f"VALIDATION DE TES 'COTES PERFECT' HISTORIQUES (toi: wr≥85% n≥10)")
    print(f"{'='*100}")
    your_perfect = []
    for c, (un, uw) in user_hist.items():
        if un >= 10 and uw / un >= 0.85:
            market_n, market_w = g.get(c, [0, 0])
            market_wr = market_w / market_n if market_n else 0
            your_perfect.append((c, un, uw, uw / un, market_n, market_w, market_wr))
    your_perfect.sort(key=lambda x: -x[1])
    print(f"{'cote':>5} {'tonN':>5} {'tonW':>5} {'tonWR':>7} {'mktN':>6} {'mktWR':>7} {'écart':>7} {'verdict'}")
    print("-" * 80)
    for c, un, uw, uwr, mn, mw, mwr in your_perfect:
        if mn == 0:
            print(f"{c:>5.2f} {un:>5} {uw:>5} {uwr*100:>6.1f}% {'?':>6} {'?':>7} {'?':>7} pas dans dataset foot")
        else:
            ecart = (uwr - mwr) * 100
            verdict = "✅ confirmé" if abs(ecart) < 5 else ("⚠️ surperf perso" if ecart > 0 else "⚠️ overfit?")
            print(f"{c:>5.2f} {un:>5} {uw:>5} {uwr*100:>6.1f}% {mn:>6} {mwr*100:>6.1f}% {ecart:>+6.1f}% {verdict}")

    print("\nLecture :")
    print("  - wr     = winrate observé point estimate")
    print("  - wr_lo  = borne basse Wilson IC95 (wr 'pessimiste', le vrai signal)")
    print("  - EV_lo  = EV en mode prudent. Si > 0 → vraie cote rentable confirmée.")
    print("  - tonN/tonW = ton historique perso à cette cote exacte.")
    print("  - 'écart' = ton wr perso - wr marché. >0 = tu surperformes (chance ?)")


if __name__ == "__main__":
    main()
