# Exploration stratégies — 2026-05-02

Période : 2024-01-01 -> 2026-05-02 (853 jours), stake 10€/combo, magic cotes smart (sport x bucket).
Baseline H7 : 2 x EV3j foot+basket cote 2-5 + 2 x EV4j multi cote 10-50 -> ROI +227% (full-period).

## 1. Tableau comparatif full-period (8 pistes + baseline H7)

| Rang | Strat | ROI | PnL | Combos | WR | Combos/j | EUR/mois (10€) | Verdict vs H7 |
|------|-------|-----|-----|--------|-----|----------|----------------|---------------|
| 1 | **P5_top5_leagues** | **+344.0%** | 58 611€ | 1 704 | 10.3% | 2.00 | 2 092€ | bat H7 sur ROI mais volume divise par 2 |
| 2 | **P2_5legs** (nouveau leader) | **+295.8%** | 100 617€ | 3 401 | 27.7% | 3.99 | **3 591€** | **bat H7 +68pts ROI ET +831€/mois** |
| 3 | P3_triple_lottery | +258.4% | 87 994€ | 3 405 | 19.3% | 3.99 | 3 140€ | bat H7 +31pts ROI, +380€/mois |
| 4 | **H7 (baseline)** | +227.4% | 77 341€ | 3 401 | 28.1% | 3.99 | 2 760€ | référence |
| 5 | P1_5combos | +225.6% | 95 905€ | 4 252 | 23.9% | 4.98 | 3 422€ | ROI quasi identique, push volume seulement |
| 6 | P6_ultra_lottery | +222.6% | 75 669€ | 3 400 | 24.8% | 3.99 | 2 700€ | jamais mieux que 10-50 |
| 7 | P8_china_cba | +199.6% | 50 880€ | 2 549 | 34.4% | 2.99 | 1 816€ | China CBA dilue, pas pepite |
| 8 | P7_3lottery_tight | +196.7% | 83 642€ | 4 252 | 24.3% | 2 985€ | tighter cote = perd EV |
| 9 | P4_mix_sort | +81.1% | 27 106€ | 3 344 | 52.8% | 3.92 | 967€ | WR3j foot dilue gravement |

## 2. Walk-forward 5 semestres (top 3 + H7)

| Strat | S1-2024 | S2-2024 | S1-2025 | S2-2025 | S1-2026 | Moy | Std | Min | Max |
|-------|---------|---------|---------|---------|---------|-----|-----|-----|-----|
| P5_top5_leagues | +360.6% | +425.1% | +394.5% | +241.3% | +276.2% | +339.5% | 78.2 pts | +241.3% | +425.1% |
| **P2_5legs** | **+246.1%** | **+383.0%** | **+295.9%** | **+233.5%** | **+332.6%** | **+298.2%** | **61.8 pts** | **+233.5%** | **+383.0%** |
| P3_triple_lottery | +236.5% | +289.7% | +300.6% | +229.3% | +225.1% | +256.2% | 35.9 pts | +225.1% | +300.6% |
| H7 | +226.4% | +276.0% | +259.3% | +172.8% | +190.3% | +225.0% | 43.9 pts | +172.8% | +276.0% |

Critere validation (tous semestres > +30% ROI, variance < 200 pts) : **les 3 candidats passent**.

## 3. Verdict

**Nouveau leader : P2_5legs** (5-jambes : 2xEV3j fb 2-5 + 1xEV4j multi 10-50 + 1xEV5j multi 20-100).

Justification :
- ROI full-period **+295.8% (vs +227.4% H7) : +68 pts**.
- EUR/mois **3 591€ vs 2 760€ H7 : +30% gain mensuel** au meme stake.
- Walk-forward solide : moyenne +298% / 5 semestres, **min +233.5%** (jamais sous H7), max +383%.
- Variance 61.8 pts -> tres acceptable (P3 plus stable mais perd 42 pts ROI).
- Memes 4 combos/jour qu'H7 mais une jambe est upgradee EV4j -> EV5j 20-100 (pepite extreme).

P5_top5_leagues bat P2 sur ROI brut (+344% vs +296%) MAIS :
- Volume divise par deux (1 704 combos vs 3 401) -> seulement **2 092€/mois**.
- Variance 78.2 pts (la plus elevee), min 241.3%.
- Foot top5 only = 6/12 jours sans EV3j foot -> cassure de routine.
- Conclusion : interessant comme **filtre additionnel** sur la jambe EV3j foot, pas comme strat principale.

P3_triple_lottery offre la **stabilite max** (std 35.9 pts, min +225%) mais ROI 38 pts en dessous de P2.

## 4. Modification code

`backtest_engine.py` ligne 141 : boucle `for n_legs in (2, 3, 4)` -> `for n_legs in (2, 3, 4, 5)` pour activer 5-jambes (cap adaptatif 25 picks deja en place pour n=5).

## 5. Recommandations actionables

1. **Switch H7 -> P2_5legs en production** sur le morning_combos.
2. Surveiller la jambe EV5j 20-100 : si fail rate > 92% sur 30 jours, downgrade vers H7.
3. Tester variante **P2 + filtre top5** sur la jambe EV3j foot uniquement (ne pas filtrer la jambe basket) -> piste P9 a explorer.
4. Stake adaptatif : EV5j 20-100 a 5€ et reste a 10€ pourrait ameliorer le drawdown (Kelly fractionne).

## Datasets bruts
- `/Users/maxenceleguay/Sites/winnaHisto/datasets/strats_results.json`
- `/Users/maxenceleguay/Sites/winnaHisto/datasets/strats_walkforward.json`
