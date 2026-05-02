# Marchés étendus (1×2 + Over/Under + BTTS) — Backtest Multi_full

**Date :** 2026-05-02
**Mission :** Tester si Multi_full étendu (1×2 + Over/Under + BTTS) améliore le ROI ET réduit la série rouge versus Multi_full standard (1×2 only).

---

## Résultat critique : pas de données Over/Under

L'audit du dataset `sofascore_unified` montre :

| Sport       | Total rows | with O/U | with BTTS |
| ----------- | ---------: | -------: | --------: |
| baseball    |     25 239 |        0 |         0 |
| basketball  |    178 651 |        0 |         0 |
| football    |    222 317 |        0 |   117 420 |
| ice-hockey  |     28 887 |        0 |         0 |
| tennis      |    229 128 |        0 |         0 |

→ **Aucune ligne** de tout le dataset n'a `odds_over` + `over_threshold` renseignés.
→ Seul **football** dispose de BTTS (53 % des lignes foot).

Le backtest "extended" se réduit donc à : **1×2 + BTTS (foot only)**.

---

## Calibration magic cotes

Filtre identique à `magic_cotes_smart.json` : **n ≥ 50** ET **EV ≥ 0**.

**Magic cotes par sport×bucket×marché :**

| Sport       |  1×2 |  over | under | btts_y | btts_n |
| ----------- | ---: | ----: | ----: | -----: | -----: |
| football    |  859 |   0   |   0   |    391 |     58 |
| basketball  |  333 |   0   |   0   |      0 |      0 |
| ice-hockey  |  116 |   0   |   0   |      0 |      0 |
| baseball    |   55 |   0   |   0   |      0 |      0 |
| tennis      |  141 |   0   |   0   |      0 |      0 |

Fichier sauvegardé : `/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_extended.json`

NB : la version filtrée backtestée est dans `/tmp/magic_cotes_extended_filt.json`. La version brute (n≥5, sans filtre EV) est dans `/tmp/magic_cotes_extended.json` (≈38 k entrées).

---

## Backtest Multi_full — 5 semestres

Composition : 6 safe (foot+basket+tennis+hockey, 2 jambes) + 2 EV3j (foot+basket) + 1 EV4j multi + 1 EV5j multi. Stake = 10 €/combo. Dédup max1. Whitelist Winamax FR.

