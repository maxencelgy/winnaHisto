# ML (LightGBM) vs Magic Cotes — comparaison OOS stricte

**Date** : 2026-05-02
**Question** : un gradient boosting peut-il prédire `home_won` mieux que le système "magic cotes" (Winamax) en out-of-sample ?
**Réponse courte** : **Non — pas pour générer du ROI sur cotes Winamax.** Les deux approches ont des métriques de classification quasi équivalentes, et **toutes les stratégies testées (ML, magic, naïve favori, stack) sont en ROI négatif** sur le marché 1X2 brut. La force des magic cotes vient des **combinés cote × marché × ligue × seuil EV**, pas de la prédiction `home_won` simple. Le ML léger n'extrait aucun edge supplémentaire.

---

## 1. Setup expérimental

- **Source** : `datasets/sofascore_unified/{football,basketball,ice-hockey,baseball,tennis}.csv`
- **Lignes valides après cleaning** (`hs+as>0`, `odds_1` & `odds_2` valides) : ~552k
- **Train** : 2024-01-01 → 2025-12-31 (~420k lignes)
- **Test OOS** : 2026-01-01 → 2026-05-02 — **131 917 matchs**
  - tennis 52 238, basketball 39 728, football 32 289, ice-hockey 5 482, baseball 2 180

### Features (17 numériques + 5 sport one-hot)
`cote_1, cote_2, cote_x, ip_1=1/cote_1, ip_2, ip_x, overround, fair_p1, fair_p2, cote_ratio, log_cote_ratio, cote_diff, has_draw, day_of_week, month, league_freq` (frequency encoding sur train) + `sport_*`.
**Exclus** (target leakage / cardinalité) : `total_score`, `btts`, `home`, `away`.

### Modèles comparés
1. **Naive favori** : `home_won_pred = (cote_1 < cote_2)` ; proba = `fair_p1 = ip_1/overround`
2. **Magic lookup** (`magic_cotes_smart.json`) : pour chaque (sport, league, cote_1), match dans une fenêtre ±5%, `n≥5`. Fallback `fair_p1` si pas de match.
3. **LightGBM** : `n_estimators=400, lr=0.05, max_depth=6, num_leaves=63, min_data_in_leaf=200`, early stopping (best iter = 84).
4. **Stacking** : `0.5*P_LGB + 0.5*WR_magic` (fallback LGB).

**Match rate magic** : seulement **14.28%** des matchs test (18 844/131 917) ont une magic cote utilisable.

---

## 2. Métriques de classification (full test, n=131 917)

| Modèle | Accuracy | Log loss | AUC ROC | Brier |
|---|---:|---:|---:|---:|
| Naive favori (`fair_p1`) | 0.6831 | 0.5813 | 0.7583 | 0.1992 |
| Magic + fallback fair_p1 | 0.6860 | 0.5834 | 0.7555 | 0.1999 |
| **LightGBM** | **0.6891** | **0.5781** | **0.7595** | **0.1982** |

**Sur le sous-ensemble magic-matched (n=18 844)** :

| Modèle | Accuracy | Log loss | AUC | Brier |
|---|---:|---:|---:|---:|
| Magic seul | 0.6264 | 0.6510 | 0.6814 | 0.2282 |
| Naive `fair_p1` | 0.6267 | 0.6368 | 0.6839 | 0.2235 |
| **LightGBM** | **0.6329** | **0.6346** | **0.6847** | **0.2225** |

**Insights** :
- LGB > naive d'environ **+0.6 pt d'accuracy**, **+0.0012 d'AUC**, gain de log loss/Brier marginal. Le bookmaker (cotes) capture déjà ~99% du signal.
- Magic seul **sous-performe** la naive `fair_p1` sur le sous-ensemble magic-matched (logloss 0.651 vs 0.637). Le WR observé sur n≥5 est trop bruité comme proba calibrée.
- LGB "consomme" déjà l'info des cotes : top features = `cote_1` (gain 561k), `fair_p1` (272k), `cote_diff` (153k), `ip_1` (61k), `cote_ratio` (22k). `league_freq` et `month` jouent un rôle mineur. Aucune feature exotique ne ressort.

---

## 3. Backtest ROI — stake fixe 10€/pick, side = home, S1-2026

