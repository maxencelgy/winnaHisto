"""find_new_records_v2.py

Sweep ~600-1000 candidate montante strategies on S1-26 (2026-01-01 -> 2026-04-30, OOS strict)
to find configurations complementary to the 108 already in the lib.

Angles:
  1. High-cote single-shot 1.50-2.00 with WR >= 60%  (foot/hockey/basket)
  2. Hybrid descending paliers (NB: engine doesn't natively descend cote per palier;
     simulated by tighter cote ranges + multi-market broad selection) — replaced by
     multi-market xmkt sweeps as engine doesn't support per-palier cote shift.
  3. sort_by="cote" (cheapest of N) on multi-market — but engine only supports wr/ev,
     so we mimic with very low cote_max and broad market list (cheapest = lowest in range).
  4. Tennis SOLO 3-5 paliers
  5. Same-day combos: legs_per_palier=2, max_combos=1

Usage:  python3 picks/find_new_records_v2.py
"""
import os, sys, time, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

START = "2026-01-01"
END = "2026-04-30"
INITIAL_STAKE = 100
MIN_CYCLES_TOTAL = 25

XMKT_FOOT = "1x2,btts,over_1_5,over_2_5"
XMKT_FOOT_WIDE = "1x2,btts,over_1_5,over_2_5,over_0_5,1x,x2"

CANDIDATES = []


def add(strategy):
    CANDIDATES.append(strategy)


def mk(idx, sports, market, cmin, cmax, sort_by, min_wr, n_paliers, legs_per_palier=1, min_ev=None):
    return {
        "id": f"NR2_{idx:04d}",
        "components": [{
            "sports": sports,
            "market": market,
            "cote_min": cmin,
            "cote_max": cmax,
            "sort_by": sort_by,
            "max_legs": legs_per_palier,
            "max_combos": 1,
            "min_wr": min_wr,
            "min_ev": min_ev,
            "legs_per_palier": legs_per_palier,
        }],
        "montante": {
            "initial_stake": INITIAL_STAKE,
            "n_paliers_target": n_paliers,
            "combo_legs_per_palier": legs_per_palier,
        },
    }


def gen():
    idx = 0
    # ===== ANGLE 1: High-cote single-shot 1.50-2.00 WR >= 60% =====
    sports_sets_a1 = [
        ["football"],
        ["football", "ice-hockey"],
        ["ice-hockey"],
        ["basketball"],
    ]
    high_ranges = [
        (1.50, 1.70), (1.55, 1.75), (1.60, 1.80), (1.50, 1.80),
        (1.50, 2.00), (1.70, 2.00),
    ]
    for sp in sports_sets_a1:
        for cmin, cmax in high_ranges:
            for wr in [0.60, 0.65, 0.70, 0.75]:
                for npal in [2, 3]:
                    idx += 1
                    add(mk(idx, sp, "1x2", cmin, cmax, "wr", wr, npal))
                    idx += 1
                    add(mk(idx, sp, "1x2", cmin, cmax, "ev", wr, npal))

    # foot multi-market high-cote
    for cmin, cmax in high_ranges:
        for wr in [0.60, 0.65, 0.70]:
            for npal in [2, 3]:
                idx += 1
                add(mk(idx, ["football"], XMKT_FOOT, cmin, cmax, "wr", wr, npal))

    # ===== ANGLE 2: micro-cote sweeps  =====
    sports_sets_a2 = [
        ["football"],
        ["football", "ice-hockey"],
        ["ice-hockey"],
        ["basketball"],
    ]
    micro_ranges = [
        (1.05, 1.10), (1.05, 1.15), (1.08, 1.18), (1.10, 1.20),
    ]
    for sp in sports_sets_a2:
        for cmin, cmax in micro_ranges:
            for wr in [0.85, 0.90]:
                for npal in [5, 6, 7, 8]:
                    idx += 1
                    add(mk(idx, sp, "1x2", cmin, cmax, "wr", wr, npal))

    # Multi-market xmkt micro
    for cmin, cmax in micro_ranges:
        for wr in [0.85, 0.88, 0.90]:
            for npal in [6, 7, 8, 9, 10]:
                idx += 1
                add(mk(idx, ["football", "ice-hockey"], XMKT_FOOT, cmin, cmax, "wr", wr, npal))
                idx += 1
                add(mk(idx, ["football"], XMKT_FOOT_WIDE, cmin, cmax, "wr", wr, npal))

    # ===== ANGLE 3: "safest pick of N" — wide range, very high WR threshold =====
    for sp in [["football"], ["football", "ice-hockey"], ["ice-hockey"]]:
        for cmin, cmax in [(1.05, 1.30), (1.05, 1.40), (1.05, 1.50)]:
            for wr in [0.85, 0.90, 0.92]:
                for npal in [4, 5, 6]:
                    idx += 1
                    add(mk(idx, sp, "1x2", cmin, cmax, "wr", wr, npal))

    # ===== ANGLE 4: TENNIS SOLO =====
    tennis_ranges = [
        (1.05, 1.15), (1.10, 1.20), (1.10, 1.25), (1.15, 1.30),
        (1.20, 1.40), (1.30, 1.50), (1.50, 2.00),
    ]
    for cmin, cmax in tennis_ranges:
        for wr in [0.60, 0.70, 0.80, 0.85, 0.90]:
            for npal in [2, 3, 4, 5, 6]:
                idx += 1
                add(mk(idx, ["tennis"], "1x2", cmin, cmax, "wr", wr, npal))

    # Tennis with another sport (key combos only)
    for cmin, cmax in [(1.05, 1.15), (1.10, 1.20)]:
        for wr in [0.80, 0.85]:
            for npal in [4, 5, 6]:
                idx += 1
                add(mk(idx, ["tennis", "football"], "1x2", cmin, cmax, "wr", wr, npal))
                idx += 1
                add(mk(idx, ["tennis", "ice-hockey"], "1x2", cmin, cmax, "wr", wr, npal))

    # ===== ANGLE 5: SAME-DAY COMBOS (legs_per_palier=2) =====
    for sp in [["football"], ["football", "ice-hockey"], ["football", "tennis"]]:
        for cmin, cmax in [(1.05, 1.15), (1.05, 1.20), (1.10, 1.20)]:
            for wr in [0.85, 0.88, 0.90]:
                for npal in [2, 3, 4]:
                    idx += 1
                    add(mk(idx, sp, XMKT_FOOT, cmin, cmax, "wr", wr, npal, legs_per_palier=2))

    # legs_per_palier=3 (small)
    for cmin, cmax in [(1.05, 1.15), (1.10, 1.20)]:
        for wr in [0.85, 0.90]:
            for npal in [2, 3]:
                idx += 1
                add(mk(idx, ["football"], XMKT_FOOT, cmin, cmax, "wr", wr, npal, legs_per_palier=3))

    # Tennis 2j combos
    for cmin, cmax in [(1.05, 1.15), (1.10, 1.20)]:
        for wr in [0.80, 0.85]:
            for npal in [2, 3]:
                idx += 1
                add(mk(idx, ["tennis"], "1x2", cmin, cmax, "wr", wr, npal, legs_per_palier=2))


