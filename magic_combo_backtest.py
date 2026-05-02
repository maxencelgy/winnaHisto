#!/usr/bin/env python3
"""
Backtest empirique : "si on avait combiné les cotes magiques chaque jour
sur 6 saisons, ROI réel ?".

Étapes :
1. Charger dataset foot + tennis (~10k matchs foot + 27k tennis)
2. Identifier "cotes magiques" : cotes avec n ≥ 100 et EV (= wr × cote − 1) > +2%
3. Pour chaque date du dataset, lister les sélections où le favori est à cote magique
4. Simuler stratégies :
   - "Combiné 2 jambes magiques par jour"
   - "Combiné 3 jambes magiques par jour"
   - "Combiné 4 jambes magiques par jour"
5. Output : ROI réel + win rate + nombre de combos joués

Usage :
    python3 magic_combo_backtest.py
    python3 magic_combo_backtest.py --min-ev 0.03 --max-legs 4 --stake 1
"""

import argparse
import csv
import glob
import os
from collections import defaultdict
from datetime import datetime

FD_DIR = "/Users/maxenceleguay/Sites/winnaHisto/datasets/fd"
TENNIS_CSV = "/Users/maxenceleguay/Sites/winnaHisto/datasets/tennis_all.csv"


def fnum(s):
    try:
        return float(str(s).replace(",", "."))
    except (TypeError, ValueError):
        return None


def round_cote(o, step=0.01):
    return round(round(o / step) * step, 2)


def parse_date(s):
    if not s:
        return None
    s = str(s)
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s.split()[0], fmt).date()
        except (ValueError, IndexError):
            continue
    return None


