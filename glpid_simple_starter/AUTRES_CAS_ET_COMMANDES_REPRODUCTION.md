# Autres cas de fiscalité locale et commandes de reproduction

## Objet et statut

Cette note présente des cas empiriques supplémentaires de fiscalité infranationale et les commandes permettant d’adapter les méthodes du projet. Elle distingue :

- les résultats publiés, déjà estimés par les auteurs ;
- les analyses exploratoires QCEW de Seattle et de Pennsylvanie, exécutables avec la base du projet ;
- les réanalyses de nouveaux cas, qui nécessitent encore de collecter et préparer les données.

**Aucun fichier de données de réplication des études publiées ci-dessous n’est préinstallé.** L’étude QCEW de Pennsylvanie est une analyse agrégée distincte, et non une réplication des travaux sur les microdonnées du Census. Les cas Ontario, Pittsburgh et autres plans multi-États nécessitent encore de constituer des données avec les colonnes attendues. Ne pas inventer les expositions, les dates de réforme, les résultats ni les groupes témoins.

## Cas empiriques intéressants

| Cas | Résultat publié | Méthode / intérêt | Réserves et disponibilité |
|---|---|---|---|
| **Réformes de l’impôt foncier commercial en Ontario** | Michael Smart conclut à un effet positif mais **faible** sur l’emploi urbain et la productivité des entreprises. Le résumé consulté ne donne pas d’estimation chiffrée à reprendre. | Étudie les réformes provinciales des années 2000 qui ont réduit certains taux commerciaux municipaux et déplacé une partie de la charge vers les résidents. C’est le cas le plus proche d’une réforme de taxe sur les entreprises locales dans ces références. | Le calendrier de réforme doit être reconstruit municipalité par municipalité dans l’article et les documents officiels. Le document de recherche est disponible ; les données et le code de réplication n’ont pas été confirmés comme librement téléchargeables. [Smart, *The Reform of Business Property Tax in Ontario: An Evaluation* (2012), dépôt de l’Université de Toronto](https://hdl.handle.net/1807/81261). |
| **Impôt sur les sociétés des États américains et incidence locale** | L’estimation structurelle attribue environ **40 %** de l’incidence aux propriétaires d’entreprises, **30–35 %** aux travailleurs et **25–30 %** aux propriétaires fonciers. | Combine les variations des taux d’impôt sur les sociétés et des règles d’apportionnement avec un modèle d’équilibre spatial. Utile pour montrer que l’incidence peut se répartir au-delà de l’entreprise imposée. | Ce sont des parts d’incidence modélisées, pas des variations directes d’emploi de 40 % ni l’effet d’une seule réforme. [Suárez Serrato et Zidar, *Who Benefits from State Corporate Tax Cuts?*, AER 2016](https://www.aeaweb.org/articles?id=10.1257/aer.20141702). |
| **Taux d’impôt des États américains et réallocation des établissements** | Pour les C corporations, les auteurs rapportent des élasticités de court terme de **−0,4 pour l’emploi** et **−0,5 pour le nombre d’établissements** par rapport au taux d’impôt sur les sociétés ; environ la moitié de la réponse estimée passe par la réallocation entre États. | Microdonnées administratives du Census sur les entreprises multi-établissements : le résultat porte directement sur les choix de localisation et les emplois des sites. [Giroud et Rauh, *State Taxation and the Reallocation of Business Activity*, NBER WP 21534](https://www.nber.org/papers/w21534), publié dans le *Journal of Political Economy* ([DOI](https://doi.org/10.1086/701357)). | Les microdonnées de recensement ne sont pas un jeu ouvert ordinaire. Une analyse QCEW publique serait une étude agrégée distincte, pas une réplication. Une réallocation entre États n’implique pas une hausse équivalente de l’activité nationale ou mondiale. |
| **Pittsburgh — impôt foncier à taux différenciés sur terrains et bâtiments** | Étude historique des changements de construction et de l’activité urbaine associés à la taxation plus forte du terrain que des améliorations. **Ne pas citer un pourcentage causal** : les sources consultées ne fournissent pas un effet isolé suffisamment vérifié. | Cas d’une politique foncière urbaine conçue pour diminuer la pénalisation fiscale de la construction. Utile pour formuler des résultats à tester : permis, mises en chantier, investissements et valeurs foncières. | Étude de cas historique, sans estimation causale nette vérifiée ici ; plusieurs changements urbains coïncident. [Oates et Schwab, *The Impact of Urban Land Taxation: The Pittsburgh Experience*](https://doi.org/10.1086/ntj41789240) ; contexte sur la taxe à deux taux dans [Cohen et Coughlin, Federal Reserve Bank of St. Louis](https://doi.org/10.20955/r.87.359-374). |

### Ce qu’ils apprennent

Les résultats les plus directement liés aux décisions des entreprises sont ceux sur l’emploi, le nombre d’établissements et leur réallocation. L’incidence d’une réforme fiscale peut néanmoins se répartir entre propriétaires, salariés et propriétaires fonciers. Une hausse observée dans un territoire peut aussi être le déplacement d’activité d’un territoire voisin, plutôt qu’une création nette d’activité à l’échelle nationale. Il faut donc fixer l’échelle de l’effet recherché avant l’estimation.

## Commandes déjà exécutables dans ce dépôt : point de comparaison Seattle

Le projet a déjà les données trimestrielles QCEW 2015–2025 pour King County et cinq comtés témoins. King County reste un proxy imparfait de Seattle ; ces commandes n’identifient pas les employeurs qui paient effectivement JumpStart.

Depuis PowerShell :

```powershell
Set-Location "C:\Users\ambro\Desktop\Mapping-the-Global-Economic-Impact-of-Local-Policy-Decisions\glpid_simple_starter"
.\.venv\Scripts\Activate.ps1

# Facultatif si le panel 2015–2025 est déjà dans PostgreSQL :
python scripts\fetch_qcew_local_panel.py --start-year 2015 --end-year 2025

# Modèle principal : entrée en vigueur en 2021-Q1, transition depuis l’adoption exclue
python scripts\local_employment_did.py --indicator employment --post-quarter 2021-Q1 --adoption-quarter 2020-Q3
python scripts\local_employment_did.py --indicator weekly-wage --post-quarter 2021-Q1 --adoption-quarter 2020-Q3

# Variante de date, à comparer à la principale et non comme une expérience indépendante
python scripts\local_employment_did.py --indicator employment --post-quarter 2020-Q3
python scripts\local_employment_did.py --indicator weekly-wage --post-quarter 2020-Q3
```

Le résultat et les commandes supplémentaires de placebo et de sensibilité sont détaillés dans [l’étude JumpStart](./ETUDE_CAUSALE_JUMPSTART_SEATTLE_2026-10-31.md). L’emploi total n’y présente pas d’effet significatif discernable ; le salaire moyen montre une pré-tendance qui empêche de conclure à un effet causal.

## Tableau de bord de la base

Pour explorer les réformes, territoires, sources, indicateurs et entreprises dans une interface locale, installez les dépendances puis lancez Streamlit depuis `glpid_simple_starter` :

```powershell
python -m pip install -r requirements.txt
streamlit run dashboard.py
```

L'onglet « Sources et données » détaille les tables, indicateurs, unités, territoires et périodes liés à chaque source, et distingue les sources simplement référencées des sources utilisées par des données effectivement présentes. L'onglet « Tester un effet causal » ne propose que les réformes dont le territoire traité a un indicateur trimestriel QCEW avec au moins 8 périodes avant et 8 après la réforme. Les bornes de période sont initialisées automatiquement sur les périodes communes disponibles ; les témoins proposés sont préremplis quand une configuration connue existe. Le panel doit être complet pour tous les territoires sélectionnés. Si une réforme n'est pas proposée, les dates seules ne suffisent pas : il faut d'abord importer un indicateur de résultat sur une période adéquate et des territoires témoins compatibles. L'outil montre les sources des observations et affiche l'effet estimé, l'intervalle de confiance, la p-valeur et le diagnostic de pré-tendance ; il ne certifie pas les hypothèses causales. Les requêtes à PostgreSQL sont en lecture seule. Il n'affiche pas de carte car la base ne contient pas encore les géométries territoriales.

## Nouveau cas exécutable : baisse de l’impôt sur les sociétés en Pennsylvanie

Le dépôt contient maintenant un panel QCEW d’emploi privé et de salaire hebdomadaire moyen pour la Pennsylvanie et six États voisins (2015-Q1–2025-Q4). Le collecteur ajoute aussi la politique Act 53 de 2022 et le calendrier statutaire du taux de Pennsylvanie. Cette étude publique agrégée ne mesure pas l’activité d’une entreprise particulière et ne constitue pas une preuve d’impact mondial.

Depuis PowerShell, dans le même environnement virtuel que ci-dessus :

```powershell
# Facultatif : recharger/actualiser les 616 observations QCEW et le taux statutaire
python scripts\fetch_qcew_state_tax_panel.py --start-year 2015 --end-year 2025

# DiD principal : post à compter de la première baisse applicable en 2023-Q1
python scripts\local_employment_did.py --indicator employment --treated-id us-pa --control-ids us-de us-md us-nj us-ny us-oh us-wv --post-quarter 2023-Q1 --adoption-quarter 2022-Q3 --start-quarter 2015-Q1 --end-quarter 2025-Q4
python scripts\local_employment_did.py --indicator weekly-wage --treated-id us-pa --control-ids us-de us-md us-nj us-ny us-oh us-wv --post-quarter 2023-Q1 --adoption-quarter 2022-Q3 --start-quarter 2015-Q1 --end-quarter 2025-Q4

# Placebos antérieurs à la réforme
python scripts\local_employment_did.py --indicator employment --treated-id us-pa --control-ids us-de us-md us-nj us-ny us-oh us-wv --post-quarter 2018-Q1 --adoption-quarter 2018-Q1 --start-quarter 2015-Q1 --end-quarter 2021-Q4
python scripts\local_employment_did.py --indicator weekly-wage --treated-id us-pa --control-ids us-de us-md us-nj us-ny us-oh us-wv --post-quarter 2018-Q1 --adoption-quarter 2018-Q1 --start-quarter 2015-Q1 --end-quarter 2021-Q4
```

Les estimations principales sont −0,34 % pour l’emploi (IC 95 % [−2,27 % ; +1,63 %], p=0,7336) et +0,22 % pour le salaire hebdomadaire moyen (IC 95 % [−0,98 % ; +1,44 %], p=0,7188). Aucun effet n’est statistiquement discernable ; avec sept grappes et des États témoins dont la fiscalité peut également changer, l’identification causale reste fragile. Les détails, placebos, sources et limites figurent dans [l’étude QCEW de Pennsylvanie](./ETUDE_CAUSALE_PENNSYLVANIE_QCEW_2026-10-31.md).

## Reproduire les plans du projet sur de nouveaux cas

Le script `scripts/local_causal_designs.py` accepte des données CSV préparées. Les exemples ci-dessous sont des **gabarits de commandes** : les fichiers de données et dates doivent être remplacés par des données vérifiées. Ils ne fonctionnent pas en l’état avec les seuls fichiers actuels du dépôt.

### A. Ontario ou établissements multi-États : DiD intra-entreprise

Pour une entreprise ayant des sites comparables des deux côtés d’une réforme, préparer un panel équilibré avec une ligne par site et période :

```text
firm_id,location_id,period_start,treated,value
```

- `treated` vaut 1 pour un site soumis à la réforme et 0 pour le site témoin de la même firme ;
- `value` est une mesure cohérente au niveau du site (par exemple emploi ou masse salariale agrégée) ;
- `period_start` est au format `AAAA-MM-JJ` ;
- les firmes/sites, traitement et périodes doivent être sourcés ; ne pas choisir les témoins d’après les résultats post-réforme.

Commande, après création du CSV et validation de la date effective :

```powershell
$postDate = "AAAA-MM-JJ" # Remplacer par la première période réellement post-réforme documentée
python scripts\local_causal_designs.py --design within-firm --input data\replication\ontario_sites.csv --post-date $postDate
```

Le modèle comprend des effets fixes de site et firme × période afin d’absorber les chocs communs aux sites d’une firme. Cela ne corrige pas un déplacement de postes entre les sites traités et témoins : cette réallocation peut justement être un résultat, mais elle complique l’interprétation du changement global du groupe.

### B. Réformes fiscales de plusieurs États : DiD à exposition continue

Pour comparer des entreprises selon leur part d’activité exposée avant la réforme, préparer :

```text
company_id,period_start,exposure,value
```

`exposure` est une part sourcée comprise entre 0 et 1, calculée **avant** la réforme (par exemple part de l’emploi ou des établissements dans les juridictions concernées) et fixe sur l’ensemble du panel. `value` est la même mesure de résultat pour toutes les entreprises et périodes.

```powershell
$postDate = "AAAA-MM-JJ" # Remplacer par la date de traitement définie dans le protocole
python scripts\local_causal_designs.py --design continuous-did --input data\replication\state_tax_exposure.csv --post-date $postDate
```

Le coefficient correspond à l’écart associé à une variation d’exposition de 0 à 1. L’estimateur disponible ne comprend pas de contrôle sectoriel variable dans le temps ni un modèle spatial ; vérifier les tendances préalables et les retombées entre États séparément. Ne pas interpréter ce coefficient comme l’effet mondial d’une baisse d’impôt.

### C. Pittsburgh ou réforme foncière locale : RDD uniquement si un vrai seuil existe

Une taxe foncière à deux taux ne constitue pas automatiquement une régression sur discontinuité. Le RDD n’est pertinent que si une règle assigne le traitement de façon discontinue à un seuil vérifiable. Une fois ce seuil établi dans le texte légal et les données, préparer :

```text
running,value
```

`running` est la variable d’assignation (pas une variable arbitraire) et `value` le résultat. Puis lancer des bandes passantes alternatives documentées :

```powershell
python scripts\local_causal_designs.py --design rdd --input data\replication\local_tax_threshold.csv --cutoff <SEUIL_VERIFIE> --bandwidth <BANDE_PASSANTE>
```

Dans PowerShell, remplacer `<SEUIL_VERIFIE>` et `<BANDE_PASSANTE>` par des nombres avant exécution. Le script estime une RDD sharp locale linéaire pondérée ; il ne valide pas la manipulation, la densité, les covariables, la validité juridique du seuil ou une assignation fuzzy.

## Préparer une analyse territoriale publique supplémentaire

Les fichiers QCEW de l’outil de collecte existant sont codés pour King County et cinq comtés de Washington. Ils ne téléchargent pas automatiquement l’Ontario ou Pittsburgh. Pour une nouvelle géographie américaine, obtenir les séries du [BLS QCEW](https://www.bls.gov/cew/downloadable-data-files.htm), vérifier la couverture/suppression des cellules, puis les importer dans `territory_indicators` avec une source documentée. Le format accepté par `scripts/import_csv.py` pour ces données est :

```text
territory_indicator_id,territory_id,indicator_code,period_start,period_end,value,unit,geographic_scope,source_id,source_page,notes
```

Commande après préparation du CSV :

```powershell
python scripts\import_csv.py data\replication\qcew_new_territories.csv territory_indicators
```

Le script `scripts/local_employment_did.py` peut ensuite analyser des `territory_id` personnalisés via `--treated-id` et `--control-ids`, **si** tous les territoires ont le même panel complet pour un indicateur. Exemple de gabarit (remplacer les identifiants par les IDs effectivement importés et validés) :

```powershell
python scripts\local_employment_did.py --indicator employment --treated-id <ID_TRAITE> --control-ids <ID_TEMOIN_1> <ID_TEMOIN_2> <ID_TEMOIN_3> --post-quarter AAAA-Qn --adoption-quarter AAAA-Qn --start-quarter AAAA-Qn --end-quarter AAAA-Qn
```

La commande vérifie la complétude, mais ne valide ni le choix des témoins, ni les tendances parallèles, ni l’absence de chocs concomitants. Les erreurs-types sont fragiles avec peu de territoires.

## Limites d’accès et règles de conclusion

- Les études du Census utilisent des données administratives protégées ; leurs microdonnées ne doivent pas être récupérées ou exportées hors d’un accès autorisé.
- Un résultat publié peut être informatif sans être reproductible avec les fichiers ouverts du projet.
- Le QCEW mesure emploi et salaire moyen par territoire/secteur, pas les comptes de filiales ni l’exposition d’un employeur donné à la taxe.
- Une significativité statistique n’établit pas à elle seule une causalité ; une commande qui s’exécute ne valide pas les hypothèses du modèle.
- Rapporter les unités, périodes, géographies, sources, taille d’échantillon, intervalle de confiance, tendances préalables et placebos.

## Références

- Smart, M. (2012), [*The Reform of Business Property Tax in Ontario: An Evaluation*](https://hdl.handle.net/1807/81261).
- Suárez Serrato, J. C. et Zidar, O. (2016), [*Who Benefits from State Corporate Tax Cuts? A Local Labor Markets Approach with Heterogeneous Firms*](https://www.aeaweb.org/articles?id=10.1257/aer.20141702).
- Giroud, X. et Rauh, J. (2019), [*State Taxation and the Reallocation of Business Activity: Evidence from Establishment-Level Data*](https://www.nber.org/papers/w21534).
- Oates, W. E. et Schwab, R. M., [*The Impact of Urban Land Taxation: The Pittsburgh Experience*](https://doi.org/10.1086/ntj41789240).
- Cohen, J. P. et Coughlin, C. C., [*An Introduction to Two-Rate Taxation of Land and Buildings*](https://doi.org/10.20955/r.87.359-374).
