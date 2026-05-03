#!/usr/bin/env python3
"""META MIX v2 — analyse les meilleurs mixs réalistes."""
import sys, os, json, urllib.request, itertools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Liste des profils pratiques (≥40% completion + PnL >100€ + Avril positif)
PROFILES = [
    # Top par EV pratique de toute la lib
    "montante_o25_x2p_TOP_PRACTICAL",                # Over 2.5 cote 1.7-1.95 44% +528€ +186€ Apr
    "montante_hockey_combo2j_x2p_TOP_PRACTICAL",     # Hockey combo cote 1.25-1.50 52% +553€
    "montante_o15_combo2j_x2p_apr_freq",             # Foot O 1.5 combo 2j 54% +365€ +160€ Apr
    "montante_o15_x4p_apr_winner",                   # Foot O 1.5 ×4p 53% +269€ +166€ Apr
    "montante_hockey_combo2j_x2p_max_freq",          # Hockey combo cote 1.30-1.50 49% +471€
    "montante_o15_x4p_top_completion",               # Foot O 1.5 ×4p cote 1.20-1.40 56% +421€
    "montante_hockeybasket_combo3j_x3p_practical",   # Hockey+Basket combo 3j 47% +419€ +91€ Apr
    "montante_btts_x2p_practical",                    # BTTS 1.60-1.80 44% +277€ +44€ Apr
    "montante_basket_combo2j_x2p_practical",         # Basket combo 1.25-1.45 40% +284€
    "montante_o15_x2p_66pct_safe",                    # Foot O 1.5 1.35-1.55 66% +301€
]

# Get perfs from API
def get_perfs(sid):
    url = f"http://localhost:5051/api/montante-simulate?strategy={sid}&start=2026-01-01&end=2026-04-30&mode=intraday&initial_stake=10"
    try:
        d = json.loads(urllib.request.urlopen(url, timeout=30).read())
        s1_pnl = d.get("final_pnl", 0)
        # Avril
        url_apr = f"http://localhost:5051/api/montante-simulate?strategy={sid}&start=2026-04-01&end=2026-04-30&mode=intraday&initial_stake=10"
        d_apr = json.loads(urllib.request.urlopen(url_apr, timeout=30).read())
        apr_pnl = d_apr.get("final_pnl", 0)
        return {
            "s1_pnl": s1_pnl, "apr_pnl": apr_pnl,
            "compl": d.get("completion_rate", 0),
            "n_complete": d.get("n_cycles_complete", 0),
            "n_total": d.get("n_cycles_total", 0),
        }
    except Exception as e:
        print(f"err {sid}: {e}")
        return None

print("[META MIX v2] Mesure perfs individuelles...")
perfs = {}
for sid in PROFILES:
    p = get_perfs(sid)
    if p: perfs[sid] = p

print(f"\n=== Perfs individuelles ({len(perfs)} profils) ===")
print(f"{'Profile':<55s} {'S1 PnL':>9s} {'%':>5s} {'Apr PnL':>9s}")
print("-"*95)
for sid, p in sorted(perfs.items(), key=lambda x: -x[1]["s1_pnl"]):
    print(f"  {sid[:54]:<55s} {p['s1_pnl']:>+7.0f}€  {p['compl']*100:>3.0f}%  {p['apr_pnl']:>+7.0f}€")

# Generate top mixes (3, 4, 5)
print("\n[META MIX v2] Calcul tous les mixs 3/4/5 stratégies...")
mixes = []
keys = list(perfs.keys())
for k in [3, 4, 5]:
    for combo in itertools.combinations(keys, k):
        s1 = sum(perfs[c]["s1_pnl"] for c in combo)
        apr = sum(perfs[c]["apr_pnl"] for c in combo)
        compl_avg = sum(perfs[c]["compl"] for c in combo) / len(combo)
        cycles = sum(perfs[c]["n_complete"] for c in combo)
        capital = 10 * len(combo)
        mixes.append({
            "k": k, "profiles": list(combo),
            "s1_pnl": s1, "apr_pnl": apr,
            "compl_avg": compl_avg,
            "cycles_total": cycles,
            "capital": capital,
        })

# Top par S1 PnL
print(f"\n=== TOP 10 MIX par PnL S1-26 ===")
mixes.sort(key=lambda r: -r["s1_pnl"])
for r in mixes[:10]:
    print(f"  [{r['k']}-mix {r['capital']}€/jour]  S1 +{r['s1_pnl']:.0f}€  Apr +{r['apr_pnl']:.0f}€  compl moy {r['compl_avg']*100:.0f}%  cycles {r['cycles_total']}")
    for p in r["profiles"]:
        print(f"      • {p}")

print(f"\n=== TOP 10 MIX par PnL Avril ===")
mixes.sort(key=lambda r: -r["apr_pnl"])
for r in mixes[:10]:
    print(f"  [{r['k']}-mix {r['capital']}€/jour]  Apr +{r['apr_pnl']:.0f}€  S1 +{r['s1_pnl']:.0f}€  compl {r['compl_avg']*100:.0f}%")
    for p in r["profiles"]:
        print(f"      • {p}")

print(f"\n=== TOP 5 MIX 3-strats par EV pratique (S1 + 4×Apr, focus récent) ===")
mixes.sort(key=lambda r: -(r["s1_pnl"] + r["apr_pnl"]*4) if r["k"] == 3 else 0)
mix3 = [m for m in mixes if m["k"] == 3]
mix3.sort(key=lambda r: -(r["s1_pnl"] + r["apr_pnl"]*4))
for r in mix3[:5]:
    print(f"  [3-mix 30€/jour]  S1 +{r['s1_pnl']:.0f}€  Apr +{r['apr_pnl']:.0f}€  compl moy {r['compl_avg']*100:.0f}%")
    for p in r["profiles"]:
        print(f"      • {p}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/meta_mix_v2.json","w") as f:
    json.dump({"perfs": perfs, "top_mixes_s1": mixes[:30]}, f, indent=2, default=str)
print("\nSaved.")
