# Taxe sur les boissons de Philadelphia — étude et réplication

## Résumé

La taxe de Philadelphia sur les boissons sucrées est un cas où une réponse locale est observée dans les prix et les ventes au détail. La taxe de 1,5 cent par once est entrée en vigueur le 1er janvier 2017. Une étude publiée dans *JAMA Network Open* compare les magasins de Philadelphia à ceux de Baltimore et examine aussi les codes postaux de Pennsylvanie limitrophes.

L'étude rapporte une hausse du prix relatif des boissons taxées et une baisse des volumes vendus à Philadelphia. Les ventes rapportées dans les zones limitrophes ont augmenté en même temps : les achats transfrontaliers ont donc compensé une partie de la baisse observée dans la ville. C'est un résultat local sur le marché des boissons, pas une mesure de l'emploi, des investissements ou de l'impact macroéconomique mondial.

## Données et méthode de l'étude

- **Réforme :** taxe municipale sur la distribution de boissons sucrées, 1,5 cent par once, à compter du 1er janvier 2017.
- **Unité observée :** prix et volumes de ventes de boissons, par produit et type de magasin.
- **Échantillon :** 291 magasins de chaînes (54 supermarchés, 20 magasins généralistes et 217 pharmacies).
- **Comparaison :** Philadelphia contre Baltimore, complétée par une analyse de codes postaux de Pennsylvanie limitrophes de Philadelphia.
- **Méthode :** différence-en-différences, comparaison des résultats de 2016 à ceux de 2017.
- **Couverture :** les données commerciales de caisse couvrent environ 25 % des onces de boissons taxées vendues à Philadelphia. Les microdonnées IRI sous-jacentes ne sont pas librement accessibles et ne sont pas incluses dans ce dépôt.

## Résultats publiés

Les écarts de prix indiqués sont ceux rapportés par l'article entre Philadelphia et Baltimore :

| Type de magasin | Écart de prix publié | IC à 95 % | p |
|---|---:|---:|---:|
| Supermarchés | +0,65 cent/once | 0,60 à 0,69 | < 0,001 |
| Magasins généralistes | +0,87 cent/once | 0,72 à 1,02 | < 0,001 |
| Pharmacies | +1,56 cent/once | 1,50 à 1,62 | < 0,001 |

Estimations de différence-en-différences des ventes moyennes par période de quatre semaines :

| Type de magasin | Effet publié | IC à 95 % | p |
|---|---:|---:|---:|
| Supermarchés | −2,85 millions d'onces | −4,10 à −1,60 | < 0,001 |
| Magasins généralistes | −1,20 million d'onces | −2,04 à −0,36 | 0,001 |
| Pharmacies | −0,02 million d'onces | −0,03 à −0,01 | < 0,001 |

En valeurs descriptives, le volume total de boissons taxées rapporté à Philadelphia passe de 2,475 à 1,214 milliards d'onces (−51,0 %). Dans les codes postaux limitrophes étudiés, il passe de 713,1 millions à environ 1,021 milliard d'onces ; cette hausse compense 24,4 % de la baisse du volume de Philadelphia selon les auteurs. Ces totaux décrivent l'échantillon de détaillants utilisé par l'étude, pas un recensement de toutes les ventes.

## Interprétation et limites

Ce cas fournit une preuve empirique plus directement liée au mécanisme qu'une comparaison entre grandes entreprises : le prix local et les ventes locales évoluent autour de l'entrée en vigueur de la taxe, avec Baltimore comme comparaison et les achats transfrontaliers comme mécanisme de déplacement. Il ne prouve pas que toutes les différences observées sont causées par la taxe : la période analysée est courte, la couverture est partielle et l'échantillon se limite à des chaînes de magasins. L'article rapporte également que les tendances préalables ne sont pas toutes satisfaisantes sur l'ensemble de la période 2014–2015 ; il faut donc éviter de présenter l'estimation comme une réplication causale indépendante ou une preuve universelle.

Les valeurs détaillées sont conservées dans `territory_indicators`, avec le code source `source-philadelphia-beverage-tax-jama-2019`, les unités, périodes, intervalles de confiance et notes de provenance. Les estimations publiées sont séparées des valeurs annuelles de prix et de volumes. Elles ne doivent pas être réutilisées comme si elles étaient des observations brutes trimestrielles.

L'application les montre dans **Tester un effet causal** pour la taxe de Philadelphia, sous la rubrique **Résultats publiés**. Elle ne les recalcule pas. Les observations annuelles de 2016 et 2017 ne satisfont pas les exigences du modèle de panel trimestriel de l'application (au moins huit trimestres avant et après, résultats traités et témoins comparables) ; le sélecteur indique donc **résultat à charger** pour une nouvelle estimation.

## Sources

- Ville de Philadelphia, [Philadelphia Beverage Tax](https://www.phila.gov/services/payments-assistance-taxes/business-taxes/philadelphia-beverage-tax/) — champ et taux actuels.
- Roberto CA et al., *Association of a Beverage Tax on Sugar-Sweetened and Artificially Sweetened Beverages With Changes in Beverage Prices and Sales at Chain Retailers in a Large Urban Setting*, *JAMA Network Open*, 2019; DOI [10.1001/jama.2019.4249](https://doi.org/10.1001/jama.2019.4249), PMID [31087022](https://pubmed.ncbi.nlm.nih.gov/31087022/).

## Commandes de reproduction et vérification

Depuis `glpid_simple_starter`, avec PostgreSQL démarré, le schéma appliqué et `.env` configuré :

```powershell
.\.venv\Scripts\python.exe scripts\import_philadelphia_beverage_tax_case.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_import_philadelphia_beverage_tax_case.py"
psql -U postgres -d glpid -c "SELECT policy_id, title, adoption_date, effective_date FROM policy_changes WHERE policy_id = 'policy-philadelphia-beverage-tax-2017';"
psql -U postgres -d glpid -c "SELECT t.name, i.indicator_code, i.period_start, i.value, i.unit, i.notes FROM territory_indicators i JOIN territories t USING (territory_id) WHERE i.indicator_code LIKE 'pbt_published_did_%' ORDER BY i.indicator_code;"
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

L'import est idempotent. Il ajoute les chiffres publiés accessibles et leurs références ; il ne télécharge pas les microdonnées IRI et ne simule pas de données absentes.
