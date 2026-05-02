# Legitimate angles — Multi_full variance/ROI improvements

**Date**: 2026-05-02
**Setup**: Multi_full preset, Winamax FR whitelist, dédup max1, flat stake 10€, magic_cotes_smart.

## Contexte

Multi_full = preset référence (+1593€/mois avril, +66% ROI/semestre walk-forward sous Winamax FR + dédup max1).
Trade-off observé : série rouge 4-15j sur 6 mois inévitable.
Skip-day post-perte rejeté (data-snooping).

Deux pistes statistiquement valides testées en parallèle.

---

## PISTE 1 — Filter leagues hyper-stables (out-of-sample strict)

### Méthodologie

1. Run Multi_full (Winamax FR + dédup max1) sur chaque semestre in-sample (S1-2024 → S2-2025) sans restriction supplémentaire de league.
2. Pour chaque combo généré, attribution proportionnelle du PnL et de la stake aux leagues de ses jambes (méthode pure, pas de re-backtest par league pour éviter changement de comportement de dédup).
3. Filtre stable = ROI > +20% sur CHAQUE des 4 semestres + n ≥ 5 paris attribués par semestre (volume crédible).
4. Test OOS strict sur S1-2026 (2026-01-01 → 2026-04-30) : Multi_full all leagues vs Multi_full restreint aux leagues stables.

### Leagues stables identifiées (in-sample)

6 leagues passent le filtre :

| Sport | League | Total n | S1-2024 ROI/n | S2-2024 ROI/n | S1-2025 ROI/n | S2-2025 ROI/n |
|---|---|---|---|---|---|---|
| football | LaLiga 2 | 226 | +140.4% / 56 | +119.4% / 67 | +55.5% / 51 | +20.1% / 52 |
| football | Serie A | 196 | +85.7% / 55 | +67.7% / 43 | +65.9% / 41 | +134.5% / 57 |
| football | Liga Portugal 2 | 171 | +81.1% / 49 | +28.4% / 41 | +123.3% / 47 | +109.3% / 34 |
| football | Serie B | 129 | +100.3% / 26 | +173.8% / 35 | +91.3% / 33 | +128.0% / 35 |
| ice-hockey | DEL 2 | 108 | +231.1% / 28 | +133.7% / 37 | +84.2% / 22 | +90.4% / 21 |
| football | Ligue 2 | 97 | +72.8% / 36 | +63.4% / 27 | +185.2% / 14 | +160.6% / 20 |

### Résultats OUT-OF-SAMPLE (S1-2026, 2026-01-01 → 2026-04-30)

| Variante | n combos | PnL | ROI | jours +/- | dailyWR | série rouge max |
|---|---|---|---|---|---|---|
| **Multi_full ALL (Winamax FR)** | 621 | **+5384.04€** | **+86.70%** | 80/40 | 66.7% | 4 |
| **Multi_full STABLE-only (6 leagues)** | 217 | +746.56€ | +34.40% | 39/51 | 43.3% | **10** |

### Verdict PISTE 1 : **REJETÉ**

- Le filtre ne survit PAS out-of-sample. Multi_full STABLE-only fait −60% de PnL absolu, −52pts de ROI, et **−23pts de daily winrate**.
- **La série rouge max DOUBLE (4 → 10 jours)** : c'est l'effet inverse de l'objectif de réduction de variance.
- jours +/- s'inverse même : 39/51 (jours rouges majoritaires) vs 80/40 baseline.
- Cause probable : sample shrinkage. 217 combos vs 621 (concentration risk) + l'effet "league-stable in-sample" est en grande partie un overfit. Les 4 semestres sont corrélés par le contexte global du marché ; survivre à 4 semestres consécutifs ne garantit pas la persistance.
- Conclusion : pas de signal exploitable. Garder Multi_full all leagues + Winamax FR whitelist.

---

## PISTE 2 — Magic recalibration récente (6 mois)

### Méthodologie

1. Recalibrer `magic_cotes` en groupant par sport×bucket×cote (rounded 0.01) sur **2025-10-01 → 2026-03-31** uniquement (6 mois).
2. Filtrer n ≥ 5 et EV > 0 (mêmes critères que magic_cotes_smart).
3. Sauvegardé dans `/tmp/magic_cotes_recent.json` (5900 entrées : foot=2991, basket=2344, hockey=287, baseball=30, tennis=248).
4. Test OOS sur **avril 2026** (2026-04-01 → 2026-04-30, 1 mois après calibration end).
5. Comparaison Multi_full + magic standard vs Multi_full + magic récente.

### Résultats OOS (avril 2026, Multi_full + Winamax FR + dédup max1)

| Variante | n combos | PnL | ROI | jours +/- | dailyWR | série rouge max |
|---|---|---|---|---|---|---|
| **Magic STANDARD (28 mois)** | 148 | **+1516.32€** | **+102.45%** | 19/11 | 63.3% | 3 |
| **Magic RECENT (6 mois)** | 204 | +258.97€ | +12.69% | 18/12 | 60.0% | **6** |

### Verdict PISTE 2 : **REJETÉ**

- Magic récente produit −83% de PnL absolu et −90pts de ROI.
- **La série rouge double aussi (3 → 6)**, daily WR baisse (63% → 60%).
- Volume +38% (148 → 204) mais avec ROI massivement plus faible : la magic récente s'ouvre à plus de buckets/cotes mais leur edge est plus bruité.
- Cause probable : 6 mois × 5 sports = sample-size insuffisant par bucket. Beaucoup de buckets ne dépassent le seuil n≥5 que grâce au régime de marché récent (variance d'échantillonnage), créant des "faux positifs" de calibration.
- Le bénéfice théorique de "recency" est dominé par le coût de "sample reduction".
- Conclusion : pas de signal exploitable. Garder magic_cotes_smart 28 mois.

---

## Synthèse

Aucune des deux pistes ne survit au test out-of-sample strict. Les deux **dégradent** le système (PnL, ROI, série rouge, daily WR) sans biais statistique. Multi_full all leagues + magic_cotes_smart 28 mois reste le setup optimal.

**Recommandation** :
- Ne pas implémenter ces filtres.
- La série rouge 4-15j observée sur 6 mois est inhérente à la structure de variance du système (combo-betting paris sportifs avec ROI ~+66%/semestre). La réduire significativement nécessite soit une réduction de stake (donc PnL), soit un changement de structure (sizing dynamique type Kelly/N — à explorer hors data-snooping), soit accepter le trade-off actuel.

### Fichiers générés

- `/tmp/legitimate_angles_runner.py` — code de test (helper, non destiné production)
- `/tmp/legitimate_angles_log.txt` — log brut d'exécution
- `/tmp/legitimate_angles_raw.json` — données structurées (résultats par league + summaries OOS)
- `/tmp/magic_cotes_recent.json` — magic recalibrée 6 mois (à supprimer si non utile)
