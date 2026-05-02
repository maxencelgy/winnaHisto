#!/usr/bin/env python3
"""
Analyse au niveau TICKET (et pas leg) : où sont les vrais gains du user ?

Objectif : identifier les profils de combinés rentables, mesurer ROI réel
(ticket_stake / ticket_gain) et estimer un revenu mensuel typique.

Usage :
    python3 combo_analysis.py
    python3 combo_analysis.py --csv "/path.csv"
"""

import argparse
import csv
import glob
import os
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
from statistics import median, mean


def fnum(s):
    try:
        return float((s or "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def find_csv():
    matches = sorted(glob.glob(str(Path.home() / "Downloads" / "winamax-history-*.classified.csv")),
                     key=os.path.getmtime, reverse=True)
    if matches:
        return matches[0]
    matches = sorted(glob.glob(str(Path.home() / "Downloads" / "winamax-history-*.csv")),
                     key=os.path.getmtime, reverse=True)
    return matches[0] if matches else None


def load_tickets(path):
    """Groupe par ticket_ref. Renvoie un dict ticket_ref -> {meta, legs[]}"""
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    tickets = {}
    for r in rows:
        ref = r.get("ticket_ref") or ""
        if not ref:
            continue
        if ref not in tickets:
            tickets[ref] = {
                "ref": ref,
                "date": r.get("ticket_date"),
                "type": r.get("ticket_type"),
                "status": r.get("ticket_status"),
                "total_odds": fnum(r.get("ticket_total_odds")),
                "stake": fnum(r.get("ticket_stake")),
                "stake_type": r.get("ticket_stake_type"),
                "gain": fnum(r.get("ticket_gain")),
                "legs_count": int(r.get("ticket_legs_count") or 0),
                "legs": [],
            }
        tickets[ref]["legs"].append({
            "sport": (r.get("selection_sport") or "").strip() or "?",
            "market": (r.get("selection_market") or "").strip() or "?",
            "odds": fnum(r.get("selection_odds")),
            "status": r.get("selection_status"),
            "label": r.get("selection_label"),
        })
    # parse date
    for t in tickets.values():
        try:
            t["dt"] = datetime.strptime(t["date"], "%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            t["dt"] = None
    return tickets


def settled(tickets):
    return [t for t in tickets.values() if t["status"] in ("Gagné", "Perdu")]


def real_pnl(t):
    """PnL réel du ticket. Freebet : pas de mise perdue, gain = ticket_gain - 0 (mais déduire stake si Freebet rendu)."""
    stake = t["stake"] or 0
    gain = t["gain"] or 0
    if (t.get("stake_type") or "").lower() == "freebet":
        # Freebet : gain net = gain (la mise n'est ni perdue ni rendue)
        return gain - 0 if t["status"] == "Gagné" else 0
    if t["status"] == "Gagné":
        return gain - stake
    return -stake


def section(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def fmt(rows, headers):
    rows = [tuple(str(x) for x in r) for r in rows]
    widths = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(headers)]
    line = lambda parts: "  ".join(str(p).ljust(w) for p, w in zip(parts, widths))
    print(line(headers))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print(line(r))


def aggregate(tickets, key_fn):
    g = defaultdict(lambda: {"n": 0, "won": 0, "stake": 0.0, "gain": 0.0, "pnl": 0.0,
                              "freebet_n": 0})
    for t in tickets:
        k = key_fn(t)
        if k is None:
            continue
        g[k]["n"] += 1
        if t["status"] == "Gagné":
            g[k]["won"] += 1
        if (t.get("stake_type") or "").lower() == "freebet":
            g[k]["freebet_n"] += 1
        else:
            g[k]["stake"] += t["stake"] or 0
        g[k]["gain"] += t["gain"] or 0
        g[k]["pnl"] += real_pnl(t)
    return g


def print_aggregate(g, label, min_n=5, sort_key="pnl"):
    rows = []
    for k, v in g.items():
        if v["n"] < min_n:
            continue
        wr = v["won"] / v["n"]
        roi = v["pnl"] / v["stake"] if v["stake"] > 0 else 0
        rows.append((k, v["n"], v["won"], wr, v["stake"], v["pnl"], roi, v["freebet_n"]))
    if sort_key == "pnl":
        rows.sort(key=lambda r: -r[5])
    else:
        rows.sort(key=lambda r: -r[6])
    fmt(
        [(str(k)[:30], n, w, f"{wr*100:.1f}%", f"{stake:.0f}€", f"{pnl:+.0f}€",
          f"{roi*100:+.1f}%", fb)
         for k, n, w, wr, stake, pnl, roi, fb in rows[:25]],
        [label, "n", "gagnés", "winrate", "misé(€)", "pnl(€)", "ROI", "fb"],
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    csv_path = args.csv or find_csv()
    if not csv_path or not os.path.exists(csv_path):
        print("CSV introuvable. Donne --csv chemin.csv")
        return

    print(f"Source : {csv_path}")
    tickets = load_tickets(csv_path)
    s = settled(tickets)
    print(f"Tickets totaux : {len(tickets)} | settled : {len(s)}")

    # Métriques globales
    total_stake = sum((t["stake"] or 0) for t in s if (t["stake_type"] or "").lower() != "freebet")
    total_pnl = sum(real_pnl(t) for t in s)
    total_won = sum(1 for t in s if t["status"] == "Gagné")
    n_freebet = sum(1 for t in s if (t["stake_type"] or "").lower() == "freebet")
    print(f"\n💸 Mises totales (cash) : {total_stake:.0f}€")
    print(f"💰 PnL total : {total_pnl:+.0f}€")
    print(f"📊 ROI global : {(total_pnl/total_stake*100) if total_stake else 0:+.1f}%")
    print(f"🎯 Tickets gagnés : {total_won}/{len(s)} ({total_won/len(s)*100:.1f}%)")
    print(f"🎁 Freebets utilisés : {n_freebet}")

    # Période et fréquence
    dates = [t["dt"] for t in s if t["dt"]]
    if dates:
        period_days = (max(dates) - min(dates)).days
        per_month = len(s) / max(period_days/30, 1)
        pnl_per_month = total_pnl / max(period_days/30, 1)
        print(f"📅 Période : {min(dates).date()} → {max(dates).date()} ({period_days} jours)")
        print(f"⚡ Fréquence : {per_month:.1f} tickets/mois")
        print(f"💵 PnL moyen mensuel : {pnl_per_month:+.1f}€/mois")

    # === SPLIT PAR TYPE DE TICKET ===
    section("Split par TYPE de ticket (Simple / Combiné / etc.)")
    g = aggregate(s, lambda t: t["type"] or "?")
    print_aggregate(g, "type", min_n=1)

    # === SPLIT PAR NB JAMBES ===
    section("Split par NOMBRE DE JAMBES")
    g = aggregate(s, lambda t: t["legs_count"] or 0)
    print_aggregate(g, "nb_jambes", min_n=5)

    # === SPLIT PAR TRANCHE COTE TOTALE ===
    section("Split par TRANCHE de cote totale (combinés uniquement)")
    def tranche_total(t):
        if t["legs_count"] <= 1:
            return None
        c = t["total_odds"]
        if not c:
            return None
        if c < 2: return "1.x"
        if c < 3: return "2.x"
        if c < 5: return "3-5"
        if c < 8: return "5-8"
        if c < 12: return "8-12"
        if c < 20: return "12-20"
        if c < 50: return "20-50"
        return "50+"
    g = aggregate(s, tranche_total)
    print_aggregate(g, "cote_totale", min_n=5)

    # === SPLIT PAR TRANCHE STAKE ===
    section("Split par MISE (cash uniquement, freebets exclus)")
    def tranche_stake(t):
        if (t.get("stake_type") or "").lower() == "freebet":
            return None
        s_ = t["stake"]
        if not s_:
            return None
        if s_ < 2: return "0-2€"
        if s_ < 5: return "2-5€"
        if s_ < 10: return "5-10€"
        if s_ < 20: return "10-20€"
        if s_ < 50: return "20-50€"
        return "50€+"
    g = aggregate(s, tranche_stake)
    print_aggregate(g, "mise", min_n=5)

    # === COMBO TYPE × NB JAMBES ===
    section("Split COMBINÉS uniquement par NB JAMBES")
    combos = [t for t in s if t["legs_count"] >= 2]
    g = aggregate(combos, lambda t: f"{t['legs_count']} jambes")
    print_aggregate(g, "nb_jambes", min_n=5)

    # === SPORT DOMINANT DANS LES COMBOS GAGNÉS ===
    section("Sports les plus présents dans les COMBINÉS GAGNÉS")
    sport_count = Counter()
    for t in combos:
        if t["status"] != "Gagné":
            continue
        for leg in t["legs"]:
            sport_count[leg["sport"]] += 1
    fmt([(s, n) for s, n in sport_count.most_common(15)], ["sport", "occ"])

    # === MARCHÉS LES PLUS PRÉSENTS DANS LES COMBOS GAGNÉS ===
    section("Marchés les plus présents dans les COMBINÉS GAGNÉS")
    market_count = Counter()
    for t in combos:
        if t["status"] != "Gagné":
            continue
        for leg in t["legs"]:
            market_count[leg["market"]] += 1
    fmt([(m, n) for m, n in market_count.most_common(15)], ["marché", "occ"])

    # === ZOOM SUR LES COMBOS À FORTE COTE GAGNÉS ===
    section("TOP 15 plus gros COMBINÉS GAGNÉS (par PnL)")
    won_combos = [t for t in combos if t["status"] == "Gagné"]
    won_combos.sort(key=lambda t: -real_pnl(t))
    rows = []
    for t in won_combos[:15]:
        sports = "+".join(sorted({l["sport"] for l in t["legs"]}))[:25]
        rows.append((
            t["dt"].date() if t["dt"] else "?",
            t["legs_count"],
            f"{t['total_odds']:.2f}" if t["total_odds"] else "?",
            f"{(t['stake'] or 0):.1f}€",
            f"{(t['gain'] or 0):.1f}€",
            f"{real_pnl(t):+.1f}€",
            sports,
        ))
    fmt(rows, ["date", "n_legs", "cote_t", "mise", "gain", "pnl", "sports"])

    # === SUMMARY DOIT-ON FAIRE DES COMBOS ? ===
    section("VERDICT — Où viennent vraiment tes gains ?")
    simple = [t for t in s if t["legs_count"] == 1]
    multi = [t for t in s if t["legs_count"] >= 2]

    pnl_simple = sum(real_pnl(t) for t in simple)
    stake_simple = sum((t["stake"] or 0) for t in simple if (t["stake_type"] or "").lower() != "freebet")
    pnl_combo = sum(real_pnl(t) for t in multi)
    stake_combo = sum((t["stake"] or 0) for t in multi if (t["stake_type"] or "").lower() != "freebet")

    print(f"  SIMPLES   : {len(simple):>4} tickets | misé {stake_simple:.0f}€ | "
          f"PnL {pnl_simple:+.0f}€ | ROI {(pnl_simple/stake_simple*100) if stake_simple else 0:+.1f}%")
    print(f"  COMBINÉS  : {len(multi):>4} tickets | misé {stake_combo:.0f}€ | "
          f"PnL {pnl_combo:+.0f}€ | ROI {(pnl_combo/stake_combo*100) if stake_combo else 0:+.1f}%")

    if pnl_combo > pnl_simple:
        print(f"  → Les combinés sont la source principale du PnL ({pnl_combo:+.0f}€ vs {pnl_simple:+.0f}€).")
    else:
        print(f"  → Les simples portent plus de PnL que les combinés ({pnl_simple:+.0f}€ vs {pnl_combo:+.0f}€).")

    # Combinés gagnés : profil moyen
    if won_combos:
        avg_legs = mean(t["legs_count"] for t in won_combos)
        odds_vals = [t["total_odds"] for t in won_combos if t["total_odds"]]
        avg_odds = mean(odds_vals) if odds_vals else 0
        cash_stakes = [t["stake"] for t in won_combos
                       if (t["stake_type"] or "").lower() != "freebet" and t["stake"]]
        avg_stake = mean(cash_stakes) if cash_stakes else 0
        med_pnl = median(real_pnl(t) for t in won_combos)
        print(f"\n  Profil typique d'un COMBO GAGNÉ (n={len(won_combos)}) :")
        print(f"    - Nb jambes médian : {median(t['legs_count'] for t in won_combos):.0f} (moy {avg_legs:.1f})")
        print(f"    - Cote totale moyenne : {avg_odds:.2f}")
        print(f"    - Mise moyenne (cash) : {avg_stake:.2f}€")
        print(f"    - PnL médian : {med_pnl:+.2f}€")


if __name__ == "__main__":
    main()
