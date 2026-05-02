# Stratégies — Recherche série rouge MAX 2 jours (2026-05-02)

**Mission :** Trouver une stratégie avec **série rouge ≤ 2 jours** ET **PnL ≥ +1000€/mois sur avril 2026**, validée walk-forward 5 semestres.

**Setup commun :** Winamax FR, dedup=max1, sizing=flat, stake=10€, bankroll=100€.

---

## Phase 1 — Avril 2026 (2026-04-01 → 2026-05-02)

| # | Stratégie | n_combos | n_won | PnL | DD | Streak | Jours+ | Jours- | Daily WR | Filtre dur |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | Volume_max_smooth | 116 | 71 | +304€ | 44€ | **3j** | 20 | 10 | 66.7% | KO (streak 3j) |
| 2 | Smart_safe_volEV | 144 | 78 | +709€ | 94€ | **5j** | 19 | 12 | 61.3% | KO (streak 5j) |
| 3 | EV3j_volume | 164 | 77 | +524€ | 77€ | **4j** | 21 | 10 | 67.7% | KO (streak 4j) |
| 4 | **Sandwich_stable** | 158 | 79 | **+529€** | 92€ | **2j** | 20 | 11 | 64.5% | **OK** (streak 2j, PnL 500+) |
| 5 | Premier_focus_volume | 63 | 23 | -32€ | 101€ | **7j** | 10 | 19 | 34.5% | KO (perte) |
| 6 | Sport_stratifie | 97 | 58 | +267€ | 80€ | **2j** | 21 | 9 | 70.0% | Limite (streak OK, PnL <500€) |
| 7 | Volume_safe_18 | 64 | 49 | +183€ | 30€ | **2j** | 20 | 5 | 80.0% | Limite (streak OK, PnL <500€) |
| 8 | EV4j_low_cote | 153 | 80 | +577€ | 107€ | **4j** | 19 | 12 | 61.3% | KO (streak 4j) |

**Note :** L'objectif **PnL ≥ +1000€/mois ET streak ≤ 2j** n'est atteint par aucune piste. Trois pistes (Sandwich_stable, Sport_stratifie, Volume_safe_18) passent le filtre streak ≤ 2j sur avril 2026, mais ne dépassent pas +529€/mois.

---

## Phase 2 — Walk-forward 5 semestres

Filtre dur (≤2j ET ≥500€) : **Sandwich_stable seul** passe. Walk-forward étendu aux 2 finalistes streak-low.

### Sandwich_stable — `6 safe (1.3-1.8 multi-sport) + 5 EV3j (2-3) + 1 EV4j (5-10)`

| Semestre | n_combos | n_won | PnL | ROI | DD | **Streak** | Jours+/joués | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| S1-2024 | 845 | 399 | +2853€ | **33.8%** | 278€ | **8j** | 109/182 | streak FAIL |
| S2-2024 | 802 | 379 | +2533€ | **31.6%** | 259€ | **10j** | 104/183 | streak FAIL |
| S1-2025 | 919 | 484 | +3864€ | **42.0%** | 160€ | **6j** | 122/181 | streak FAIL |
| S2-2025 | 889 | 451 | +3375€ | **38.0%** | 265€ | **7j** | 115/184 | streak FAIL |
| S1-2026 | 671 | 363 | +2624€ | **39.1%** | 144€ | **4j** | 80/121 | streak FAIL |