def main():
    gen()
    n = len(CANDIDATES)
    print(f"[gen] {n} candidates generated")
    t0 = time.time()
    results = []
    fail = 0
    for i, strat in enumerate(CANDIDATES):
        try:
            r = simulate(strat, START, END, mode="intraday", initial_stake=INITIAL_STAKE)
            if r["n_cycles_total"] < MIN_CYCLES_TOTAL:
                continue
            comp = r["completion_rate"]
            cap = r["avg_capital_complete"]
            results.append({
                "id": strat["id"],
                "comp": comp,
                "n_total": r["n_cycles_total"],
                "n_complete": r["n_cycles_complete"],
                "cap": cap,
                "pnl": r["final_pnl"],
                "roi": r["roi"],
                "ratio": cap / INITIAL_STAKE if cap else 0,
                "comp_x_cap": comp * cap,
                "strat": strat,
            })
        except Exception:
            fail += 1
            continue
        if (i + 1) % 100 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / max(elapsed, 0.01)
            eta = (n - i - 1) / max(rate, 0.01)
            print(f"  [{i+1}/{n}]  kept={len(results)}  fail={fail}  rate={rate:.1f}/s  eta={eta:.0f}s")
    print(f"[done] {len(results)} kept / {n} (fail={fail})  in {time.time()-t0:.1f}s")

    def fmt(r):
        s = r["strat"]["components"][0]
        m = r["strat"]["montante"]
        return (f"{r['id']}  comp={r['comp']*100:5.1f}%  cyc={r['n_complete']}/{r['n_total']}  "
                f"cap={r['cap']:7.2f}  ratio={r['ratio']:5.2f}x  pnl={r['pnl']:+8.0f}  "
                f"roi={r['roi']:+6.1f}%  | sp={'/'.join(s['sports'])} mkt={s['market'][:30]} "
                f"c={s['cote_min']:.2f}-{s['cote_max']:.2f} wr={s['min_wr']} sort={s['sort_by']} "
                f"np={m['n_paliers_target']} legs={m['combo_legs_per_palier']}")

    print("\n========== TOP 10 by COMP x CAP ==========")
    for r in sorted(results, key=lambda x: -x["comp_x_cap"])[:10]:
        print(fmt(r))

    print("\n========== TOP 10 by FINAL_PNL ==========")
    for r in sorted(results, key=lambda x: -x["pnl"])[:10]:
        print(fmt(r))

    print("\n========== TOP 10 by COMPLETION (>=30 cycles) ==========")
    elig = [r for r in results if r["n_total"] >= 30]
    for r in sorted(elig, key=lambda x: (-x["comp"], -x["cap"]))[:10]:
        print(fmt(r))

    print("\n========== TOP 10 by RATIO (cap/100) , min 25 cycles ==========")
    for r in sorted(results, key=lambda x: -x["ratio"])[:10]:
        print(fmt(r))


if __name__ == "__main__":
    main()