| Stratégie | n picks | WR | ROI | PnL |
|---|---:|---:|---:|---:|
| All home (sanity) | 131 917 | 53.01% | −6.17% | −81 425€ |
| Naive favori (c1<c2) | 77 607 | 68.12% | −1.93% | −15 014€ |
| Magic WR>0.65 | 7 778 | 69.17% | −2.13% | −1 657€ |
| Magic WR>0.70 | 6 311 | 71.87% | **−0.93%** | −586€ |
| Magic WR>0.75 | 4 432 | 75.09% | −2.27% | −1 004€ |
| LGB P>0.65 | 40 828 | 78.97% | −2.36% | −9 644€ |
| LGB P>0.70 | 31 776 | 82.18% | −2.08% | −6 625€ |
| LGB P>0.75 | 25 868 | 84.43% | −2.14% | −5 532€ |
| Stack P>0.65 | 42 848 | 78.19% | −2.36% | −10 091€ |
| Stack P>0.70 | 33 019 | 81.68% | −2.08% | −6 879€ |
| Stack P>0.75 | 26 877 | 83.98% | −2.13% | −5 736€ |
| LGB>0.65 ∩ Magic>0.65 | 4 146 | 76.34% | −2.34% | −972€ |

**Aucune stratégie singleton n'est ROI-positive.** Le bookmaker prend sa marge (~5–7% overround) et les WR observés correspondent aux probas implicites — pas d'edge structurel sur le marché 1X2 simple.

### LGB P>0.65 par sport
| Sport | n | WR | ROI |
|---|---:|---:|---:|
| football | 5 385 | 77.34% | **+2.86%** |
| ice-hockey | 1 081 | 79.74% | **+4.97%** |
| tennis | 17 556 | 79.81% | −1.69% |
| basketball | 16 651 | 78.74% | −5.04% |
| baseball | 155 | 58.71% | −23.74% |

**Edge potentiel** : ice-hockey (+5.0% ROI, n=1 081) et football (+2.9% ROI, n=5 385) avec LGB seuil 0.65. Volume modeste mais cohérent avec la littérature (NHL/foot top5 souvent légèrement inefficaces côté favoris). Basketball et baseball franchement négatifs → à éviter en pick simple.

---

## 4. Verdict

### Le ML est **équivalent**, pas supérieur
- LightGBM bat la naive de **+0.6pt d'accuracy** et **−0.003 logloss** : statistiquement réel sur 132k obs mais économiquement marginal.
- Le ML **ne génère pas de ROI positif** sur les cotes Winamax brutes (1X2 home), idem magic seul.
- Le **stacking ML+magic** ne crée pas d'edge non plus (ROI ~−2.1% à −2.4% sur tous les seuils).

### Pourquoi magic cotes "fonctionne" en pratique mais pas ici
Le système Multi_full **+66% ROI/semestre** ne vient PAS du marché 1X2 simple : il combine
1. **combinés N legs** (effet payout × WR par leg),
2. **filtres EV multi-fenêtres** (3j/5j/6j),
3. **plusieurs marchés** (1, 2, BTTS, OU) — pas que `home`,
4. **ligues secondaires** moins liquides (cf. `strategies_exploration_v2`),
5. **sélection magic** avec n≥30 typiquement, pas n≥5.

Ce backtest teste une **prédiction binaire `home_won` en pari simple**, ce qui n'est pas la surface d'edge du système.

### Recommandations actionnables
1. **Ne pas remplacer magic par ML pour les picks** : pas de gain économique, complexifie la stack.
2. **Tester ML comme filtre additionnel** sur les combinés H9 : exiger `LGB_proba(home_won) > 0.70` pour les legs `home` du combo. À mesurer sur les 28 mois walk-forward — pourrait réduire la variance sans toucher l'EV.
3. **Edge ice-hockey/football LGB>0.65** (+5% / +3% ROI) : volume faible mais piste à explorer en pari simple ciblé. À valider walk-forward avant déploiement.
4. **Étendre les features** pour gain ML réel : ELO/forme dynamique, repos jours, B2B basketball, surface tennis, fatigue ATP/WTA. Les features actuelles ne donnent au ML que ce que les cotes contiennent déjà.
5. **ML pour autres targets** plus prometteur : `total_score > seuil`, `btts`, écart de score — marchés dérivés où les cotes sont moins efficaces.

### Conclusion
Le **gradient boosting léger est équivalent à la baseline cotes** pour `home_won` et **n'apporte rien sur les magic cotes en pari simple**. La supériorité du système Multi_full provient de la combinaison combos × marchés × filtres EV — pas d'une meilleure prédiction `home_won`. **Magic cotes reste l'outil principal** ; le ML peut éventuellement servir de **filtre de réduction de variance** sur les legs combo, à valider en walk-forward.

---

## Annexe — Top 10 feature importance LightGBM (gain)
| Feature | Gain |
|---|---:|
| cote_1 | 560 631 |
| fair_p1 | 271 523 |
| cote_diff | 152 651 |
| ip_1 | 60 835 |
| cote_ratio | 22 207 |
| league_freq | 11 141 |
| fair_p2 | 5 611 |
| overround | 4 474 |
| cote_2 | 4 132 |
| month | 2 931 |

Toutes les features dérivées de la cote home dominent (>95% du gain). Aucun signal calendaire ou structurel significatif au-delà.
