# Étude exploratoire — baisse de l’impôt sur les sociétés en Pennsylvanie

## Résumé

Cette étude teste si la baisse graduelle de l’impôt sur les sociétés de Pennsylvanie à partir de 2023 est associée à une évolution de l’emploi privé et du salaire hebdomadaire moyen plus favorable que dans six États voisins. Elle utilise des données QCEW agrégées par État, et non les comptes de sociétés ni les résultats mondiaux de multinationales.

| Résultat | Variation DiD estimée | IC 95 % clusterisé | p-valeur | Écart de tendance avant adoption (p) |
|---|---:|---:|---:|---:|
| Emploi privé moyen, tous secteurs | −0,34 % | [−2,27 % ; +1,63 %] | 0,7336 | 0,000329 par trimestre (0,4870) |
| Salaire hebdomadaire moyen | +0,22 % | [−0,98 % ; +1,44 %] | 0,7188 | 0,000323 par trimestre (0,4223) |

Les deux estimations sont proches de zéro, leurs intervalles couvrent zéro et les p-valeurs sont élevées. Ces résultats **ne montrent pas d’effet discernable** sur ces mesures agrégées. Ils ne démontrent ni que la réforme n’a eu aucun effet, ni qu’elle a causé les mouvements observés.

## Politique et données

- **Politique :** baisse graduelle du taux statutaire de l’impôt sur le revenu net des sociétés de Pennsylvanie, établie par l’Act 53 de 2022.
- **Adoption enregistrée :** 8 juillet 2022 ; **première baisse applicable :** 1er janvier 2023.
- **Taux statutaires enregistrés :** 9,99 % en 2022, 8,99 % en 2023, 8,49 % en 2024 et 7,99 % en 2025. Ces taux ne sont pas les taux effectifs payés par chaque entreprise.
- **Résultats :** emploi privé mensuel moyen trimestriel et salaire hebdomadaire moyen, QCEW, tous secteurs privés.
- **Période :** 2015-Q1 à 2025-Q4.
- **Territoire traité :** Pennsylvanie (`us-pa`).
- **Témoins :** Delaware, Maryland, New Jersey, New York, Ohio et Virginie-Occidentale.
- **Base :** 616 indicateurs QCEW (7 États × 44 trimestres × 2 résultats) et 4 observations annuelles du taux statutaire de Pennsylvanie. Les séries QCEW sont complètes pour les deux indicateurs et les sept États.

Sources enregistrées dans la base :

