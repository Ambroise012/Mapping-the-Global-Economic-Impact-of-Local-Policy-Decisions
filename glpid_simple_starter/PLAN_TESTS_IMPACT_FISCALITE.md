# Plan de tests — fiscalité locale et effets économiques

## Objectif

Ce document recense les cas déjà essayés et les prochains tests pertinents pour étudier si une réforme fiscale a été suivie d’un changement mesurable chez les entreprises concernées. Il sert de plan de recherche, pas de preuve que les réformes ont causé les mouvements observés.

Les tests boursiers disponibles dans le projet comparent les rendements des sociétés candidates à un indice de marché dans une fenêtre autour d’une date. Ils sont descriptifs. Une conclusion causale exige des entreprises traitées et témoins comparables, une exposition fiscale mesurée avant la réforme, des dates d’événement fiables et des tests de robustesse.

## Cas déjà chargés et testés

Les CAR moyens ci-dessous sont les moyennes arithmétiques des CAR individuels calculés par `scripts/event_study.py`. Les fenêtres sont actuellement définies en **jours calendaires** ; le nombre de séances est celui effectivement observé. Les résultats ne sont pas des tests de significativité.

| Lieu et politique | Événement testé | Fenêtre | Séances | CAR moyen observé | Réserve principale |
|---|---|---:|---:|---:|---|
| États-Unis — TCJA, baisse du taux fédéral | Signature, 22/12/2017 | ±1 j | 2 | −0,49 % | Date enregistrée comme adoption, pas annonce initiale ; seulement 5 sociétés candidates |
| États-Unis — TCJA | Signature | ±5 j | 7 | −1,31 % | Exposition et groupe témoin non mesurés |
| États-Unis — TCJA | Signature | ±10 j | 13 | −1,90 % | Fenêtre longue, autres nouvelles possibles |
| États-Unis — TCJA | Entrée en vigueur, 01/01/2018 | ±5 j | 7 | +0,80 % | Jour férié ; l’information était déjà connue |
| Royaume-Uni — taux principal de corporation tax | Annonce enregistrée, 03/03/2021 | ±1 j | 3 | +0,50 % | Coïncide avec le budget ; annonce antérieure à l’entrée en vigueur |
| Royaume-Uni | Annonce enregistrée | ±5 j | 7 | +2,71 % | CAR très différent selon la société |
| Royaume-Uni | Entrée en vigueur, 01/04/2023 | ±5 j | 9 | +2,44 % | Entrée en vigueur un samedi ; réforme anticipée |
| Irlande — mise en œuvre de Pillar Two | Adoption, 18/12/2023 | ±5 j | 8 | −3,34 % | Applicabilité aux sociétés candidates non établie |
| Irlande — Pillar Two | Entrée en vigueur, 31/12/2023 | ±5 j | 7 | +1,60 % | Date non cotée et règle déjà connue |
| Pennsylvanie — baisse progressive du taux d’impôt sur les sociétés | Adoption, 08/07/2022 | ±5 j | 7 | −1,25 % | Siège dans l’État ne mesure pas les bénéfices répartis en Pennsylvanie |
| Pennsylvanie | Première baisse appliquée, 01/01/2023 | ±5 j | 8 | +2,09 % | Date anticipée ; 5 candidates seulement |
| État de New York — surtaxe temporaire | Adoption, 19/04/2021 | ±5 j | 8 | +1,66 % | Seuil d’assujettissement et activité attribuable à NY non vérifiés |
| État de New York | Date d’effet inscrite, 01/01/2021 | ±5 j | 7 | +2,93 % | Effet rétroactif : date économique d’annonce différente |
| France — baisse progressive du taux normal d’IS | Adoption, 30/12/2017 | ±5 j | 6 | −0,78 % | Le calendrier de baisse était progressif ; 2017 n’est pas l’unique nouvelle |
| France — taux normal à 25 % | Entrée en vigueur, 01/01/2022 | ±5 j | 9 | +0,31 % | Étape annoncée plusieurs années auparavant |
| France — taux normal à 25 % | Entrée en vigueur | ±20 j | 30 | +0,80 % | Fenêtre trop longue pour isoler une réaction ponctuelle |

Ces chiffres sont des diagnostics exploratoires issus des cours téléchargés. Ils ne signifient pas, par exemple, qu’une politique a fait monter ou baisser les actions de ce montant.

## Ordre de priorité recommandé

### 1. Priorité : étudier un indicateur économique local, pas uniquement le cours boursier

Pour une ville ou un État, les cours d’une entreprise cotée reflètent ses activités mondiales. Il est généralement plus informatif de tester, selon les données disponibles :

- emploi, salaires et créations d’établissements dans le territoire ;
- ouvertures, fermetures et investissements d’entreprises ;
- recettes fiscales, créations de sociétés ou permis d’activité ;
- indicateurs d’entreprises ventilés par juridiction, quand les rapports les publient.

