# Guide de la base GLPID : structure, contenu, sources et couverture

**État des lieux vérifié le 1er novembre 2026.** Ce document décrit la base PostgreSQL configurée dans `.env` à cette date. Les quantités ci-dessous sont un instantané : elles changent quand un collecteur est relancé ou que des données sont ajoutées.

## 1. En bref : ce que contient la base

| Élément | Lignes | À comprendre |
|---|---:|---|
| Territoires | 56 | Pays, États, villes, comtés, régions et géographies de comparaison. |
| Sources | 42 | Sources documentaires et jeux de données : certaines sont effectivement liées à des observations, d’autres sont seulement référencées dans le catalogue. |
| Changements de politique | 8 | Réformes fiscales documentées avec leurs dates et leur territoire. |
| Indicateurs territoriaux | 7 351 | Séries économiques, taux légaux, résultats publiés, ou volumes d’articles, associés à une période, une géographie et une source. |
| Entreprises | 29 | Entreprises candidates regroupées autour de plusieurs réformes ; ce n’est pas un échantillon de traitement validé. |
| Expositions d’entreprises | 29 | Une fiche d’exposition par entreprise, toutes de type « siège social » ; ces fiches ne prouvent pas qu’une entreprise est effectivement assujettie à une taxe donnée. |
| Indicateurs d’entreprises | 0 | Aucun chiffre d’affaires, bénéfice, salaire, effectif ou impôt local d’entreprise n’est chargé dans cette table. |
| Cours boursiers d’entreprises | 15 027 | Prix journaliers pour 29 entreprises, principalement des cours boursiers globaux, pas des résultats locaux. |
| Cours d’indices de marché | 3 046 | Observations journalières de quatre indices de référence. |

La taille PostgreSQL constatée est d’environ **25 Mo**. Les données sont donc un prototype de recherche structuré, pas un recensement exhaustif des entreprises, des ventes locales ou de toutes les réformes fiscales.

## 2. Comment le schéma est organisé

Le schéma principal est défini dans [`sql/001_schema.sql`](sql/001_schema.sql). Les relations essentielles sont :

```text
territories ──< policy_changes >── sources
     │
     ├──< territory_indicators >── sources
     │
     ├──< company_exposures >── companies
     │                             ├──< company_indicators >── sources
     │                             └──< company_prices >────── sources
     └── parent_territory_id         market_index_prices ───── sources
```

Les principales tables :

| Table | Rôle et champs importants |
|---|---|
| `territories` | Référentiel géographique : identifiant, nom, type, pays, territoire parent et description. Les frontières géométriques ne sont pas stockées. |
| `sources` | Catalogue de provenance : éditeur, titre, catégorie, URL, date de consultation et notes sur la couverture, l’accès ou les limites. Une source inscrite ici n’implique pas que ses données ont été téléchargées. |
| `policy_changes` | Réformes : territoire, dates d’annonce, d’adoption, d’entrée en vigueur et de fin, statut, secteur concerné, mécanisme attendu et source légale. |
| `territory_indicators` | Résultats ou caractéristiques mesurés par territoire et période : code d’indicateur, valeur, unité, portée géographique, source, page/API et notes. |
| `companies` | Référentiel d’entreprises : raison sociale, pays, secteur, ticker, LEI/registre éventuels et territoire du siège. |
| `company_exposures` | Lien entre une entreprise et un territoire : siège, opérations, revenus, emploi, actifs ou assujettissement fiscal. Les scores et leur preuve doivent être documentés ; le simple lien au siège n’est pas une preuve d’exposition économique. |
| `company_indicators` | Résultats d’entreprise datés, localisés et sourcés : chiffre d’affaires, emploi, rémunération, impôt, etc. Cette table est actuellement vide. |
| `company_prices` | Cours boursiers journaliers et rendements dérivés. Ils reflètent le marché et l’entreprise consolidée, pas nécessairement les résultats du site local touché par une réforme. |
| `market_index_prices` | Séries d’indices journaliers servant de référence pour une étude événementielle sur les actions. |

