#!/usr/bin/env python3
"""
Analyse de l'historique Winamax exporté par winamax-history.js.

Usage :
    python3 analyze.py                              # cherche le dernier winamax-history-*.csv dans ~/Downloads
    python3 analyze.py /chemin/vers/le.csv          # fichier explicite
    python3 analyze.py --min-n 5 file.csv           # ne montre que les cotes avec ≥5 paris

Sorties :
    - Top cotes avec 100% winrate (triées par n)
    - Top cotes avec 0% winrate (triées par n)
    - Tableau complet trié par n descendant
    - Tableau "edge" (EV par pari) trié par EV décroissant
    - Splits par sport et par marché
    - Sauvegarde un CSV résumé : winamax-stats.csv
"""

import csv
import sys
import glob
import os
from collections import defaultdict
from pathlib import Path


def find_default_csv():
    candidates = sorted(
        glob.glob(str(Path.home() / "Downloads" / "winamax-history-*.csv")),
        key=os.path.getmtime,
        reverse=True,
    )
    if candidates:
        return candidates[0]
    candidates = sorted(
        glob.glob("winamax-history-*.csv"),
        key=os.path.getmtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def settled(rows):
    return [r for r in rows if r["selection_status"] in ("Gagné", "Perdu")]


def fnum(s):
    try:
        return float((s or "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def group_by(rows, key_fn):
    g = defaultdict(lambda: {"won": 0, "total": 0})
    for r in rows:
        k = key_fn(r)
        if k is None:
            continue
        g[k]["total"] += 1
        if r["selection_status"] == "Gagné":
            g[k]["won"] += 1
    return g


def fmt_table(rows, headers):
    widths = [max(len(h), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
    line = lambda parts: "  ".join(str(p).ljust(w) for p, w in zip(parts, widths))
    print(line(headers))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print(line(r))


def section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def stats_table(group, label, min_n=1):
    out = []
    for k, v in group.items():
        if v["total"] < min_n:
            continue
        wr = v["won"] / v["total"]
        # Pour cotes : EV par 1€ misé = winrate * cote - 1. Pour autres dimensions on n'a pas la cote unique → skip.
        odds = fnum(k) if label == "cote" else None
        ev = (wr * odds - 1) if odds else None
        out.append((k, v["total"], v["won"], wr, ev))
    return out


def print_odds_groups(rows, min_n=1):
    g = group_by(rows, lambda r: (fnum(r["selection_odds"]) and f"{fnum(r['selection_odds']):.2f}"))
    table = stats_table(g, "cote", min_n=min_n)

    section(f"Cotes EXACTES avec 100% de winrate (min n={min_n})")
    perfect = [t for t in table if t[3] == 1.0]
    perfect.sort(key=lambda x: -x[1])
    fmt_table(
        [(c, n, w, "100.0%", f"+{ev:.3f}") for c, n, w, _, ev in perfect],
        ["cote", "n", "gagnés", "winrate", "EV"],
    )

    section(f"Cotes EXACTES avec 0% de winrate (min n={min_n})")
    zero = [t for t in table if t[3] == 0.0]
    zero.sort(key=lambda x: -x[1])
    fmt_table(
        [(c, n, w, "0.0%", f"{ev:.3f}") for c, n, w, _, ev in zero],
        ["cote", "n", "gagnés", "winrate", "EV"],
    )

    section(f"Toutes les cotes triées par n décroissant (min n={min_n})")
    by_n = sorted(table, key=lambda x: -x[1])
    fmt_table(
        [(c, n, w, f"{wr*100:.1f}%", f"{ev:+.3f}") for c, n, w, wr, ev in by_n],
        ["cote", "n", "gagnés", "winrate", "EV"],
    )

    section(f"Top edges : meilleur EV avec n significatif (min n=10)")
    edges = [t for t in table if t[1] >= 10]
    edges.sort(key=lambda x: -x[4])
    fmt_table(
        [(c, n, w, f"{wr*100:.1f}%", f"{ev:+.3f}") for c, n, w, wr, ev in edges[:20]],
        ["cote", "n", "gagnés", "winrate", "EV"],
    )

    return table


def save_summary(table, path):
    with open(path, "w", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cote", "n", "gagnés", "winrate", "EV"])
        for c, n, won, wr, ev in sorted(table, key=lambda x: float(x[0])):
            w.writerow([c, n, won, f"{wr:.4f}", f"{ev:.4f}" if ev is not None else ""])
    print(f"\nRésumé sauvegardé → {path}")


def split_dimension(rows, key, label):
    g = group_by(rows, lambda r: (r.get(key) or "").strip() or "(vide)")
    table = stats_table(g, label)
    section(f"Split par {label}")
    table.sort(key=lambda x: -x[1])
    fmt_table(
        [(k, n, w, f"{wr*100:.1f}%") for k, n, w, wr, _ in table],
        [label, "n", "gagnés", "winrate"],
    )


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a.split("=")[0].lstrip("-"): (a.split("=")[1] if "=" in a else True) for a in argv[1:] if a.startswith("--")}
    min_n = int(flags.get("min-n", 1))

    path = args[0] if args else find_default_csv()
    if not path or not os.path.exists(path):
        print("Aucun CSV trouvé. Donne le chemin en argument :")
        print("  python3 analyze.py /chemin/winamax-history-2026-04-26.csv")
        return 1

    print(f"Source : {path}")
    rows = load(path)
    settled_rows = settled(rows)
    print(f"Lignes totales : {len(rows)} | settled (Gagné/Perdu) : {len(settled_rows)}")

    table = print_odds_groups(settled_rows, min_n=min_n)
    split_dimension(settled_rows, "selection_sport", "sport")
    split_dimension(settled_rows, "selection_market", "marché")
    split_dimension(settled_rows, "ticket_type", "type ticket")

    out = Path(path).with_name("winamax-stats.csv")
    save_summary(table, out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
