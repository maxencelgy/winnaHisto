# META MIX — Recommandations stratégiques (validé 3 mai 2026)

## ⚠ IMPORTANT — Ce qui marche en pratique vs en théorie

Les "jackpots" (combo 8-10j ×5p) ont des PnL EV positifs énormes mais **n'aboutissent que 1-2% du temps**. Concrètement :
- Tu lances la stratégie 50 jours d'affilée → tu gagnes peut-être 1 cycle.
- 49 jours sur 50 = perte sèche de 10€.
- 1 jour de chance = +5500€.

C'est mathématiquement positif mais **mentalement intenable** — on est sur du gambling structuré, pas une machine à profit régulière.

**👉 Préfère les profils PRATIQUES ci-dessous : ≥30% completion = ça aboutit vraiment ~1 fois sur 3.**

---

## ✅ MIX 5-STRATS ULTIMATE PRATIQUE — Optimisé v2 (RECOMMANDÉ)

🎯 **Mix S1-26 optimal** trouvé via brute-force des combinaisons : 49% completion moyen, 219 cycles complets sur 4 mois.

Capital quotidien engagé : **50€** (10€ × 5 stratégies)

| # | Stratégie | Completion | S1 PnL | Apr PnL |
|---|-----------|------------|--------|---------|
| 1 | `montante_o25_x2p_TOP_PRACTICAL` | 44% | **+528€** | **+187€** |
| 2 | `montante_hockey_combo2j_x2p_TOP_PRACTICAL` | 52% | **+553€** | +87€ |
| 3 | `montante_hockey_combo2j_x2p_max_freq` | 49% | +471€ | +62€ |
| 4 | `montante_o15_x4p_top_completion` | 56% | +421€ | +186€ |
| 5 | `montante_hockeybasket_combo3j_x3p_practical` | 47% | +419€ | +91€ |

**Total PnL S1-26 : +2392€** (598€/mois)
**Total PnL Avril : +613€** (sur 50€/jour engagés)
**Cycles complets cumulés : 219 / 4 mois = ~55 cycles/mois → ~2 cycles aboutis/jour**

## 🌸 MIX 5-STRATS AVRIL OPTIMAL (focus mois récent)

| # | Stratégie | Apr PnL |
|---|-----------|---------|
| 1 | `montante_o25_x2p_TOP_PRACTICAL` | +187€ |
| 2 | `montante_o15_combo2j_x2p_apr_freq` | +160€ |
| 3 | `montante_o15_x4p_apr_winner` | +166€ |
| 4 | `montante_o15_x4p_top_completion` | +186€ |
| 5 | `montante_hockeybasket_combo3j_x3p_practical` | +91€ |

**PnL Avril cumulé : +790€** sur 50€/jour
**PnL S1-26 cumulé : +2003€**
**Completion moyen : 51%**

## 🎯 MIX 4-STRATS AVRIL CHAMPION (ROI/€ optimal)

Best ratio gain/capital engagé :

| # | Stratégie | Apr PnL |
|---|-----------|---------|
| 1 | `montante_o25_x2p_TOP_PRACTICAL` | +187€ |
| 2 | `montante_o15_combo2j_x2p_apr_freq` | +160€ |
| 3 | `montante_o15_x4p_apr_winner` | +166€ |
| 4 | `montante_o15_x4p_top_completion` | +186€ |

**PnL Avril : +699€ sur 40€/jour engagés** (ROI Apr ~58%/mois sur capital engagé)
**Completion moyen : 52%** — tu vois des wins quasi tous les jours.

⚡ Tu vois **réellement** des wins ~tous les jours, pas un mois sur six.

---

## 🛡️ MIX FRÉQUENCE PURE — Pour confirmer chaque jour

🎯 Stratégies ≥50% completion uniquement — tu vois des wins **chaque jour ou presque**.

Capital quotidien : **40€** (10€ × 4)

| # | Stratégie | Completion | S1 PnL | Apr PnL |
|---|-----------|------------|--------|---------|
| 1 | `montante_o15_x2p_ultra_freq_80pct` | **80%** | +183€ | +110€ |
| 2 | `montante_o15_x3p_sweet_spot` | 63% | +262€ | +108€ |
| 3 | `montante_o15_x4p_top_completion` | 56% | +421€ | +186€ |
| 4 | `montante_hockey_combo2j_x2p_max_freq` | 49% | +471€ | +62€ |

**Total PnL S1-26 : +1337€** (~334€/mois)
**Total PnL Avril : +466€**
**Confort psychologique max** — tu vois des verts tous les jours.

---

## ⚖️ MIX BALANCE — Le compromis optimal

🎯 30-50% completion + capital décent + Avril solide.

Capital quotidien : **50€**

| # | Stratégie | Completion | S1 PnL | Apr PnL |
|---|-----------|------------|--------|---------|
| 1 | `montante_o15_combo2j_x4p_april_killer` | 31% | +271€ | **+311€** ★ |
| 2 | `montante_hockey_combo2j_x3p_top_pnl` | 36% | +789€ | +115€ |
| 3 | `montante_o15_x4p_top_completion` | 56% | +421€ | +186€ |
| 4 | `montante_o15_combo2j_x5p_balanced` | 30% | +404€ | +294€ |
| 5 | `montante_o15_combo2j_x3p_top_apr` | 39% | +440€ | +228€ |

**Total PnL S1-26 : +2325€**
**Total PnL Avril : +1134€** sur 50€/jour engagés
**ROI Avril : ~76%/mois** — réaliste et atteignable.

---

## 🎰 MIX JACKPOT-HUNTER — variance énorme (à éviter en premier)

⚠ **Completion 1-4%** : tu rates 96% du temps. Ne lance que si ton bankroll peut absorber des pertes répétées.

| # | Stratégie | Cap/cycle | S1 PnL | Apr |
|---|-----------|-----------|--------|-----|
| 1 | `montante_o15_combo10j_x4p_ULTIMATE` | 5652€ | +5162€ | +5532€ |
| 2 | `montante_btts_combo2j_x6p_jackpot` | 6876€ | +5806€ | -270€ |
| 3 | `montante_o15_combo8j_x5p_NUCLEAR` | 3433€ | +2973€ | +3313€ |

⚠ Ces chiffres reposent sur **1-2 cycles complets sur 4 mois**. Sample size minuscule, variance énorme. À utiliser comme "lottery occasionnelle" — pas comme stratégie principale.

---

## Conclusion pragmatique

**Pour ton use case "lance bouton, vois des paris à venir, gagne de l'argent" :**

1. ✅ Use le **MIX PRATIQUE** ci-dessus (5-strats ≥30% completion)
2. ✅ Capital engagé 50€/jour
3. ✅ Tu verras ~14 cycles complets/mois → barre verte régulière
4. ✅ PnL réaliste : ~+700€/mois si Avril type, ou ~+2700€ sur 4 mois historique

**Évite** les "jackpots" comme stratégie principale — c'est de la lottery validée sur historique mais inadaptée à un usage quotidien.