Les relations utilisent des identifiants stables et des clés étrangères. Pour chaque observation, `source_id` indique la source, `period_start` et `period_end` la période, `unit` l’unité et `geographic_scope` le niveau géographique. Les champs `notes` et `source_page` apportent le contexte nécessaire pour ne pas confondre des séries de périmètres différents.

Les vues SQL de [`sql/002_views.sql`](sql/002_views.sql) facilitent la lecture :

- `v_policy_timeline` : réforme, territoire, dates et source ;
- `v_territory_indicators` : indicateurs territoriaux avec territoire et source ;
- `v_company_indicators` et `v_company_exposures` : résultats et expositions des entreprises ;
- `v_company_price_returns` : rendements journaliers calculés depuis les cours ;
- `v_event_study_candidates` : entreprises liées au territoire d’une réforme.

## 3. Les réformes déjà cataloguées

Les huit politiques enregistrées, classées par date d’entrée en vigueur :

| Réforme | Territoire | Entrée en vigueur |
|---|---|---:|
| Taxe sur les boissons sucrées de Philadelphia | Philadelphia | 2017-01-01 |
| Réduction du taux fédéral d’impôt sur les sociétés à 21 % (TCJA) | États-Unis | 2018-01-01 |
| Surtaxe temporaire de l’impôt sur les sociétés pour les contribuables à hauts revenus | État de New York | 2021-01-01 |
| Taxe municipale JumpStart sur les dépenses de paie | Seattle | 2021-01-01 |
| Taux normal d’impôt sur les sociétés porté à 25 % | France | 2022-01-01 |
| Réduction progressive du taux d’impôt sur les sociétés | Pennsylvanie | 2023-01-01 |
| Taux principal de l’impôt sur les sociétés porté à 25 % | Royaume-Uni | 2023-04-01 |
| Mise en œuvre irlandaise du taux minimum de 15 % du Pilier Deux | Irlande | 2023-12-31 |

Les dates d’adoption et d’entrée en vigueur sont conservées séparément. Cela importe pour les textes rétroactifs ou les annonces susceptibles d’avoir affecté les décisions avant la mise en œuvre. Le catalogue ne garantit ni que la réforme a le même champ pour toutes les entreprises, ni qu’un indicateur observé l’identifie causalement.

## 4. Données collectées ou importées et leur recouvrement

### Panels territoriaux et de marché du travail

| Source effectivement utilisée | Contenu en base | Période et géographie | Ce que cela mesure / limites |
|---|---|---|---|
| **BLS QCEW** — collecteurs `fetch_qcew_state_tax_panel.py` et `fetch_qcew_local_panel.py` | **6 418 observations** d’emploi privé et de salaires hebdomadaires, tous secteurs et secteurs sélectionnés | 2015–2025 ; 7 États et 6 comtés de l’État de Washington | Emploi et rémunérations au niveau d’un État ou d’un comté, pas d’une entreprise. King County sert de proxy imparfait pour Seattle. Le titre source dans le catalogue mentionne « state-level », alors que les données incluent aussi les comtés de Washington. |
| **Eurostat, API de diffusion, `lfsi_emp_q`** — `fetch_eurostat_employment_panel.py` | **768 observations** | 16 pays, du T1 2014 au T4 2025 | Emploi total, deux sexes, 15–74 ans, CVS, en milliers de personnes. Résultat national, pas emploi des sociétés assujetties. |
| **ONS, Labour Force Survey** — même collecteur | **25 observations** | Royaume-Uni, T1 2019–T1 2025 | Emploi national CVS des 16 ans et plus, en milliers. Périmètre d’âge différent d’Eurostat. |
| **BLS, Current Population Survey (CPS)** — même collecteur | **47 observations** | États-Unis, T1 2014–T3 2025 | Moyenne trimestrielle du niveau mensuel d’emploi CVS des 16 ans et plus, en milliers. Le T4 2025 n’a pas été calculé à partir d’un trimestre partiel. |
| **GDELT DOC API** — `fetch_gdelt_context.py` | **48 observations** mensuelles | Seattle, 2019–2022 | Volume d’articles correspondant à une requête sur Seattle et JumpStart. C’est une mesure de l’attention médiatique, pas un résultat économique ni un nombre d’événements vérifiés. |

