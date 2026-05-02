#!/usr/bin/env python3
"""Tester quelle stratégie a la courbe la plus lisse + beaux gains sur avril 2026."""
import urllib.request, json, sys

URL = "http://127.0.0.1:5050/api/backtest-hybrid"
DATE_START = "2026-04-01"
DATE_END = "2026-05-02"

# 8 stratégies candidates pour la "courbe lisse + beaux gains"
strategies = {
    "H_daily (baseline)": {"preset": "H_daily"},
    "H_daily_boost": {
        # H_daily + 1 EV3j cote 2-5 (boost ROI sans casser la régularité)
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.5, "sort_by": "wr",
             "sports": ["football","basketball"], "max_combos": 5},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 4.0, "sort_by": "wr",
             "sports": ["football","basketball"], "max_combos": 2},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football","basketball"], "max_combos": 1},
        ],
    },
    "H_smooth (3 safe + 2 EV3j)": {
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football","basketball"], "max_combos": 3},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football","basketball"], "max_combos": 2},
        ],
    },
    "H_balance (4 safe + 1 EV3j + 1 EV4j)": {
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football","basketball"], "max_combos": 4},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football","basketball"], "max_combos": 1},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football","basketball","ice-hockey","baseball","tennis"], "max_combos": 1},
        ],
    },
    "H_safe_only (10 WR2j)": {
        "components": [
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football","basketball"], "max_combos": 10},
        ],
    },
    "H_stable (rappel)": {"preset": "H_stable"},
    "H7 (rappel)": {"preset": "H7"},
    "H_daily + dedup max1": {"preset": "H_daily", "dedup": "max1"},
}

def run(spec):
    params = {"date": DATE_START, "end_date": DATE_END,
              "sizing": "flat", "stake": "10", "bankroll": "100"}
    if "preset" in spec:
        params["preset"] = spec["preset"]
    if "components" in spec:
        params["components"] = json.dumps(spec["components"])
    if "dedup" in spec:
        params["dedup"] = spec["dedup"]
    qs = urllib.parse.urlencode(params)
    return json.loads(urllib.request.urlopen(URL + "?" + qs, timeout=60).read())

import urllib.parse

print(f"{'Stratégie':40s} {'n':>5s} {'WR%':>5s} {'jrs+/-':>9s} {'win%j':>6s} {'PnL€':>7s} {'ROI%':>6s} {'BR_fin':>7s} {'DD':>5s} {'volat':>6s}")
print("-" * 105)

results = []
for name, spec in strategies.items():
    try:
        d = run(spec)
        if d.get("error"):
            print(f"{name:40s} ERR: {d['error'][:60]}")
            continue
        # Calcule volatilité = écart-type des PnL journaliers
        daily_pnls = [day["pnl"] for day in d["daily"]]
        if daily_pnls:
            mean_p = sum(daily_pnls) / len(daily_pnls)
            var = sum((p - mean_p) ** 2 for p in daily_pnls) / len(daily_pnls)
            std = var ** 0.5
        else:
            std = 0
        ratio = (d["pnl_total"] / d["max_drawdown"]) if d["max_drawdown"] > 0 else 999
        results.append({
            "name": name,
            "n": d["n_combos_total"],
            "wr": d["wr_combos"] * 100,
            "green": d["n_days_green"],
            "red": d["n_days_red"],
            "win_pct": d["daily_win_rate"] * 100,
            "pnl": d["pnl_total"],
            "roi": d["roi"] * 100,
            "br_final": d["bankroll_final"],
            "dd": d["max_drawdown"],
            "std": std,
            "ratio": ratio,
        })
        print(f"{name:40s} {d['n_combos_total']:>5d} {d['wr_combos']*100:>5.1f} "
              f"{d['n_days_green']:>2d}/{d['n_days_red']:<2d}     {d['daily_win_rate']*100:>5.0f}% "
              f"{d['pnl_total']:>+7.0f} {d['roi']*100:>+6.1f} {d['bankroll_final']:>7.0f} "
              f"{d['max_drawdown']:>5.0f} {std:>6.1f}")
    except Exception as e:
        print(f"{name:40s} EXCEPTION: {e}")

print()
print("=== Top 3 par RATIO ROI / DrawDown (best risk/reward) ===")
results.sort(key=lambda r: -r["ratio"])
for r in results[:3]:
    print(f"  ⭐ {r['name']}: ROI {r['roi']:+.1f}% / DD {r['dd']:.0f}€ → ratio {r['ratio']:.1f} | "
          f"jours {r['green']}/{r['green']+r['red']} ({r['win_pct']:.0f}%) | volat std {r['std']:.0f}€")

print()
print("=== Top 3 par % JOURS GAGNANTS (courbe la plus lisse) ===")
results.sort(key=lambda r: -r["win_pct"])
for r in results[:3]:
    print(f"  ⭐ {r['name']}: {r['win_pct']:.0f}% jours gagnants ({r['green']}/{r['green']+r['red']}) | "
          f"ROI {r['roi']:+.1f}% | DD {r['dd']:.0f}€")

print()
print("=== Top 3 par BR FINALE (gains absolus) ===")
results.sort(key=lambda r: -r["br_final"])
for r in results[:3]:
    print(f"  ⭐ {r['name']}: BR final {r['br_final']:.0f}€ | ROI {r['roi']:+.1f}% | "
          f"jours+ {r['win_pct']:.0f}% | DD {r['dd']:.0f}€")

print()
print("=== RECOMMANDATION ===")
# Score composite : %jours gagnants × √ROI / √DD
for r in results:
    r["score"] = r["win_pct"] * (max(r["roi"], 1) ** 0.5) / max(r["dd"], 1) ** 0.5
results.sort(key=lambda r: -r["score"])
print(f"Meilleur compromis 'courbe lisse + gains' : **{results[0]['name']}**")
print(f"  → BR 100€ → {results[0]['br_final']:.0f}€ en avril 2026")
print(f"  → {results[0]['win_pct']:.0f}% jours gagnants ({results[0]['green']}/{results[0]['green']+results[0]['red']})")
print(f"  → ROI {results[0]['roi']:+.1f}% | DD max {results[0]['dd']:.0f}€ | volat {results[0]['std']:.0f}€/j")