**ROI semestriel : tous > 30%** mais **streak max ≥ 4j sur tous les semestres** (jusqu'à 10j sur S2-2024). La validation streak ≤ 2j sur 6 mois ÉCHOUE.

### Sport_stratifie — `1 safe + 1 EV3j par sport × 4 sports = 8 combos`

| Semestre | PnL | ROI | DD | **Streak** | Jours+/joués |
|---|---:|---:|---:|---:|---:|
| S1-2024 | +915€ | 18.3% | 228€ | **15j** | 83/165 |
| S2-2024 | +967€ | 20.3% | 118€ | **7j** | 89/154 |
| S1-2025 | +1371€ | 23.9% | 106€ | **5j** | 106/158 |
| S2-2025 | +1550€ | 30.2% | 166€ | **9j** | 101/167 |
| S1-2026 | +1688€ | 35.5% | 178€ | **4j** | 82/120 |

streak FAIL partout. ROI hétérogène (18-35%).

### Volume_safe_18 — `18 combos 2-jambes safe (1.4-2)`

| Semestre | PnL | ROI | DD | **Streak** | Jours+/joués |
|---|---:|---:|---:|---:|---:|
| S1-2024 | +448€ | 18.4% | 126€ | **5j** | 78/123 |
| S2-2024 | +547€ | 20.0% | 114€ | **8j** | 79/129 |
| S1-2025 | +606€ | 17.4% | 71€ | **6j** | 87/143 |
| S2-2025 | +578€ | 19.3% | 73€ | **5j** | 89/138 |
| S1-2026 | +578€ | 21.6% | 152€ | **8j** | 66/104 |

streak FAIL partout. ROI < 22% (sous-critère ROI > 30%).

---

## VERDICT — Trade-off mathématiquement impossible

### Trois confirmations :

1. **Aucune des 8 pistes** n'atteint simultanément `streak ≤ 2j` ET `PnL ≥ +1000€/mois` sur avril 2026.

2. **Le streak ≤ 2j observé en avril 2026** sur 3 pistes est un **artefact statistique d'échantillon court (30 jours)**. Le walk-forward 5 semestres prouve que sur des fenêtres de 6 mois, ces stratégies génèrent des séries rouges de **4 à 15 jours**.

3. **Mathématiquement attendu :** avec un daily-WR de 65%, la probabilité d'observer une série de ≥3 jours négatifs sur 180 jours est ≈ 1 - (1 - 0.35³)^178 ≈ 99.5%. Une série de 4j est attendue ~95% du temps. **Aucune stratégie multi-combos quotidienne diversifiée ne peut tenir < 3j sur un semestre.**

### Loi du trade-off variance/gains observée :

| Profil | Streak max attendu (semestre) | PnL/mois |
|---|---|---|
| Multi_full (référence) | 3-7j | +1593€ |
| Sandwich_stable (best PnL streak-aware) | 4-10j | +500-650€ |
| Volume_safe_18 (low-variance) | 5-8j | +90-110€ |
| Multi_12safe (référence streak) | 2j (avril seul) | +168€ |

**Plus on lisse (cotes basses, peu de combos), plus le PnL chute** ; **plus on monte le PnL, plus le streak s'étend**. La frontière de Pareto suggère un plafond ≈ +700€/mois pour streak ≤ 3-4j sur un semestre complet.

### Recommandation pragmatique

Si la contrainte stricte `streak ≤ 2j sur 6 mois` est non négociable, **seul un engagement < 1 combo/jour ou des fenêtres d'inactivité conditionnelles** (skip days post-perte) peuvent la satisfaire — au prix d'un PnL très limité.

**Best compromis avril 2026 :** `Sandwich_stable` (+529€/mois, streak avril 2j, walk-forward ROI moyen +37%/semestre, mais streak réel sur 6 mois 4-10j).

**Best compromis longue durée déjà en prod :** `Multi_full` reste le meilleur PnL avec streak 3-7j semestriel (+1593€/mois avril).

### Composition des 3 finalistes (pour reference)

```python
# Sandwich_stable
[{"max_legs":2,"cote_min":1.3,"cote_max":1.8,"sort_by":"wr","sports":ALL,"max_combos":6},
 {"max_legs":3,"cote_min":2.0,"cote_max":3.0,"sort_by":"ev","sports":ALL,"max_combos":5},
 {"max_legs":4,"cote_min":5.0,"cote_max":10.0,"sort_by":"ev","sports":ALL,"max_combos":1}]
# dedup=max1, bookmaker=winamax_fr, flat 10€
```

---
**Date :** 2026-05-02. **Engine :** `/Users/maxenceleguay/Sites/winnaHisto/backtest_engine.py` via `/api/backtest-hybrid`.
