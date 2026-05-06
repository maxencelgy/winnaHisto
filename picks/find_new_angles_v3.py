#!/usr/bin/env python3
"""Sweep nouveaux angles non explorés:
  A. 2 paliers ULTRA-SAFE ≥85% completion (sécuriser 2p à 90%+)
  B. Tennis-only montantes (data tennis solide mais sous-exploitée)
  C. Combos 2j daily WR sort (2 picks combinés par palier)
  D. TOP5-only montantes (filtre included_leagues = TOP5 elite)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
PERIOD = ("S1-26", "2026-01-01", "2026-04-30")

CANDS = []

# A. 2 PALIERS ULTRA-SAFE — chercher 90%+ completion
# Cote ultra-basse 1.05-1.12 + WR magic ≥90% sur seulement 2 paliers
A_SPORTS = [
    (["football","ice-hockey"], "FH"),
    (["football","ice-hockey","tennis","basketball"], "FHTB"),
    (["football"], "F"),
    (["football","tennis"], "FT"),
]
A_MARKETS = [
    "1x2",
    "1x2,btts,over_1_5,over_2_5",
]
A_CRANGES = [(1.03,1.08), (1.05,1.10), (1.05,1.12), (1.07,1.13), (1.08,1.15)]
A_MINWR = [0.88, 0.90, 0.92]
for sports, sname in A_SPORTS:
    for mkt in A_MARKETS:
        for cmin, cmax in A_CRANGES:
            for mwr in A_MINWR:
                for sort in ["wr", "ev"]:
                    CANDS.append({
                        "id": f"A_2P_{sname}_{mkt[:3]}_{cmin}-{cmax}_wr{int(mwr*100)}_{sort}",
                        "kind": "A_2P_ULTRA_SAFE",
                        "components": [{"sports": sports, "market": mkt,
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": 2,
                                      "combo_legs_per_palier": 1},
                    })

# B. TENNIS-ONLY montantes
B_CRANGES = [(1.10,1.25), (1.15,1.30), (1.20,1.35), (1.25,1.45), (1.30,1.50)]
B_NPS = [2, 3, 4, 5]
B_MINWR = [None, 0.70, 0.75, 0.80]
for cmin, cmax in B_CRANGES:
    for n_p in B_NPS:
        for mwr in B_MINWR:
            for sort in ["wr", "ev"]:
                CANDS.append({
                    "id": f"B_TENNIS_{cmin}-{cmax}_p{n_p}_wr{mwr}_{sort}",
                    "kind": "B_TENNIS",
                    "components": [{"sports": ["tennis"], "market": "1x2",
                                    "cote_min": cmin, "cote_max": cmax,
                                    "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                    "min_wr": mwr, "min_ev": None,
                                    "legs_per_palier": 1}],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 1},
                })

# C. COMBOS 2J DAILY (legs_per_palier=2)
C_SPORTS = [
    (["football","ice-hockey"], "FH"),
    (["football"], "F"),
]
C_CRANGES = [(1.05,1.15), (1.05,1.20), (1.08,1.20), (1.10,1.25)]
C_MINWR = [0.85, 0.88, 0.90]
for sports, sname in C_SPORTS:
    for mkt in ["1x2,btts,over_1_5,over_2_5", "1x2"]:
        for cmin, cmax in C_CRANGES:
            for mwr in C_MINWR:
                for n_p in [2, 3]:
                    for sort in ["wr", "ev"]:
                        CANDS.append({
                            "id": f"C_COMBO2J_{sname}_{mkt[:3]}_{cmin}-{cmax}_wr{int(mwr*100)}_p{n_p}_{sort}",
                            "kind": "C_COMBO2J",
                            "components": [{"sports": sports, "market": mkt,
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": 2}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": 2},
                        })

# D. Cote 1.50-1.75 (mid-cote) sort=ev WR≥55% — angle volume max
D_SPORTS = [
    (["football","ice-hockey"], "FH"),
    (["football","ice-hockey","tennis","basketball"], "FHTB"),
    (["football","tennis"], "FT"),
]
for sports, sname in D_SPORTS:
    for mkt in ["1x2,btts,over_1_5,over_2_5", "1x2"]:
        for cmin, cmax in [(1.40,1.55), (1.45,1.60), (1.50,1.70), (1.55,1.75)]:
            for mwr in [0.55, 0.60, 0.65]:
                for n_p in [2, 3]:
                    for sort in ["ev", "wr"]:
                        CANDS.append({
                            "id": f"D_MID_{sname}_{mkt[:3]}_{cmin}-{cmax}_wr{int(mwr*100)}_p{n_p}_{sort}",
                            "kind": "D_MIDCOTE",
                            "components": [{"sports": sports, "market": mkt,
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": 1}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": 1},
                        })

print(f"[v3] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, PERIOD[1], PERIOD[2], mode="intraday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 25:
            results.append({
                "id": s["id"],
                "kind": s["kind"],
                "comp": r["completion_rate"],
                "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"],
                "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
                "strat": s,
            })
    except Exception:
        pass

print(f"\n[v3] {len(results)} viable (≥25 cycles)")

# Sort by completion × cap (best risk/reward montante)
def score(r):
    return r["comp"] * r["cap"]

results.sort(key=lambda r: -score(r))

print(f"\n=== TOP 30 par completion × cap ===")
print(f"  {'kind':<15} {'compl%':>6} {'n_c/tot':>8} {'cap€':>6} {'pnl€':>7}  id")
for r in results[:30]:
    print(f"  {r['kind']:<15} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>5.0f} {r['pnl']:>+6.0f}  {r['id']}")

# Top par kind
for kind in ["A_2P_ULTRA_SAFE", "B_TENNIS", "C_COMBO2J", "D_MIDCOTE"]:
    sub = [r for r in results if r["kind"] == kind]
    sub.sort(key=lambda r: -score(r))
    print(f"\n=== TOP 8 {kind} ===")
    print(f"  {'compl%':>6} {'n_c/tot':>8} {'cap€':>6} {'pnl€':>7}  id")
    for r in sub[:8]:
        print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>5.0f} {r['pnl']:>+6.0f}  {r['id']}")

# Save full results
out = "/tmp/find_new_angles_v3.json"
with open(out, "w") as f:
    json.dump([{k: v for k, v in r.items() if k != "strat"} for r in results], f, indent=2)
print(f"\nSaved {out}")