- [Bureau of Labor Statistics — QCEW](https://www.bls.gov/cew/) ; observations téléchargées depuis l’API QCEW trimestrielle au niveau des États.
- [Pennsylvania Act 53 of 2022 — texte officiel](https://www.legis.state.pa.us/WU01/LI/LI/US/PDF/2022/0/0053..PDF).

## Méthode et résultats

Le modèle utilise le logarithme du résultat, des effets fixes de territoire et de trimestre, et l’interaction entre Pennsylvanie et la période postérieure. Les trimestres 2022-Q3 et 2022-Q4 sont exclus comme période de transition entre l’adoption et la première baisse applicable. La période postérieure commence en 2023-Q1. Les erreurs-types sont regroupées par État.

Chaque modèle principal comporte 294 observations (7 territoires × 42 trimestres). L’effet relatif présenté est calculé à partir du coefficient logarithmique par `100 × (exp(coefficient) − 1)`.

| Résultat | Coefficient logarithmique | Variation relative | IC 95 % | p-valeur |
|---|---:|---:|---:|---:|
| Emploi privé moyen | −0,00340 | −0,34 % | [−2,27 % ; +1,63 %] | 0,7336 |
| Salaire hebdomadaire moyen | +0,00222 | +0,22 % | [−0,98 % ; +1,44 %] | 0,7188 |

Les estimations de tendance linéaire différentielle pré-adoption ne sont pas statistiquement discernables de zéro dans ces modèles. Ce constat est un diagnostic limité : il ne valide pas à lui seul l’hypothèse de tendances parallèles.

### Placebos antérieurs à la réforme

Le modèle a également été relancé avec une pseudo-date 2018-Q1 et uniquement les données 2015-Q1–2021-Q4, entièrement antérieures à l’adoption. Chaque estimation placebo comporte 196 observations (7 × 28).

| Résultat | Placebo estimé | IC 95 % clusterisé | p-valeur |
|---|---:|---:|---:|
| Emploi privé moyen | +0,51 % | [−0,54 % ; +1,56 %] | 0,3433 |
| Salaire hebdomadaire moyen | +0,25 % | [−0,79 % ; +1,29 %] | 0,6418 |

Les placebos ne détectent pas d’écart statistiquement significatif à cette pseudo-date, mais un placebo non significatif ne prouve pas l’identification causale.

## Limites d’interprétation

1. **Agrégation :** QCEW observe l’emploi et le salaire moyens de l’ensemble du secteur privé dans chaque État. Il ne repère ni les entreprises assujetties, ni leurs établissements, ni les recrutements, les transferts de postes ou les profits attribuables à la Pennsylvanie.
2. **Pas d’échelle mondiale :** ces résultats ne mesurent pas l’impact global d’une entreprise multinationale et ne permettent pas d’inférer une création ou une perte nette d’activité à l’échelle nationale ou mondiale.
3. **Témoins non validés comme contrefactuel :** les six États voisins ont des structures sectorielles et des politiques fiscales distinctes ; certains peuvent également avoir modifié leur fiscalité. Le modèle ne contrôle pas explicitement leurs changements de taux d’impôt.
4. **Peu de grappes :** les erreurs-types reposent sur seulement sept États. Les intervalles et tests asymptotiques peuvent être fragiles avec si peu de grappes.
5. **Autres chocs et biais :** conjoncture, composition sectorielle, politiques simultanées, migration interétatique et retombées vers les témoins peuvent influencer les résultats.
6. **Résultat moyen :** le salaire QCEW est un salaire hebdomadaire moyen agrégé, non une rémunération à poste ou salarié constant. Il peut varier du fait de la composition de l’emploi.

**Conclusion :** cette première analyse publique est reproductible et utile comme dépistage descriptif, mais elle ne permet pas de soutenir que la baisse d’impôt a causé une variation de l’emploi ou des salaires. Pour une identification plus solide, il faudrait mesurer l’exposition pré-réforme des entreprises à la Pennsylvanie, disposer de données établissement-entreprise et comparer des sites proches ou des entreprises multi-établissements, avec des témoins dont les politiques fiscales sont documentées.

## Commandes de reproduction (PowerShell)

Depuis la racine du dépôt :

```powershell
Set-Location "C:\Users\ambro\Desktop\Mapping-the-Global-Economic-Impact-of-Local-Policy-Decisions\glpid_simple_starter"
.\.venv\Scripts\Activate.ps1

# Tests du collecteur et des modèles locaux
python -m unittest tests.test_fetch_qcew_state_tax_panel tests.test_local_causal_designs tests.test_local_employment_did

# Recharger le panel QCEW et le calendrier de taux de Pennsylvanie dans PostgreSQL
python scripts\fetch_qcew_state_tax_panel.py --start-year 2015 --end-year 2025

# Estimations principales : première baisse effective en 2023-Q1
python scripts\local_employment_did.py --indicator employment --treated-id us-pa --control-ids us-de us-md us-nj us-ny us-oh us-wv --post-quarter 2023-Q1 --adoption-quarter 2022-Q3 --start-quarter 2015-Q1 --end-quarter 2025-Q4
python scripts\local_employment_did.py --indicator weekly-wage --treated-id us-pa --control-ids us-de us-md us-nj us-ny us-oh us-wv --post-quarter 2023-Q1 --adoption-quarter 2022-Q3 --start-quarter 2015-Q1 --end-quarter 2025-Q4

# Placebos pré-réforme (fenêtre entièrement antérieure à 2022)
python scripts\local_employment_did.py --indicator employment --treated-id us-pa --control-ids us-de us-md us-nj us-ny us-oh us-wv --post-quarter 2018-Q1 --adoption-quarter 2018-Q1 --start-quarter 2015-Q1 --end-quarter 2021-Q4
python scripts\local_employment_did.py --indicator weekly-wage --treated-id us-pa --control-ids us-de us-md us-nj us-ny us-oh us-wv --post-quarter 2018-Q1 --adoption-quarter 2018-Q1 --start-quarter 2015-Q1 --end-quarter 2021-Q4
```

Le collecteur effectue 308 requêtes QCEW (7 États × 44 trimestres), puis insère ou met à jour les observations. Il nécessite la configuration PostgreSQL existante dans `.env` ; ne pas publier les paramètres de connexion. Le modèle principal est exécuté automatiquement par les deux commandes ci-dessus, sans sauvegarde des sorties dans des fichiers.