Pour le QCEW, les 13 géographies chargées sont : Pennsylvania, Delaware, Maryland, New Jersey, New York, Ohio, West Virginia, ainsi que King, Clark, Spokane, Thurston, Whatcom et Yakima Counties dans l’État de Washington. Les comtés sont des proxys pour les analyses municipales, pas des frontières fiscales équivalentes aux villes.

### Philadelphia : valeurs d’une étude publiée

L’import `import_philadelphia_beverage_tax_case.py` a ajouté **34 observations agrégées reprises de l’article JAMA**, réparties entre :

- 12 prix annuels de boissons taxées (2016 et 2017, Philadelphia et Baltimore, trois types de magasins) ;
- 12 volumes moyens par période de quatre semaines sur les mêmes territoires, années et types de magasins ;
- 4 volumes annuels rapportés pour Philadelphia et les codes postaux limitrophes ;
- 6 estimations différence-en-différences publiées : effets sur les prix et les volumes par type de magasin.

Ces 34 lignes ne sont **pas des données de caisse brutes** et ne sont **pas une collecte directe des tickets de vente**. La source primaire des chiffres est l’article évalué par les pairs de [JAMA Network Open](https://pubmed.ncbi.nlm.nih.gov/31087022/), fondé sur les données commerciales IRI. Les microdonnées IRI ne sont pas ouvertes dans le dépôt. L’échantillon décrit par l’article comprend 291 magasins de chaînes et environ 25 % des onces de boissons taxées vendues à Philadelphia. Les résultats sont ventilés par type de magasin, pas par marque ou par enseigne.

La source officielle de la Ville de Philadelphia documente la taxe et ses règles, mais ne fournit pas ces mesures de ventes. Les chiffres de l’article sont stockés avec des notes de provenance et ne doivent pas être interprétés comme un panel trimestriel permettant à l’application de refaire l’estimation.

### Fiscalité et taux légaux

Les autres lignes de `territory_indicators` comprennent notamment :

- des taux légaux d’impôt sur les sociétés et des taux liés au Pilier Deux pour quelques juridictions et années de référence, issus de sources administratives ou législatives ;
- les taux de Pennsylvanie associés au calendrier de réduction prévu par l’Act 53 ;
- des résultats de marché du travail et les indicateurs Philadelphia ci-dessus.

Un taux légal n’est pas le taux effectif réellement payé par une entreprise. Les assiettes, seuils, crédits, pertes reportées, répartitions territoriales et règles de groupe ne sont pas reconstruits par ces seuls indicateurs. La base ne contient pas les déclarations fiscales confidentielles.

### Entreprises, expositions et cours

Les 29 entreprises candidates représentent 15 sociétés américaines, 5 britanniques, 4 irlandaises et 5 françaises. Elles ont 29 fiches d’exposition de type **siège social** ; les expositions ne sont pas une mesure vérifiée de la part de leurs ventes, bénéfices, salariés ou impôts qui est concernée par chaque réforme.

Les données de marché proviennent de l’endpoint de cours historiques Yahoo Finance utilisé par `fetch_event_data.py` :

- 15 027 cours journaliers pour 29 entreprises, du 1er août 2017 au 30 avril 2024 selon les périodes propres à chaque entreprise ;
- 3 046 observations pour quatre indices : S&P 500 (`^GSPC`), FTSE (`^FTSE`), CAC 40 (`^FCHI`) et ISEQ (`^ISEQ`).

Ces historiques servent à des études événementielles sur les rendements boursiers. Une réaction boursière autour d’une date ne mesure ni les ventes locales ni l’effet causal d’une réforme sur l’activité locale. La source Yahoo Finance est un endpoint de données de marché, avec des conditions d’accès et de réutilisation à vérifier ; ce n’est pas un registre comptable officiel.

## 5. Sources : données téléchargées versus catalogue documentaire

La table `sources` contient **42 références**, mais il faut distinguer trois situations :

1. **Séries effectivement téléchargées par des collecteurs** : Eurostat, ONS, BLS CPS, BLS QCEW, GDELT DOC API et Yahoo Finance. Les lignes correspondantes sont reliées à des observations ; les commandes ci-dessous permettent de les recharger, sous réserve de disponibilité des API et de leurs conditions d’accès.
2. **Résultats publiés importés** : JAMA pour Philadelphia. Les nombres agrégés ont été transcrits depuis l’article ; les données propriétaires IRI n’ont pas été téléchargées.
3. **Références de lois, organismes et bases potentielles** : par exemple Légifrance, Congrès américain, Pennsylvania General Assembly, New York Senate, UK Parliament, Irish Revenue, INPI, Companies House, SEC/EDGAR, GLEIF, OECD, IMF, OpenAlex, OpenCorporates et registres de brevets. Certaines références légales sont liées à une réforme ou à un taux déjà enregistré ; beaucoup d’autres sont uniquement dans le catalogue. Leur présence ne signifie pas que leurs jeux de données ont été collectés.

Les sources officielles reliées aux huit réformes incluent les textes ou pages de l’Assemblée législative de Pennsylvanie, du Congrès américain, de New York, de Légifrance, du Parlement britannique, du gouvernement/Revenue irlandais, de la Ville de Seattle et de Philadelphia. Les sources fiscales administratives fournissent aussi des valeurs légales ponctuelles. La provenance ligne par ligne s’affiche dans l’onglet **Sources et données** du tableau de bord.

Les collecteurs ne sont pas tous des « scraping » de pages HTML : ils appellent des API officielles ou des fichiers CSV/JSON publiés. Cette distinction permet de savoir si une donnée est un téléchargement reproductible, une valeur extraite d’une publication, une donnée de marché ou une simple référence documentaire.

## 6. Ce que l’on peut faire avec la base aujourd’hui

- **Explorer** les politiques, territoires, sources et indicateurs dans le tableau de bord Streamlit.
- **Tracer** une série territoriale par période, unité et portée géographique, avec sa source.
- **Préparer et estimer une DiD exploratoire** avec séries QCEW ou emploi national lorsque les périodes, unités et indicateurs sont compatibles, et que les territoires témoins sont sélectionnés.
- **Étudier un événement boursier** autour d’une annonce, d’une adoption ou d’une entrée en vigueur, en comparant les rendements d’actions à un indice.
- **Consigner les sources et résultats publiés**, comme le cas Philadelphia, sans présenter les résultats cités comme une nouvelle estimation produite par GLPID.
- **Préparer des extensions** avec des comptes statutaires, des offres d’emploi, des données de salaire ou d’effectifs au niveau établissement, des expositions d’entreprise mieux documentées, ou des microdonnées accessibles sous licence.

Le code contient également des fonctions statistiques pour une DiD intra-entreprise entre lieux, une DiD à intensité d’exposition continue et une RDD autour d’un seuil. Elles nécessitent des données au niveau entreprise/site/salarié et une mesure d’exposition ou de seuil adaptée ; elles ne sont pas alimentées automatiquement par les séries actuellement présentes. Leur présence dans le code ne signifie donc pas que ces analyses sont déjà estimables dans cette base.

## 7. Limites de couverture et d’interprétation

- **Peu de résultats réellement locaux d’entreprise** : `company_indicators` est vide ; les résultats QCEW et les panels Eurostat/ONS/BLS sont agrégés par territoire ou pays.
- **Pas de ventes ou de marques Philadelphia** : l’article publie des résultats agrégés par type de magasin ; ni les enseignes ni les fabricants ne sont identifiés dans les valeurs intégrées.
- **Pas de données administratives individuelles** : aucun fichier DSN/DADS, LEHD/Census, paie, embauches, déclarations fiscales ou registres de salariés n’est stocké.
- **Périmètres hétérogènes** : emploi CVS/non CVS, classes d’âge et niveaux de géographie diffèrent ; des séries du même nom ne sont pas automatiquement comparables.
- **Témoins imparfaits** : un État ou un comté ne représente pas nécessairement un témoin non traité comparable. Plusieurs réformes nationales peuvent toucher aussi les juridictions témoins.
- **Expositions d’entreprises indicatives** : le siège ne détermine pas les ventes, l’emploi, les bénéfices imposables ou l’assujettissement local.
- **Pas de géométries** : la base stocke les noms et relations parent/enfant, pas les polygones nécessaires à une carte précise.
- **Une estimation statistique n’établit pas à elle seule une causalité** : il faut documenter les tendances préalables, les chocs concomitants, la sélection des témoins, les changements de mesure et les erreurs-types.

## 8. Commandes utiles pour vérifier et recharger

Depuis `glpid_simple_starter`, avec PostgreSQL démarré, `.env` configuré et dépendances installées dans `.venv` :

```powershell
# Ouvrir le tableau de bord
.\.venv\Scripts\python.exe -m streamlit run dashboard.py

# Réimporter les séries d'emploi nationales (Eurostat, ONS, BLS CPS)
.\.venv\Scripts\python.exe scripts\fetch_eurostat_employment_panel.py

# Réimporter le panel d'emploi et de salaires QCEW par État
.\.venv\Scripts\python.exe scripts\fetch_qcew_state_tax_panel.py --start-year 2015 --end-year 2025

# Réimporter le panel QCEW Seattle / comtés voisins
.\.venv\Scripts\python.exe scripts\fetch_qcew_local_panel.py --start-year 2015 --end-year 2025

# Réimporter les nombres publiés de l'étude Philadelphia (pas les microdonnées IRI)
.\.venv\Scripts\python.exe scripts\import_philadelphia_beverage_tax_case.py

# Réimporter les cours et séries d'indices du script événementiel
.\.venv\Scripts\python.exe scripts\fetch_event_data.py

# Réimporter le volume d'articles GDELT pour Seattle
.\.venv\Scripts\python.exe scripts\fetch_gdelt_context.py --start-date 2019-01-01 --end-date 2022-12-31
```

Pour contrôler rapidement les volumes et les fenêtres de couverture :

```sql
SELECT 'territories' AS table_name, count(*) FROM territories
UNION ALL SELECT 'sources', count(*) FROM sources
UNION ALL SELECT 'policy_changes', count(*) FROM policy_changes
UNION ALL SELECT 'territory_indicators', count(*) FROM territory_indicators
UNION ALL SELECT 'companies', count(*) FROM companies
UNION ALL SELECT 'company_exposures', count(*) FROM company_exposures
UNION ALL SELECT 'company_indicators', count(*) FROM company_indicators
UNION ALL SELECT 'company_prices', count(*) FROM company_prices
UNION ALL SELECT 'market_index_prices', count(*) FROM market_index_prices;

SELECT s.publisher, s.title, i.indicator_code, i.unit,
       count(*) AS observations, count(DISTINCT i.territory_id) AS territoires,
       min(i.period_start) AS debut, max(i.period_end) AS fin
FROM territory_indicators i
JOIN sources s ON s.source_id = i.source_id
GROUP BY s.publisher, s.title, i.indicator_code, i.unit
ORDER BY s.publisher, i.indicator_code;
```

Les scripts réutilisent des identifiants stables pour mettre à jour les observations déjà importées. Les requêtes d’inventaire décrivent la couverture présente ; elles ne prouvent pas que les données des sources catalogue-only sont disponibles ou ouvertes.

## 9. Fichiers de référence dans le dépôt

- Schéma : [`sql/001_schema.sql`](sql/001_schema.sql)
- Vues : [`sql/002_views.sql`](sql/002_views.sql)
- Interface : [`dashboard.py`](dashboard.py)
- Collecteurs : [`scripts/`](scripts)
- Modèles CSV : [`data/templates/`](data/templates)
- Guide de démarrage : [`README_FR.md`](README_FR.md)
- Étude Philadelphia : [`ETUDE_CAUSALE_TAXE_BOISSONS_PHILADELPHIE.md`](ETUDE_CAUSALE_TAXE_BOISSONS_PHILADELPHIE.md)