def load_observations():
    """Renvoie liste de tuples : (date, sport, match_id, cote, won)."""
    obs = []

    # ---- Foot (football-data.co.uk) ----
    for path in sorted(glob.glob(os.path.join(FD_DIR, "*.csv"))):
        league = os.path.basename(path).split("-")[0]
        try:
            with open(path, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
        except Exception:
            continue
        for r in rows:
            d = parse_date(r.get("Date"))
            if not d:
                continue
            ftr = r.get("FTR")
            fthg = fnum(r.get("FTHG"))
            ftag = fnum(r.get("FTAG"))
            if ftr is None or fthg is None or ftag is None:
                continue
            home = r.get("HomeTeam", "?")
            away = r.get("AwayTeam", "?")
            mid = f"foot:{league}:{home}vs{away}"

            # 1x2 (Pinnacle prioritaire, fallback B365)
            cands = [("PSH", "H", ftr == "H"), ("PSD", "D", ftr == "D"), ("PSA", "A", ftr == "A")]
            for col, side, won in cands:
                c = fnum(r.get(col))
                if not c:
                    c = fnum(r.get("B365" + side))
                if c and c > 1:
                    obs.append((d, "foot", f"{mid}:{side}", round_cote(c), won))

            total = fthg + ftag
            for col, won in (("P>2.5", total > 2.5), ("P<2.5", total < 2.5)):
                c = fnum(r.get(col))
                if c and c > 1:
                    obs.append((d, "foot", f"{mid}:{col}", round_cote(c), won))

    # ---- Tennis (tennis-data.co.uk) ----
    if os.path.exists(TENNIS_CSV):
        with open(TENNIS_CSV, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d = parse_date(r.get("date"))
                if not d:
                    continue
                w_name = r.get("winner") or "?"
                l_name = r.get("loser") or "?"
                mid = f"tennis:{r.get('tour')}:{w_name}vs{l_name}"
                # cotes Pinnacle si dispo, sinon B365
                cw = fnum(r.get("PSW")) or fnum(r.get("B365W"))
                cl = fnum(r.get("PSL")) or fnum(r.get("B365L"))
                if cw and cw > 1:
                    obs.append((d, "tennis", f"{mid}:W", round_cote(cw), True))
                if cl and cl > 1:
                    obs.append((d, "tennis", f"{mid}:L", round_cote(cl), False))

    return obs


def identify_magic_cotes(obs, min_n=100, min_ev=0.02):
    g = defaultdict(lambda: [0, 0])
    for _, _, _, cote, won in obs:
        g[cote][0] += 1
        if won:
            g[cote][1] += 1
    magic = {}
    for cote, (n, w) in g.items():
        if n < min_n:
            continue
        wr = w / n
        ev = wr * cote - 1
        if ev >= min_ev:
            magic[cote] = {"n": n, "wr": wr, "ev": ev}
    return magic


def daily_buckets(obs, magic):
    """Pour chaque date, sélections candidates (favoris cote magique).
    Une seule sélection par match (la mieux EV)."""
    by_date = defaultdict(dict)  # date → {match_id_short: (cote, won, ev_cote)}
    for d, sport, mid, cote, won in obs:
        if cote not in magic:
            continue
        ev = magic[cote]["ev"]
        # Tronquer match_id pour n'avoir qu'un pick par match
        match_short = mid.rsplit(":", 1)[0]
        prev = by_date[d].get(match_short)
        if prev is None or ev > prev[2]:
            by_date[d][match_short] = (cote, won, ev)
    return by_date


def simulate(by_date, n_legs, stake=1.0, max_combos_per_day=1):
    """Pour chaque date avec ≥ n_legs sélections, joue un combo des n_legs picks
    avec la meilleure EV. Renvoie stats."""
    n_played = 0
    n_won = 0
    total_pnl = 0.0
    cote_t_sum = 0.0
    days_eligible = 0
    for d, picks in by_date.items():
        items = list(picks.values())  # (cote, won, ev)
        if len(items) < n_legs:
            continue
        days_eligible += 1
        # Top n_legs par EV
        items.sort(key=lambda x: -x[2])
        top = items[:n_legs]
        cote_t = 1.0
        all_won = True
        for cote, won, _ in top:
            cote_t *= cote
            if not won:
                all_won = False
        n_played += 1
        cote_t_sum += cote_t
        if all_won:
            n_won += 1
            total_pnl += stake * (cote_t - 1)
        else:
            total_pnl -= stake
    return {
        "n_legs": n_legs,
        "days_eligible": days_eligible,
        "n_played": n_played,
        "n_won": n_won,
        "wr": n_won / n_played if n_played else 0,
        "stake_total": stake * n_played,
        "pnl": total_pnl,
        "roi": total_pnl / (stake * n_played) if n_played else 0,
        "avg_cote_t": cote_t_sum / n_played if n_played else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-n", type=int, default=100,
                    help="n minimum pour qu'une cote soit 'magique'")
    ap.add_argument("--min-ev", type=float, default=0.02,
                    help="EV minimum (point estimate) pour qu'une cote soit magique")
    ap.add_argument("--max-legs", type=int, default=5)
    ap.add_argument("--stake", type=float, default=1.0)
    ap.add_argument("--cote-max", type=float, default=10.0,
                    help="Cap sur la cote magique (ex: 1.85 = uniquement favoris)")
    ap.add_argument("--cote-min", type=float, default=1.01)
    args = ap.parse_args()

    print("Chargement dataset…")
    obs = load_observations()
    by_sport = defaultdict(int)
    for _, sport, _, _, _ in obs:
        by_sport[sport] += 1
    print(f"Observations : {len(obs)} | par sport : {dict(by_sport)}")

    magic = identify_magic_cotes(obs, min_n=args.min_n, min_ev=args.min_ev)
    magic = {c: v for c, v in magic.items() if args.cote_min <= c <= args.cote_max}
    print(f"\nCotes magiques identifiées : {len(magic)} (n≥{args.min_n}, EV≥{args.min_ev*100:.0f}%, "
          f"{args.cote_min}≤cote≤{args.cote_max})")
    sorted_magic = sorted(magic.items(), key=lambda x: -x[1]["ev"])
    print(f"{'cote':>5} {'n':>5} {'wr':>7} {'EV':>7}")
    for cote, info in sorted_magic[:25]:
        print(f"{cote:>5.2f} {info['n']:>5} {info['wr']*100:>6.1f}% {info['ev']*100:>+6.1f}%")

    by_date = daily_buckets(obs, magic)
    days_with_any = len(by_date)
    print(f"\nDates avec ≥1 cote magique : {days_with_any}")

    print(f"\n{'='*80}")
    print(f"BACKTEST — combo des n meilleurs picks magiques par jour, mise {args.stake}€")
    print(f"{'='*80}")
    print(f"{'n_legs':>6} {'jours':>6} {'joués':>6} {'gagnés':>6} {'wr':>7} "
          f"{'cote_t':>7} {'misé':>9} {'PnL':>9} {'ROI':>8}")
    print("-" * 80)
    for n_legs in range(1, args.max_legs + 1):
        s = simulate(by_date, n_legs, stake=args.stake)
        print(f"{s['n_legs']:>6} {s['days_eligible']:>6} {s['n_played']:>6} "
              f"{s['n_won']:>6} {s['wr']*100:>6.1f}% {s['avg_cote_t']:>7.2f} "
              f"{s['stake_total']:>8.0f}€ {s['pnl']:>+8.0f}€ {s['roi']*100:>+7.1f}%")

    print("\nLecture :")
    print("  - Pour chaque jour avec assez de picks, on prend les n meilleurs")
    print("    (par EV de la cote) et on les combine en 1 ticket.")
    print("  - 'jours' = jours éligibles (assez de picks magiques)")
    print("  - PnL = profit net cumulé sur la période entière")
    print(f"  - Mise unitaire fixée à {args.stake}€. Multiplie pour des mises plus grandes.")


if __name__ == "__main__":
    main()