Définir la variable mesurée, sa fréquence, sa géographie, la source et la période avant de choisir une réforme. Ne pas mélanger des chiffres locaux avec des comptes mondiaux consolidés.

### 2. États américains : Pennsylvanie et New York

Ces cas ont déjà une date de politique et des cours boursiers candidats. Pour les rendre réellement testables :

- trouver des sociétés témoins cotées comparables dont l’activité taxable est répartie dans d’autres États ;
- relever, dans des documents publiés avant la réforme, les ventes, bénéfices, impôts ou facteurs d’apportionnement par État ;
- mesurer l’exposition effective à la règle, et non utiliser uniquement l’adresse du siège ;
- pour New York, vérifier les seuils de revenu et la période fiscale de la surtaxe, ainsi que son application rétroactive ;
- pour la Pennsylvanie, traiter séparément l’adoption de 2022 et chacune des réductions annuelles de taux ; vérifier le calendrier dans le texte légal officiel.

Les titres actuellement téléchargés pour ces cas sont des candidates, pas des groupes traités validés. Le script DiD doit refuser de s’exécuter tant que les scores d’exposition documentés et les témoins ne sont pas renseignés.

### 3. France : réforme nationale de l’IS et extension à une région/ville

La baisse nationale du taux normal d’IS est un cas de référence, mais la date 2022 correspond à une étape annoncée auparavant et ne fournit pas une surprise nette isolée.

#### Pistes locales françaises

La **CFE (cotisation foncière des entreprises)** est une piste praticable à l’échelle des communes et intercommunalités : les taux locaux varient selon le territoire et l’année. Il ne s’agit pas d’un événement national unique. Construire plutôt un panel annuel de communes/EPCI qui ont connu une variation de taux substantielle et d’autres comparables qui n’en ont pas connu, puis vérifier ces changements dans les données annuelles officielles de fiscalité locale.

