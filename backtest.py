#!/usr/bin/env python3
"""
Backtest walk-forward des stratégies de paris fondées sur les edges historiques
du user. À chaque pari t, on calibre les zones d'edge sur l'historique [0, t-1]
puis on décide si la stratégie aurait pris ce pari. Bankroll simulée.

Comparaison : baseline (tout placer flat 1%) vs stratégies filtrées + Kelly/flat.

Usage :
    python3 backtest.py
    python3 backtest.py --csv "/path.csv"
    python3 backtest.py --bk0 100 --cold 500 --recalib 200
"""

import argparse
import csv
import glob
import math
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DEFAULT_CSV_GLOB = str(Path.home() / "Downloads" / "winamax-history-*.classified.csv")


def fnum(s):
    try:
        return float((s or "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def find_csv():
    matches = sorted(glob.glob(DEFAULT_CSV_GLOB), key=os.path.getmtime, reverse=True)
    if matches:
        return matches[0]
    matches = sorted(glob.glob(str(Path.home() / "Downloads" / "winamax-history-*.csv")),
                     key=os.path.getmtime, reverse=True)
    return matches[0] if matches else None


def load_legs(path):
    with open(path, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["selection_status"] in ("Gagné", "Perdu")]
    parsed = []
    for r in rows:
        try:
            dt = datetime.strptime(r["ticket_date"], "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        o = fnum(r["selection_odds"])
        if not o or o <= 1.0:
            continue
        parsed.append({
            "dt": dt,
            "o": o,
            "won": r["selection_status"] == "Gagné",
            "sport": (r.get("selection_sport") or "").strip() or "?",
            "market": (r.get("selection_market") or "").strip() or "?",
        })
    parsed.sort(key=lambda r: r["dt"])
    return parsed


def wilson_lower(won, n, z=1.96):
    if n == 0:
        return 0.0
    p = won / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / denom


def calibrate(prior, conservative=False):
    """Construit les structures d'edge à partir de tous les paris antérieurs."""
    cote_g = defaultdict(lambda: [0, 0])         # cote -> [n, won]
    trip_g = defaultdict(lambda: [0, 0])         # (cote, sport, marché) -> [n, won]
    combo_g = defaultdict(lambda: [0, 0])        # (sport, marché, tranche) -> [n, won]
    sport_g = defaultdict(lambda: [0, 0, 0.0])   # sport -> [n, won, sum_odds]

    for r in prior:
        c_key = f"{r['o']:.2f}"
        cote_g[c_key][0] += 1
        if r["won"]:
            cote_g[c_key][1] += 1
        tk = (c_key, r["sport"], r["market"])
        trip_g[tk][0] += 1
        if r["won"]:
            trip_g[tk][1] += 1
        tranche = round(r["o"] // 0.1 * 0.1, 1)
        ck = (r["sport"], r["market"], tranche)
        combo_g[ck][0] += 1
        if r["won"]:
            combo_g[ck][1] += 1
        sport_g[r["sport"]][0] += 1
        if r["won"]:
            sport_g[r["sport"]][1] += 1
        sport_g[r["sport"]][2] += r["o"]

    def winrate(n, w):
        if conservative:
            return wilson_lower(w, n)
        return w / n if n else 0

    stable = {}
    for k, (n, w) in cote_g.items():
        if n >= 10:
            wr = winrate(n, w)
            if wr >= 0.85:
                stable[float(k)] = {"n": n, "wr": wr, "ev": wr * float(k) - 1}

    triplets = {}
    for k, (n, w) in trip_g.items():
        if n >= 10:
            wr = winrate(n, w)
            if wr >= 0.85:
                triplets[k] = {"n": n, "wr": wr}

    combos = {}
    for k, (n, w) in combo_g.items():
        if n >= 20:
            wr = winrate(n, w)
            cote_mid = k[2] + 0.05
            ev = wr * cote_mid - 1
            if ev > 0.05:
                combos[k] = {"n": n, "wr": wr, "ev": ev}

    bad_sports = set()
    good_sports = set()
    for s, (n, w, so) in sport_g.items():
        if n >= 30:
            avg_o = so / n
            wr = winrate(n, w)
            ev = wr * avg_o - 1
            if ev < -0.10:
                bad_sports.add(s)
            elif ev > 0.05:
                good_sports.add(s)

    return {"stable": stable, "triplets": triplets, "combos": combos,
            "bad_sports": bad_sports, "good_sports": good_sports}


def kelly_quarter(p, c, cap=0.05):
    b = c - 1
    if b <= 0:
        return 0.0
    f = (p * b - (1 - p)) / b
    return max(0.0, min(f * 0.25, cap))


# ---- DECISION FUNCTIONS (true = on prend le pari) ----

def decide_all(leg, edges):
    return True


def decide_stable_cote(leg, edges):
    return leg["o"] in edges["stable"] and leg["sport"] not in edges["bad_sports"]


def decide_triplet(leg, edges):
    key = (f"{leg['o']:.2f}", leg["sport"], leg["market"])
    return key in edges["triplets"]


def decide_combo(leg, edges):
    tranche = round(leg["o"] // 0.1 * 0.1, 1)
    key = (leg["sport"], leg["market"], tranche)
    return key in edges["combos"] and leg["sport"] not in edges["bad_sports"]


def decide_any(leg, edges):
    return (decide_triplet(leg, edges)
            or decide_stable_cote(leg, edges)
            or decide_combo(leg, edges))


def decide_anti_fade(leg, edges):
    """Tout sauf bad_sports."""
    return leg["sport"] not in edges["bad_sports"]


# ---- SIZING ----

def sizing_flat_pct(pct):
    def s(leg, bk, edges):
        return bk * pct
    return s


def sizing_kelly_quarter(leg, bk, edges):
    """Kelly ¼ basé sur la winrate calibrée la plus proche du pari."""
    p = None
    key = (f"{leg['o']:.2f}", leg["sport"], leg["market"])
    if key in edges["triplets"]:
        p = edges["triplets"][key]["wr"]
    elif leg["o"] in edges["stable"]:
        p = edges["stable"][leg["o"]]["wr"]
    else:
        tranche = round(leg["o"] // 0.1 * 0.1, 1)
        ck = (leg["sport"], leg["market"], tranche)
        if ck in edges["combos"]:
            p = edges["combos"][ck]["wr"]
    if p is None:
        return bk * 0.005  # fallback minuscule
    f = kelly_quarter(p, leg["o"], cap=0.05)
    return bk * f


# ---- RUNNER ----

def run_backtest(legs, decide, sizing, bk0=100.0,
                 cold_start=500, recalib_every=200, conservative=False,
                 floor_bk=0.50):
    bk = bk0
    n_placed = 0
    n_won = 0
    edges = None
    bk_history = []
    max_bk = bk0
    max_dd = 0.0

    for i, leg in enumerate(legs):
        if i < cold_start:
            continue
        if edges is None or (i - cold_start) % recalib_every == 0:
            edges = calibrate(legs[:i], conservative=conservative)

        if not decide(leg, edges):
            continue

        stake = sizing(leg, bk, edges)
        if stake <= 0 or stake > bk:
            continue
        n_placed += 1
        if leg["won"]:
            n_won += 1
            bk += stake * (leg["o"] - 1)
        else:
            bk -= stake
        bk = max(bk, floor_bk)
        max_bk = max(max_bk, bk)
        dd = (max_bk - bk) / max_bk if max_bk > 0 else 0
        max_dd = max(max_dd, dd)
        bk_history.append((leg["dt"], bk))

    return {
        "final_bk": bk, "bk0": bk0,
        "roi": (bk - bk0) / bk0,
        "n_placed": n_placed,
        "n_won": n_won,
        "wr": n_won / n_placed if n_placed else 0,
        "max_dd": max_dd,
        "history": bk_history,
    }


# ---- MAIN ----

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None)
    ap.add_argument("--bk0", type=float, default=100.0)
    ap.add_argument("--cold", type=int, default=500)
    ap.add_argument("--recalib", type=int, default=200)
    ap.add_argument("--conservative", action="store_true",
                    help="Utilise Wilson IC95 lower bound pour la winrate (plus prudent)")
    args = ap.parse_args()

    csv_path = args.csv or find_csv()
    if not csv_path or not os.path.exists(csv_path):
        print("CSV historique introuvable. Donne --csv chemin.csv")
        return

    print(f"Source : {csv_path}")
    legs = load_legs(csv_path)
    n = len(legs)
    print(f"Paris settled chargés : {n}")
    print(f"Période : {legs[0]['dt']} → {legs[-1]['dt']}")
    print(f"Cold start : {args.cold} paris (calibration seule)")
    print(f"Recalibration : tous les {args.recalib} paris")
    print(f"Mode : {'CONSERVATEUR (Wilson IC95)' if args.conservative else 'NORMAL (point estimate)'}")
    print(f"Bankroll initial : {args.bk0:.2f}€")

    flat1pct = sizing_flat_pct(0.01)
    flat2pct = sizing_flat_pct(0.02)

    strategies = [
        ("Baseline tout flat 1%",        decide_all,        flat1pct),
        ("Baseline tout flat 2%",        decide_all,        flat2pct),
        ("Anti-fade (skip bad sports)",  decide_anti_fade,  flat1pct),
        ("Triplet strict (n≥10 wr≥85)",  decide_triplet,    flat2pct),
        ("Triplet strict + ¼Kelly",      decide_triplet,    sizing_kelly_quarter),
        ("Cote stable (n≥10 wr≥85)",     decide_stable_cote, flat2pct),
        ("Cote stable + ¼Kelly",         decide_stable_cote, sizing_kelly_quarter),
        ("Combo (n≥20 EV≥+5%)",          decide_combo,      flat2pct),
        ("ANY (triplet|stable|combo)",   decide_any,        flat2pct),
        ("ANY + ¼Kelly",                 decide_any,        sizing_kelly_quarter),
    ]

    results = []
    for name, dfn, sfn in strategies:
        r = run_backtest(legs, dfn, sfn, bk0=args.bk0,
                         cold_start=args.cold, recalib_every=args.recalib,
                         conservative=args.conservative)
        results.append((name, r))

    print()
    print("=" * 110)
    print(f"{'Stratégie':<35} {'Final':>10} {'ROI':>8} {'#Paris':>7} {'WR':>7} {'MaxDD':>7}")
    print("=" * 110)
    for name, r in results:
        print(f"{name:<35} {r['final_bk']:>9.2f}€ {r['roi']*100:>+6.1f}% "
              f"{r['n_placed']:>7} {r['wr']*100:>6.1f}% {r['max_dd']*100:>6.1f}%")
    print("=" * 110)

    print("\nLecture rapide :")
    base = next(r for n, r in results if n.startswith("Baseline tout flat 1"))
    print(f"  - Baseline (tout placer 1%) : {base['final_bk']:.2f}€ ({base['roi']*100:+.1f}%) sur "
          f"{base['n_placed']} paris filtrés.")
    best = max(results, key=lambda x: x[1]["final_bk"])
    print(f"  - Meilleure stratégie : {best[0]} → {best[1]['final_bk']:.2f}€ "
          f"({best[1]['roi']*100:+.1f}%) sur {best[1]['n_placed']} paris.")
    if best[1]["final_bk"] > base["final_bk"] * 1.10:
        print(f"  → Edge réel détecté : {best[0]} surperforme baseline de "
              f"{(best[1]['final_bk']/base['final_bk']-1)*100:.1f}%.")
    else:
        print("  → Aucune stratégie n'écrase clairement la baseline. Revoir les seuils ou n.")

    print("\nNote : les paris sont traités au niveau LEG (chaque jambe = obs indépendante).")
    print("Walk-forward strict : à t, calibration uniquement sur paris < t.")
    print("Pas de lookahead. Sizing flat/Kelly ne reflète pas tes mises réelles, c'est volontaire.")


if __name__ == "__main__":
    main()