3 variantes testées :
- **STANDARD** : magic = `magic_cotes_smart.json` officiel (1×2 only) + extract 1×2.
- **EXT-1x2only** : magic = nouveau magic étendu (1×2 only) + extract 1×2 (contrôle : isole l'effet du nouveau calibrage).
- **EXT+BTTS** : magic = magic étendu complet + extract 1×2 + BTTS.

| Semestre   | Variant     |     PnL | Days | Green% | Streak |  MaxDD | Combos |
| ---------- | ----------- | ------: | ---: | -----: | -----: | -----: | -----: |
| S1 2024H1  | STANDARD    |  +7 685 |  182 |    52% |      6 |   −308 |    949 |
| S1 2024H1  | EXT-1x2only |  +8 561 |  182 |    51% |      6 |   −315 |  1 048 |
| S1 2024H1  | EXT+BTTS    | +10 276 |  182 |    54% |      8 |   −399 |  1 082 |
| S2 2024H2  | STANDARD    |  +4 288 |  183 |    50% |      7 |   −165 |    934 |
| S2 2024H2  | EXT-1x2only |  +4 322 |  184 |    53% |      5 |   −180 |  1 035 |
| S2 2024H2  | EXT+BTTS    |  +8 770 |  184 |    51% |      8 |   −292 |  1 113 |
| S3 2025H1  | STANDARD    |  +8 057 |  181 |    59% |      5 |   −262 |  1 004 |
| S3 2025H1  | EXT-1x2only |  +7 551 |  181 |    57% |      5 |   −232 |  1 125 |
| S3 2025H1  | EXT+BTTS    |  +7 363 |  181 |    54% |      6 |   −497 |  1 182 |
| S4 2025H2  | STANDARD    |  +6 992 |  184 |    53% |      7 |   −322 |    950 |
| S4 2025H2  | EXT-1x2only |  +7 224 |  184 |    53% |      7 |   −308 |  1 066 |
| S4 2025H2  | EXT+BTTS    |  +8 124 |  184 |    57% |      6 |   −374 |  1 120 |
| S5 2026H1  | STANDARD    |  +4 868 |  121 |    58% |      6 |   −145 |    742 |
| S5 2026H1  | EXT-1x2only |  +5 421 |  121 |    62% |      5 |   −181 |    839 |
| S5 2026H1  | EXT+BTTS    |  +5 132 |  121 |    62% |      8 |   −273 |    862 |

### Totaux 5 semestres

| Variant     |     PnL | Combos |   ROI | Max streak | Green% | Worst DD |
| ----------- | ------: | -----: | ----: | ---------: | -----: | -------: |
| STANDARD    | +31 889 |  4 579 | 69.6% |          7 |    54% |     −322 |
| EXT-1x2only | +33 079 |  5 113 | 64.7% |          7 |    55% |     −315 |
| EXT+BTTS    | +39 665 |  5 359 | 74.0% |        **8** |    55% |     **−497** |

### Statistiques par marché (EXT+BTTS, total 5 semestres)

Picks générés (avant combo-building) :
- 1×2 (Home/Away/Draw) : ≈ 263 k (75 % du total)
- BTTS Oui : ≈ 86 k (24 %)
- BTTS Non : ≈ 8 k (2 %)
- Over / Under : 0 (pas de données)

Le marché **BTTS dominé par BTTS-Oui** (391 magic cotes vs 58 pour BTTS-Non) : BTTS-Non n'a presque pas de signal exploitable.

---

## Verdict : **MITIGÉ — pas de bénéfice net en risk/reward**

**Pour :**
- PnL absolu : +24 % vs standard (+39 665 € vs +31 889 €) sur 5 semestres.
- ROI/combo : 74 % vs 70 % (+4 pts).
- Volume combos : +17 % (5 359 vs 4 579) → un peu plus de signaux.

**Contre :**
- Série rouge max : **8 jours** vs 7 (+1 jour, dégrade la régularité).
- Worst DD : **−497 €** vs −322 € (+54 % de drawdown intra-semestre).
- Pas d'Over/Under disponible → dataset doit être ré-scrapé pour ces marchés.
- BTTS-Non quasi inutile (58 magic cotes seulement).

**Effet "EXT-1x2only" (nouveau calibrage 1×2 seul, sans BTTS) :**
- +1 190 € PnL vs STANDARD (gain marginal du recalibrage)
- streak identique (7), DD comparable
- → Le recalibrage 1×2 sur dataset complet n'apporte presque rien. Le gain de l'EXT+BTTS vient quasi-uniquement de BTTS, mais avec **plus de variance**.

### Recommandation

1. **Ne pas merger BTTS dans Multi_full standard** : le gain PnL ne compense pas le worst-case (DD -54 %, +1 j streak rouge). Un betteur conservateur préfère −322 € de DD à −497 €.
2. **Tester un preset dédié "Multi_full_BTTS"** : isole le risque, permet split-allocation BR (ex: 70 % BR sur Multi_full standard, 30 % sur variante BTTS pour upside).
3. **Re-scraper Over/Under avant de relancer un test étendu** : sans données O/U, on ne peut pas valider l'hypothèse complète.
4. **BTTS-Non quasi mort** : ne pas l'inclure dans une future stratégie (n trop faible).

---

## Comment utiliser le magic_cotes_extended

```python
import json
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_extended.json") as f:
    magic = json.load(f)

# Structure : magic[sport][bucket][market][cote_str] = {wr, n, ev}
# market ∈ {"1x2", "over", "under", "btts_y", "btts_n"}

# Pour utiliser comme remplaçant de magic_cotes_smart.json (1×2 seul) :
magic_1x2 = {"_smart": True}
for sport, buckets in magic.items():
    if sport.startswith("_"): continue
    magic_1x2[sport] = {}
    for bucket, markets in buckets.items():
        if "1x2" in markets:
            magic_1x2[sport][bucket] = markets["1x2"]
```

L'`extract_picks` actuel de `morning_live.py` peut consommer la version étendue avec une légère modification : détecter si `bucket_data` a une clé `1x2` (extended) ou pas (legacy), puis itérer sur les sous-marchés disponibles.

---

## Fichiers générés

- `/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_extended.json` — magic cotes 1×2 + over + under + btts_y + btts_n par sport×bucket (n ≥ 5, brut).
- `/tmp/magic_cotes_extended_filt.json` — version filtrée n ≥ 50 ET EV ≥ 0 (utilisée pour le backtest).
- `/tmp/results_v2.json` — résultats détaillés par semestre.