- **Période à examiner :** par exemple 2018–2024, à fixer après vérification de la disponibilité des séries de taux et de résultats économiques cohérents.
- **Unité de traitement :** établissement ou entreprise ayant un établissement professionnel dans l’EPCI fiscal concerné, avec une mesure de sa base ou de son exposition locale.
- **Résultats prioritaires :** emploi salarié local, nombre d’établissements, créations/cessations, masse salariale et, si disponible, investissement.
- **Comparaison :** EPCI voisins comparables, secteur et tendances antérieures similaires ; tenir compte des changements de périmètre intercommunal et de compétences fiscales.
- **Sources à vérifier :** [documentation officielle CFE](https://www.impots.gouv.fr/professionnel/cotisation-fonciere-des-entreprises-cfe) et jeux annuels DGFiP de taux locaux. Les délibérations et taux effectivement applicables doivent être archivés pour chaque territoire et chaque année.

Autre piste : les taux de taxe foncière sur les propriétés bâties peuvent affecter les entreprises propriétaires ou locataires indirectement. L’effet sur une entreprise locataire dépend toutefois du bail et de la répercussion de la taxe ; il faut documenter ce mécanisme plutôt que supposer que toute variation de taux lui est transmise.

Pour toute étude locale française, les pistes à examiner avant de sélectionner un cas sont donc :

- variation d’un taux local de taxe foncière sur les entreprises ou d’une contribution économique territoriale ;
- changement documenté de taux ou d’exonération dans une commune ou une intercommunalité ;
- différence d’exposition entre établissements d’une même entreprise situés dans plusieurs collectivités.

Ne pas sélectionner une ville simplement parce qu’elle est connue. Vérifier les délibérations officielles, la date de publication, les règles d’éligibilité, le périmètre de l’EPCI fiscal et la disponibilité d’un groupe témoin. Une taxe locale peut peser trop peu dans les résultats consolidés d’une société pour être détectable dans son cours.

### 4. Villes et comtés aux États-Unis

Un test municipal peut être utile si la règle est ciblée et si l’on dispose d’établissements localisés :

- taxe sur les recettes, taxes commerciales ou surtaxe locale ;
- modifications de zones d’exonération ou de crédits liés à l’implantation ;
- comparaison des établissements concernés avec ceux de la même entreprise hors de la ville.

Pour ces cas, privilégier les données d’établissement (emploi, salaires, ventes, permis, créations/fermetures) plutôt que le rendement de l’action. Ajouter les limites géographiques et une série temporelle couvrant plusieurs périodes avant et après la réforme.

### Variables cibles et sources pour une entreprise multinationale

L’unité pertinente est l’établissement, le salarié agrégé, le bail ou la filiale juridique locale, pas le groupe consolidé. Avant de choisir une politique, définir une variable mesurable, sa géographie, sa fréquence et une source documentée :

| Résultat local à privilégier | Mesures possibles | Sources à examiner | Limites à documenter |
|---|---|---|---|
| Recrutement et réallocation des postes | Offres ouvertes par site, métier et tranche de salaire ; créations, suppressions et transferts de postes entre sites | Lightcast (ex-Burning Glass), Revelio Labs, Indeed | Couverture et licences variables ; annonces dupliquées ou non représentatives des embauches effectives |
| Masse salariale et rémunérations | Effectifs, salaires bruts, bonus, entrées et sorties de personnel | DSN/DADS via CASD en France ; Census LBD/LEHD aux États-Unis | Accès soumis à autorisation et secret statistique ; privilégier les résultats agrégés et ne pas exporter de données personnelles |
| Immobilier et capital physique | Surface occupée, ouvertures/fermetures de sites, baux renouvelés/résilés, permis, investissements et retards de projets | CoStar, CBRE, registres de permis ; DVF en France pour les transactions immobilières | Bases commerciales sous licence ; DVF renseigne les transactions, pas l’occupation ni les loyers |
| Résultats de l’entité juridique locale | Chiffre d’affaires, résultat, EBITDA si publié, impôt payé par la filiale | INPI/Infogreffe, Companies House et registres nationaux | Comptes parfois abrégés, non comparables ou publiés avec retard ; distinguer filiale opérationnelle et société holding |
| Activité physique et prix localisés | Fréquentation de sites ; frais ou prix géolocalisés, frais de livraison et de service | Placer.ai, SafeGraph ; tarifs publics et données de transaction autorisées | Données de mobilité souvent sous licence et sujettes à biais de couverture ; isoler le pass-through des autres changements de prix |

Le schéma `company_indicators` permet de consigner des mesures documentées avec période, portée géographique et source, mais le projet ne collecte pas automatiquement ces bases. Vérifier leurs licences, leurs définitions et la disponibilité d’identifiants stables de site. Une valeur mondiale consolidée ne doit pas servir de substitut à un résultat local.

### Plans causaux intra-entreprise et seuils

Le script `scripts/local_causal_designs.py` fournit trois estimateurs exploratoires pour des CSV préparés à partir de données autorisées :

1. **Sites d’une même firme (`within-firm`)** : compare les sites traités et témoins au sein de chaque firme et absorbe les chocs propres à la firme et à chaque période avec des effets fixes firme × période. Le CSV doit contenir `firm_id,location_id,period_start,treated,value`. Chaque firme doit avoir un site de chaque statut et un panel équilibré.
2. **Exposition continue (`continuous-did`)** : estime l’interaction entre une part d’exposition locale mesurée avant la réforme et la période post. Le CSV doit contenir `company_id,period_start,exposure,value`, avec `exposure` dans [0,1] et constant pour chaque entreprise. Le coefficient représente le changement d’issue associé à une hausse de l’exposition de 0 à 1 ; une hausse de 10 points correspond à un dixième de ce coefficient.
3. **RDD sharp (`rdd`)** : estime le saut local de résultat au seuil légal à partir de `running,value`, où `running` est la variable d’assignation (par exemple la rémunération) et `--cutoff` le seuil vérifié. La régression est locale, linéaire et pondérée par un noyau triangulaire. Le minimum par défaut de 20 observations de chaque côté est un garde-fou logiciel, pas une justification de puissance statistique ni une preuve de validité. Le script ne couvre pas une RDD fuzzy lorsque le franchissement du seuil ne détermine pas directement le traitement.

Exemples PowerShell (adapter les chemins, dates, seuils et unités aux données vérifiées) :

```powershell
python scripts/local_causal_designs.py --design within-firm --input data\local_cases\policy\within_firm.csv --post-date 2021-01-01
python scripts/local_causal_designs.py --design continuous-did --input data\local_cases\policy\exposure_panel.csv --post-date 2021-01-01
python scripts/local_causal_designs.py --design rdd --input data\local_cases\policy\threshold.csv --cutoff 150000 --bandwidth 30000
```

Le RDD n’est pertinent que si le texte crée une assignation ou une intensité de traitement discontinue au seuil. Vérifier le seuil effectif, l’éligibilité de l’employeur, les possibilités de manipulation ou de tri autour du seuil, la densité et les covariables, et rapporter plusieurs bandes passantes. Les erreurs-types clusterisées dans les deux DiD sont fragiles lorsque le nombre de firmes ou de sites est faible. Ces scripts n’importent ni ne téléchargent les CSV et leurs résultats restent descriptifs sans hypothèses et tests de robustesse crédibles.

#### Cas locaux concrets à prioriser

| Priorité | Juridiction et mesure candidate | Date(s) à tester | Population directement exposée | Résultat local à privilégier | Points de vigilance |
|---|---|---|---|---|---|
| 1 | **Seattle, Washington — JumpStart Payroll Expense Tax** | Adoption en 2020 ; début d’application le 01/01/2021 | Employeurs dont la masse salariale et les rémunérations versées pour le travail à Seattle répondent aux seuils légaux de l’année | Emploi, rémunération, embauches et établissements à Seattle | La pandémie et les restrictions sanitaires coïncident avec l’entrée en vigueur. Utiliser les seuils, exemptions et tranches exacts de chaque année ; ne pas classer toutes les entreprises de Seattle comme traitées. Source de départ : [Seattle Finance — JumpStart Payroll Expense Tax](https://www.seattle.gov/finance/business-taxes-and-licenses/seattle-taxes/jumpstart-payroll-expense-tax). |
| 2 | **San Francisco, Californie — Proposition C, surtaxe locale sur les recettes brutes des grandes entreprises** | Vote du 06/11/2018 ; première année fiscale à examiner : 2019 | Entreprises dépassant les seuils de recettes brutes applicables et réalisant des activités imposables à San Francisco | Emploi local, ouvertures/fermetures d’établissements, recettes et composition sectorielle | Vérifier les catégories de recettes, seuils, contentieux et calendrier réel de perception. Comparer à des entreprises exposées différemment et à des villes témoins ; contrôler les autres mesures locales. Source de départ : [San Francisco Treasurer & Tax Collector — Gross Receipts Tax](https://www.sf.gov/reports/november-2024/understanding-gross-receipts-tax). |
| 3 | **Communes/EPCI français — variation annuelle de taux de CFE** | Panel possible 2018–2024 ; dates exactes à tirer des taux et délibérations annuels | Établissements professionnels localisés dans l’EPCI qui fixe ou perçoit le taux considéré | Emploi/établissements par secteur, créations d’entreprises et masse salariale | La CFE relève souvent d’un périmètre intercommunal, pas de la seule commune. Harmoniser fusions et changements de périmètre ; distinguer changement de taux et changement d’assiette. Source de départ : [impots.gouv.fr — CFE](https://www.impots.gouv.fr/professionnel/cotisation-fonciere-des-entreprises-cfe). |

**Meilleur premier test local : Seattle, mais sur l’emploi et les établissements, pas sur les cours d’actions.** La règle cible les entreprises selon leur masse salariale et la rémunération des salariés concernés dans la ville, ce qui permet de définir l’exposition plus précisément qu’avec l’adresse du siège. Il faudra néanmoins tenir compte du choc Covid, comparer Seattle à des villes similaires et vérifier les seuils légaux applicables année par année. Si les données par employeur ne sont pas accessibles, une étude sectorielle ou géographique agrégée peut être menée, mais elle sera moins précise.

Pour San Francisco et les cas français, les dates ci-dessus sont des **points de départ de recherche**, pas des événements déjà estimés dans la base. Avant de les ajouter comme résultats, archiver le texte adopté, confirmer les règles et dates d’effet auprès de la source officielle, et établir que les données économiques locales existent aux périodes nécessaires.

### 5. Événements nationaux déjà présents

Les cas Royaume-Uni, Irlande et États-Unis fédéral restent utiles comme exercices de pipeline et de comparaison entre annonce, adoption et entrée en vigueur. Ils ne sont pas prioritaires pour une affirmation causale tant que l’exposition et les témoins ne sont pas documentés. Pour Pillar Two, confirmer explicitement quelles sociétés atteignent les seuils légaux avant de les classer comme exposées.

## Protocole à appliquer à chaque nouveau cas

1. **Valider le texte officiel** : autorité, URL, version adoptée, date de publication et dispositions applicables.
2. **Distinguer les dates** : annonce publique initiale, adoption, entrée en vigueur, premières déclarations ou premiers paiements. Une date d’effet rétroactive n’est pas forcément la date de réaction du marché.
3. **Définir le mécanisme et les unités exposées** : établissement, part de chiffre d’affaires, masse salariale, bénéfices imposables ou impôt versé dans la juridiction.
4. **Choisir la variable de résultat avant le test** : rendement ajusté, emploi, salaires, investissements, ouvertures/fermetures ou recettes publiques.
5. **Construire le groupe témoin avant d’observer les résultats postérieurs** : mêmes secteurs, tailles et tendances préalables, mais exposition moindre ou absence de la règle.
6. **Préenregistrer les fenêtres** : analyse de marché en séances de bourse, par exemple [-1,+1], [-3,+3] et [-5,+5] séances ; pour des résultats économiques trimestriels/annuels, choisir des périodes adaptées à leur fréquence.
7. **Contrôler les chocs concomitants** : budget, pandémie, taux d’intérêt, prix de l’énergie, résultats financiers, autres réformes ou actualités de l’entreprise.
8. **Tester la robustesse** : fenêtres alternatives raisonnables, dates placebo, secteurs/témoins alternatifs, définition alternative de l’exposition, résultats pré-tendance.
9. **Rapporter les limites** : taille d’échantillon, données manquantes, significativité, intervalle de confiance, couverture géographique et conditions d’accès/réutilisation.

## Conditions minimales pour la comparaison DiD actuelle

Le script `scripts/causal_event_study.py` exige :

- au moins 3 entreprises traitées avec `company_exposures.exposure_score >= 0.5` ;
- au moins 3 témoins avec `exposure_score <= 0.1` ;
- `source_id` et `source_page` attestant chaque score à partir d’une donnée antérieure à la réforme ;
- des secteurs renseignés et communs aux deux groupes ;
- suffisamment de séances de marché pour les 60 séances préalables, la fenêtre événementielle et le placebo.

Pour une réforme d’État ou de ville, rattacher également les entreprises témoins au territoire de la réforme étudiée, tout en documentant que leur exposition à cette règle locale est faible. Ne pas utiliser les seuils de score comme substitut à une justification empirique : ils sont des critères techniques de classement, pas des seuils universels.

## Commandes de reproduction des tests boursiers déjà configurés

Depuis `glpid_simple_starter` :

```powershell
# États-Unis fédéral
python scripts/fetch_event_data.py --case us
python scripts/event_study.py --policy-id policy-us-tcja-corporate-rate --event-column adoption_date --window-days 5 --index-name "^GSPC"

# Pennsylvanie
python scripts/fetch_event_data.py --case pa
python scripts/event_study.py --policy-id policy-pa-corporate-rate-2023 --event-column adoption_date --window-days 5 --index-name "^GSPC"
python scripts/event_study.py --policy-id policy-pa-corporate-rate-2023 --event-column effective_date --window-days 5 --index-name "^GSPC"

# État de New York
python scripts/fetch_event_data.py --case ny
python scripts/event_study.py --policy-id policy-ny-corporate-surcharge-2021 --event-column adoption_date --window-days 5 --index-name "^GSPC"
python scripts/event_study.py --policy-id policy-ny-corporate-surcharge-2021 --event-column effective_date --window-days 5 --index-name "^GSPC"

# France
python scripts/fetch_event_data.py --case fr
python scripts/event_study.py --policy-id policy-fr-corporate-rate-25-2022 --event-column adoption_date --window-days 5 --index-name "^FCHI"
python scripts/event_study.py --policy-id policy-fr-corporate-rate-25-2022 --event-column effective_date --window-days 5 --index-name "^FCHI"
```

Les commandes rechargent les cours pour la période par défaut de chaque cas ; une connexion Internet est nécessaire. Les conditions du fournisseur de données s’appliquent.

## Commandes pour tester des cas locaux (États, villes et EPCI)

Les commandes ci-dessous sont à lancer dans PowerShell depuis `glpid_simple_starter`, avec l’environnement Python du projet activé et la base PostgreSQL configurée dans `.env`. Les cas Pennsylvanie (`pa`) et État de New York (`ny`) sont déjà pris en charge par le téléchargeur. **Seattle, San Francisco et les variations de CFE ne sont pas des cas préchargés** : pour eux, les commandes d’analyse ne fonctionneront qu’après avoir collecté et importé les données décrites plus bas. Ne pas lancer `fetch_event_data.py --case seattle` ou `--case sf` : ces options n’existent pas.

### États américains déjà configurés : Pennsylvanie et New York

Recharger les prix sur une période assez large pour couvrir les séances préalables, la fenêtre événementielle et les tests placebo, puis comparer plusieurs fenêtres descriptives :

```powershell
# Pennsylvanie — Act 53 de 2022
python scripts/fetch_event_data.py --case pa --start-date 2022-04-01 --end-date 2023-05-01
python scripts/event_study.py --policy-id policy-pa-corporate-rate-2023 --event-column adoption_date --window-days 1 --index-name "^GSPC"
python scripts/event_study.py --policy-id policy-pa-corporate-rate-2023 --event-column adoption_date --window-days 5 --index-name "^GSPC"
python scripts/event_study.py --policy-id policy-pa-corporate-rate-2023 --event-column effective_date --window-days 5 --index-name "^GSPC"
python scripts/event_study.py --policy-id policy-pa-corporate-rate-2023 --event-column effective_date --window-days 10 --index-name "^GSPC"

# État de New York — surtaxe temporaire de 2021
python scripts/fetch_event_data.py --case ny --start-date 2020-08-01 --end-date 2021-10-01
python scripts/event_study.py --policy-id policy-ny-corporate-surcharge-2021 --event-column adoption_date --window-days 1 --index-name "^GSPC"
python scripts/event_study.py --policy-id policy-ny-corporate-surcharge-2021 --event-column adoption_date --window-days 5 --index-name "^GSPC"
python scripts/event_study.py --policy-id policy-ny-corporate-surcharge-2021 --event-column effective_date --window-days 5 --index-name "^GSPC"
python scripts/event_study.py --policy-id policy-ny-corporate-surcharge-2021 --event-column effective_date --window-days 10 --index-name "^GSPC"
```

Ces commandes mesurent seulement des CAR descriptifs pour des entreprises candidates liées à l’État par leur siège. Elles ne prouvent pas que ces sociétés sont effectivement exposées à la règle. Pour tenter la comparaison traité/témoin après avoir ajouté au moins trois entreprises traitées et trois témoins admissibles, avec secteurs, scores d’exposition et sources vérifiées :

```powershell
python scripts/causal_event_study.py --policy-id policy-pa-corporate-rate-2023 --event-column adoption_date --index-name "^GSPC" --window-sessions 5 --pre-sessions 60
python scripts/causal_event_study.py --policy-id policy-pa-corporate-rate-2023 --event-column effective_date --index-name "^GSPC" --window-sessions 5 --pre-sessions 60
python scripts/causal_event_study.py --policy-id policy-ny-corporate-surcharge-2021 --event-column adoption_date --index-name "^GSPC" --window-sessions 5 --pre-sessions 60
```

Les sociétés chargées automatiquement ont un score d’exposition vide et ne constituent pas de groupes traité/témoin. Dans cet état, la DiD doit refuser l’estimation ; ne pas remplacer les scores manquants par des valeurs supposées.

### Villes américaines : Seattle et San Francisco

Pour **Seattle**, une analyse exploratoire de l’emploi est désormais disponible avec les données trimestrielles officielles QCEW du Bureau of Labor Statistics. Le niveau public est le **comté**, pas la ville : King County sert donc de proxy imparfait de Seattle. Le script télécharge et enregistre directement les séries de King County et de cinq comtés témoins dans `territory_indicators` ; il ne faut pas remplir ni importer les CSV boursiers vides de Seattle pour lancer cette analyse.

Depuis PowerShell, dans `glpid_simple_starter`, avec `.env` et le schéma appliqué :

```powershell
# Télécharge l’emploi privé et le salaire hebdomadaire moyen, tous secteurs et secteurs détaillés, 2015–2025.
python scripts/fetch_qcew_local_panel.py --start-year 2015 --end-year 2025

# Estimation avec adoption en 2020-Q3 comme début de période post-réforme.
python scripts/local_employment_did.py --indicator employment --post-quarter 2020-Q3
python scripts/local_employment_did.py --indicator weekly-wage --post-quarter 2020-Q3

# Variante avec entrée en application en 2021-Q1.
python scripts/local_employment_did.py --indicator employment --post-quarter 2021-Q1 --adoption-quarter 2020-Q3
python scripts/local_employment_did.py --indicator weekly-wage --post-quarter 2021-Q1 --adoption-quarter 2020-Q3
```

Le téléchargement peut être relancé : les enregistrements sont mis à jour dans PostgreSQL. Il inclut le total privé et les secteurs biens/services, information, finance, services professionnels, gestion de sociétés, services administratifs, santé, arts/loisirs et hébergement/restauration (codes d’industrie QCEW). Pour ce test, l’estimation utilise les témoins Clark, Spokane, Thurston, Whatcom et Yakima. Les dates 2020-Q3 (adoption) et 2021-Q1 (application) sont deux spécifications à comparer, pas deux expériences indépendantes.

La fiche JumpStart est également enregistrée dans `policy_changes`, avec l’ordonnance 126109 comme référence et les dates du 6 juillet 2020 et du 1er janvier 2021. Le texte officiel n’ayant pas pu être vérifié directement lors de cette collecte, ces dates et leur interprétation juridique restent à confirmer avant toute conclusion. QCEW ne publie pas certaines cellules sectorielles : trois trimestres du secteur information manquent dans le panel (six valeurs emploi/salaire) et ne sont pas imputés ; l’estimateur refuse un panel incomplet.

Pour une vérification placebo antérieure à la taxe, une fois la période 2015–2025 chargée, comparer une pseudo-date 2018-Q1 en ne gardant que la période pré-politique jusqu’à 2019-Q4 :

```powershell
python scripts/local_employment_did.py --indicator employment --post-quarter 2018-Q1 --adoption-quarter 2018-Q1 --start-quarter 2016-Q1 --end-quarter 2019-Q4
python scripts/local_employment_did.py --indicator employment-professional-scientific-technical --post-quarter 2018-Q1 --adoption-quarter 2018-Q1 --start-quarter 2016-Q1 --end-quarter 2019-Q4
python scripts/local_employment_did.py --indicator employment-accommodation-food-services --post-quarter 2018-Q1 --adoption-quarter 2018-Q1 --start-quarter 2016-Q1 --end-quarter 2019-Q4
```

Un effet placebo notable fragilise l’interprétation de l’estimation principale ; un placebo nul ne prouve pas la causalité.

**Résultats du dépistage par secteur (2015-Q1–2025-Q4, application définie en 2021-Q1, trimestres Q3/Q4 2020 exclus comme transition) :**

| Indicateur | Variation DiD estimée | IC 95 % | p-valeur | Pré-tendance | Lecture |
|---|---:|---:|---:|---:|---|
| Emploi privé, tous secteurs | −2,09 % | [−6,94 % ; +3,01 %] | 0,4156 | p=0,0806 | Pas d’effet discernable |
| Emploi, services professionnels/scientifiques/techniques | −6,40 % | [−13,70 % ; +1,53 %] | 0,1109 | p=0,3574 | Signal non concluant |
| Emploi, santé et assistance sociale | −5,62 % | [−9,01 % ; −2,11 %] | 0,0019 | p=0,5020 | Écart observé, mais secteur peu directement lié et choc Covid possible |
| Emploi, hébergement/restauration | −11,91 % | [−16,74 % ; −6,79 %] | <0,0001 | p=0,0188 | Pré-tendance incompatible ; Covid majeur |
| Salaire, services professionnels/scientifiques/techniques | +10,17 % | [+4,38 % ; +16,28 %] | 0,0004 | p=0,0073 | Pré-tendance incompatible |
| Emploi, gestion de sociétés | +112,21 % | [+64,66 % ; +173,48 %] | <0,0001 | p=0,7560 | **À exclure** : rupture des données King County en 2022, d’environ 30 000 à 90 000 emplois trimestriels moyens |

Les pseudo-dates 2018-Q1, testées sur 2016-Q1–2019-Q4 avant la politique, donnent +1,29 % pour l’emploi total (p=0,1137), +0,83 % pour les services professionnels (p=0,7662), et −0,31 % pour l’hébergement/restauration (p=0,7288). Ces placebos sont plutôt rassurants pour ces trois séries sur cette courte fenêtre, mais ne corrigent ni la géographie imparfaite ni les autres biais.

Il s’agit d’un dépistage exploratoire de nombreux secteurs, sans correction pour comparaisons multiples. Les erreurs-types sont regroupées sur six comtés seulement, les comtés témoins ne sont pas des villes appariées, et QCEW ne révèle pas les employeurs assujettis à la taxe. Aucun résultat de secteur ne permet actuellement d’attribuer un effet à JumpStart. La série « gestion de sociétés » doit rester exclue tant que la rupture 2022 n’est pas expliquée.

Test de sensibilité des témoins, en retirant Clark County : l’estimation d’emploi total devient −0,41 % (IC 95 % [−4,92 % ; +4,32 %], p=0,8628 ; pré-tendance p=0,0171) et celle des services professionnels −7,40 % (IC 95 % [−16,34 % ; +2,50 %], p=0,1380 ; pré-tendance p=0,7476). Les intervalles restent larges et aucun effet stable n’émerge.

### Données d’actualité GDELT : contexte, pas résultat économique

Le script `scripts/fetch_gdelt_context.py` tente de télécharger un décompte mensuel des articles correspondant à `Seattle AND (JumpStart OR "payroll expense tax")`, puis de le stocker comme indicateur contextuel. La série brute GDELT mesure l’attention médiatique et ne doit pas être interprétée comme l’intensité de la taxe ou comme un résultat économique. Lors de la collecte, l’API DOC a renvoyé `HTTP 429 Too Many Requests` après plusieurs essais, donc **aucun indicateur GDELT n’a été enregistré** dans la base. Quand le service autorise la requête, réessayer une seule fois après un délai ; ne pas boucler sur des erreurs 429.

```powershell
python scripts/fetch_gdelt_context.py --start-date 2019-01-01 --end-date 2022-12-31
```

Le tableau 2015–2025 ci-dessus remplace les estimations intermédiaires 2017–2025. Les résultats restent exploratoires : King County n’est qu’un proxy de Seattle, il y a six grappes, la pandémie perturbe la période, les secteurs testés créent un problème de comparaisons multiples et les données ne distinguent pas les employeurs assujettis.

Pour **San Francisco**, ni données d’exposition d’entreprise ni indicateurs locaux ne sont préchargés. Des CSV vides avec les en-têtes attendus sont fournis dans `data\local_cases\san_francisco\` ; ils n’importent aucune ligne tant qu’ils ne sont pas remplis. Il faut d’abord collecter des données documentées. Exemple d’import à exécuter uniquement après avoir ajouté des lignes valides :

```powershell
python scripts/import_csv.py data\local_cases\san_francisco\sources.csv sources
python scripts/import_csv.py data\local_cases\san_francisco\territories.csv territories
python scripts/import_csv.py data\local_cases\san_francisco\companies.csv companies
python scripts/import_csv.py data\local_cases\san_francisco\policy_changes.csv policy_changes
python scripts/import_csv.py data\local_cases\san_francisco\company_exposures.csv company_exposures
python scripts/import_csv.py data\local_cases\san_francisco\company_prices.csv company_prices
python scripts/import_csv.py data\local_cases\san_francisco\market_index_prices.csv market_index_prices
```

Les identifiants de réforme ci-dessous sont des exemples à utiliser uniquement si ces valeurs sont effectivement inscrites dans `policy_changes.csv`. Les mêmes `territory_id` doivent être utilisés pour la politique et ses expositions. L’import ne télécharge pas les cours ; il insère seulement les lignes contenues dans les fichiers. Avec les CSV vides fournis, aucune ligne n’est importée.

```powershell
# San Francisco — exemple si policy_id=policy-sf-proposition-c-2019 et index_name=^GSPC
python scripts/event_study.py --policy-id policy-sf-proposition-c-2019 --event-column adoption_date --window-days 5 --index-name "^GSPC"
python scripts/event_study.py --policy-id policy-sf-proposition-c-2019 --event-column effective_date --window-days 5 --index-name "^GSPC"
```

Ces tests boursiers restent peu informatifs pour une taxe municipale : le siège social ou la cotation ne mesurent pas l’activité imposable dans la ville. Avant une DiD, mesurer l’exposition locale réelle à partir des seuils légaux, de la masse salariale ou des recettes attribuables à la ville, puis ajouter des sociétés témoins comparables et faiblement exposées au même `territory_id`. Les dates de politique et d’application des exemples doivent aussi être vérifiées dans le texte adopté avant d’être importées.

### Communes et intercommunalités françaises : panel de taux de CFE

La CFE se prête mieux à un panel annuel d’établissements et de territoires qu’à une étude d’événement boursière ponctuelle. Les fichiers sous `data\local_cases\cfe\` ne sont pas fournis : il faut les créer et constituer des données annuelles validées (par exemple 2018–2024) avant tout import. Après cette collecte, importer les sources, territoires, réformes ou variations documentées, puis les indicateurs :

```powershell
# Les CSV sont à préparer : les taux de CFE, périmètres et indicateurs locaux ne sont pas préchargés.
python scripts/import_csv.py data\local_cases\cfe\sources.csv sources
python scripts/import_csv.py data\local_cases\cfe\territories.csv territories
python scripts/import_csv.py data\local_cases\cfe\policy_changes.csv policy_changes
python scripts/import_csv.py data\local_cases\cfe\territory_indicators.csv territory_indicators
python scripts/import_csv.py data\local_cases\cfe\company_indicators.csv company_indicators
```

`territory_indicators.csv` doit suivre les colonnes du chargeur `territory_indicators` dans `scripts/import_csv.py` (`territory_indicator_id`, `territory_id`, `indicator_code`, `period_start`, `period_end`, `value`, `unit`, `geographic_scope`, `source_id`, `source_page`, `notes`). `company_indicators.csv` doit suivre le gabarit correspondant dans `data\templates`. Les commandes d’import sont donc des commandes à exécuter après collecte et création des fichiers, et non une procédure immédiatement exécutable avec le contenu actuel du dépôt.

**Il n’existe pas encore de script qui estime une différence-en-différences sur ces indicateurs territoriaux annuels.** L’import les stocke dans PostgreSQL, mais `causal_event_study.py` n’analyse que des rendements boursiers quotidiens. Ne pas lancer ce dernier pour conclure sur l’effet de la CFE ; il faudra d’abord construire un panel documenté de territoires traités et témoins et un estimateur adapté à ces indicateurs. Harmoniser également les périmètres communaux/EPCI sur toute la période.

## Sources et intégrité des données

- Conserver les liens vers le texte de loi et les documents d’entreprise dans `sources`.
- Enregistrer dans `company_exposures` les scores, leur méthode, leur source et leur page.
- Ne jamais inventer un score d’exposition ou renseigner une valeur inconnue par zéro.
- Distinguer cours ajusté, devise, date de séance et ticker ; vérifier les symboles historiques et les événements d’entreprise.
- Les données historiques téléchargées via Yahoo Finance sont utilisées ici pour l’exploration ; vérifier les conditions d’accès, de licence et de redistribution avant tout autre usage.
- Une corrélation, un CAR ou une p-valeur isolée ne suffit jamais à conclure à la causalité.
