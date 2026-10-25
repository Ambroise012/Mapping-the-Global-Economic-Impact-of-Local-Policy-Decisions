# GLPID — guide de démarrage (Windows)

## Objectif
Base de recherche pour relier des changements de fiscalité/réglementation dans un territoire aux évolutions des entreprises qui y sont implantées. Cette version est volontairement simple : PostgreSQL, cinq tables, CSV et un script d'import. Elle ne télécharge pas automatiquement les lois ou rapports annuels.

## 1. Installer
Installez PostgreSQL (https://www.postgresql.org/download/windows/) et Python 3.11+ (https://www.python.org/downloads/windows/). Ouvrez PowerShell et vérifiez `python --version` et `psql --version`.

## 2. Décompresser
Décompressez le ZIP, puis ouvrez PowerShell dans le dossier `glpid_simple_starter`.

## 3. Créer la base
```powershell
psql -U postgres
```
Dans l'invite SQL :
```sql
CREATE DATABASE glpid;
\q
```
Ou créez une base `glpid` dans pgAdmin.

## 4. Créer les tables
Depuis PowerShell, dans le dossier du projet :
```powershell
psql -U postgres -d glpid -f sql/001_schema.sql
psql -U postgres -d glpid -f sql/002_views.sql
```
Si la base existe déjà, réexécutez ces deux commandes après une mise à jour du projet : les tables et vues manquantes seront ajoutées sans supprimer les données existantes. Dans pgAdmin, exécutez chaque fichier dans Query Tool, dans cet ordre.

## 5. Préparer Python
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```
Modifiez `.env` avec vos paramètres PostgreSQL. Ne partagez pas ce fichier et ne le commitez pas dans Git.

## 6. Importer les territoires exemples
```powershell
python scripts/import_csv.py data/territories.csv territories
```
Les exemples sont indicatifs : La Défense et Silicon Valley ne sont pas des unités administratives simples et leurs limites doivent être définies selon la recherche.

### En cas d'erreur d'authentification PostgreSQL
Une erreur `password authentication failed for user "postgres"` signifie que le serveur a été trouvé, mais que le mot de passe fourni ne correspond pas à celui de ce compte PostgreSQL. Ce n'est pas une erreur de création des tables.

1. Vérifiez dans `.env` que `PGUSER` est le bon utilisateur et que `PGPASSWORD` contient le mot de passe défini pour cet utilisateur lors de l'installation de PostgreSQL. Remplacez bien `CHANGE_ME` si cette valeur est encore présente.
2. Testez les identifiants directement dans PowerShell ; `-W` demande le mot de passe sans l'inscrire dans la commande :
   ```powershell
   psql -h localhost -p 5432 -U postgres -d glpid -W -c "SELECT 1;"
   ```
   Si ce test échoue aussi, corrigez le mot de passe du compte PostgreSQL (par exemple dans pgAdmin si vous pouvez vous y connecter), puis reportez le même mot de passe dans `.env`.
3. Une variable d'environnement déjà définie dans PowerShell prend priorité sur `.env`. Pour vérifier sans afficher les valeurs :
   ```powershell
   Get-ChildItem Env:PG*
   ```
   Si `PGPASSWORD` apparaît avec une ancienne valeur, supprimez-la pour cette session avant de relancer le script :
   ```powershell
   Remove-Item Env:PGPASSWORD
   ```

## 7. Ajouter des données
Les fichiers fournis contiennent un premier jeu de référence pour les territoires, les sources officielles, quelques réformes fiscales et les taux légaux d'impôt sur les sociétés observés pour 2024. Importez-les dans cet ordre :
```powershell
python scripts/import_csv.py data/templates/sources.csv sources
python scripts/import_csv.py data/territories.csv territories
python scripts/import_csv.py data/templates/policy_changes.csv policy_changes
python scripts/import_csv.py data/territory_indicators.csv territory_indicators
python scripts/import_csv.py data/templates/companies.csv companies
python scripts/import_csv.py data/templates/company_indicators.csv company_indicators
```
Le script importe ou met à jour les lignes à partir de leur identifiant. Les exemples d'entreprises et d'indicateurs d'entreprises restent vides : ne les importez pas tant qu'ils ne contiennent pas vos données.

`territory_indicators` stocke les variables fiscales et macroéconomiques attachées à un territoire et à une période, indépendamment d'une entreprise. Les indicateurs 2024 sont des taux légaux de référence, pas des taux effectifs payés par une entreprise. Les règles fiscales comportent seuils, exonérations, surtaxes et critères d'éligibilité ; les notes et liens officiels en précisent certaines limites. Ne combinez pas mécaniquement les taux fédéral et californien.

Le catalogue `sources.csv` référence des sources, pas les jeux de données eux-mêmes. Les quartiers d'affaires (La Défense, Silicon Valley, City of London) ne sont pas tous des territoires fiscaux administratifs. Les territoires proposés sont des repères de géographie ; définissez le périmètre et les entreprises exposées dans chaque étude.

Vérifiez les licences, les conditions d'accès, les limites d'API et la couverture avant toute collecte. Une source répertoriée ne signifie pas que ses données ont été téléchargées, ni qu'elles sont toutes gratuites ou ouvertes. Les sources agrégées comme les statistiques CbCR ne fournissent pas nécessairement de données au niveau d'une entreprise.

## 8. Vérifier
```powershell
psql -U postgres -d glpid
```
Puis :
```sql
SELECT * FROM territories ORDER BY territory_type, name;
SELECT * FROM v_policy_timeline;
SELECT * FROM v_company_indicators;
SELECT * FROM v_territory_indicators ORDER BY territory, indicator_code;
\q
```

## 9. Méthode de recherche conseillée
1. Trouver une réforme et son texte officiel.
2. Enregistrer la source officielle dans `sources`.
3. Enregistrer séparément date d'annonce, adoption et entrée en vigueur.
4. Sélectionner les entreprises exposées.
5. Ajouter leurs rapports annuels comme sources.
6. Collecter des indicateurs avant/après, en précisant s'ils sont mondiaux, nationaux, régionaux ou locaux.
7. Comparer avec un territoire ou des entreprises comparables.

## Sources de départ
Le catalogue et les liens des sources évoquées sont dans `data/templates/sources.csv`. Pour des sources supplémentaires, notamment INSEE / Sirene, Eurostat, Federal Register et Irish Statute Book, vérifiez leurs documentations officielles avant de les ajouter.

## 10. Tester un effet d’événement (courant boursier / juridiction)

Pour analyser si un changement de juridiction a des effets sur un cours boursier, il faut enregistrer :
- la réforme dans `policy_changes` ;
- les entreprises exposées dans `company_exposures` ;
- les cours quotidiens dans `company_prices` ;
- un indice de marché de référence dans `market_index_prices` (optionnel, mais utile).

Après une mise à jour du projet, appliquez le schéma à la base avant d’utiliser le script. Depuis le dossier `glpid_simple_starter` :

```powershell
psql -U postgres -d glpid -f sql/001_schema.sql
psql -U postgres -d glpid -f sql/002_views.sql
```

Le script suivant calcule un event study simple, en comparant le rendement journalier de chaque entreprise à celui de l’indice de référence :

```powershell
python scripts/event_study.py --policy-id policy-us-tcja-corporate-rate --event-column adoption_date --window-days 5 --index-name "^GSPC"
```

Le script :
- cherche la politique et sa date d’événement ;
- identifie les entreprises exposées au même territoire ;
- calcule les rendements journaliers autour de la date ;
- compare chaque action au rendement journalier de l’indice indiqué dans `market_index_prices` ;
- affiche le cumul du rendement anormal (CAR) par entreprise.

Pour le cas américain, le 22 décembre 2017 correspond à la signature de la loi (date d’adoption), et non à la première annonce du projet. Les cours d’entreprises et de l’indice doivent couvrir cette date, avec suffisamment de jours de bourse avant et après. `^GSPC` est ici le nom à utiliser dans `market_index_prices.index_name` pour le S&P 500 ; le nom doit correspondre exactement à celui importé.

Pour remplir la base avec des cours historiques de démonstration pour AAPL, MSFT, GOOGL, CSCO, ORCL et le S&P 500, lancez :

```powershell
python scripts/fetch_event_data.py
```

Pour comparer un autre cas déjà présent dans la base, le jeu britannique correspond à Barclays, HSBC, GSK, AstraZeneca, Unilever et au FTSE 100, autour de l’annonce du 3 mars 2021 :

```powershell
python scripts/fetch_event_data.py --case uk
python scripts/event_study.py --policy-id policy-uk-corporation-tax-2023 --event-column announcement_date --window-days 5 --index-name "^FTSE"
```

Un troisième jeu permet d’examiner la mise en œuvre irlandaise de Pillar Two avec Ryanair, Glanbia, Bank of Ireland Group, DCC et l’indice ISEQ :

```powershell
python scripts/fetch_event_data.py --case ie
python scripts/event_study.py --policy-id policy-ie-pillar-two --event-column adoption_date --window-days 5 --index-name "^ISEQ"
```

Un cas à l’échelle d’un État américain est disponible pour la baisse progressive de l’impôt sur les sociétés en Pennsylvanie (Act 53 de 2022), avec Comcast, PNC, Hershey, UGI, Crown Holdings et le S&P 500 :

```powershell
python scripts/fetch_event_data.py --case pa
python scripts/event_study.py --policy-id policy-pa-corporate-rate-2023 --event-column adoption_date --window-days 5 --index-name "^GSPC"
python scripts/event_study.py --policy-id policy-pa-corporate-rate-2023 --event-column effective_date --window-days 5 --index-name "^GSPC"
```

Deux autres exemples permettent de varier la juridiction et les dates :

```powershell
python scripts/fetch_event_data.py --case ny
python scripts/event_study.py --policy-id policy-ny-corporate-surcharge-2021 --event-column adoption_date --window-days 5 --index-name "^GSPC"
python scripts/event_study.py --policy-id policy-ny-corporate-surcharge-2021 --event-column effective_date --window-days 5 --index-name "^GSPC"

python scripts/fetch_event_data.py --case fr
python scripts/event_study.py --policy-id policy-fr-corporate-rate-25-2022 --event-column adoption_date --window-days 5 --index-name "^FCHI"
python scripts/event_study.py --policy-id policy-fr-corporate-rate-25-2022 --event-column effective_date --window-days 5 --index-name "^FCHI"
```

Le cas `ny` est une surcharge temporaire de l’impôt sur les sociétés de l’État de New York, avec IBM, Pfizer, Verizon, JPMorgan et Goldman Sachs ; le cas `fr` est la dernière étape de la baisse progressive du taux normal français à 25 %, avec Airbus, LVMH, L’Oréal, Sanofi et BNP Paribas. Les dates d’entrée en vigueur peuvent tomber un jour sans séance boursière ; le script descriptif utilise alors les jours de marché de la fenêtre.

Les périodes par défaut téléchargées sont : US, du 1er août 2017 au 1er avril 2018 ; UK, du 1er octobre 2020 au 30 juin 2021 ; IE, du 1er juillet 2023 au 30 avril 2024 ; PA, du 1er juin 2022 au 31 mars 2023 ; NY, du 1er octobre 2020 au 31 juillet 2021 ; FR, du 1er août 2017 au 31 janvier 2023. Ces périodes plus longues permettent les diagnostics pré-événement et placebo. Le script télécharge depuis l’endpoint historique Yahoo Finance, puis insère ou met à jour les prix, les sociétés candidates, leurs expositions candidates et la source dans la base PostgreSQL configurée par `.env`. Il faut une connexion Internet. Utilisez `--start-date` et `--end-date` pour charger une autre période. L’accès et la réutilisation des données restent soumis aux conditions actuelles du fournisseur.

Les sociétés sont des échantillons de démonstration, pas des groupes traités scientifiquement établis : leur exposition fiscale effective n’est pas mesurée par ce téléchargement. Vérifiez leurs rapports et ajoutez des entreprises témoins comparables avant d’interpréter les CAR comme un effet de la réforme. Les gabarits CSV dans `data/templates` restent disponibles pour importer vos propres observations vérifiées.

### Comparaison traité/témoin et vérifications causales

Le CAR descriptif ci-dessus ne suffit pas pour attribuer un mouvement à une réforme. Le script `scripts/causal_event_study.py` estime une différence-en-différences sur des séances de bourse, avec rendements ajustés de l’indice, effets fixes par entreprise et par séance, test de pré-tendance et date placebo :

```powershell
python scripts/causal_event_study.py --policy-id policy-us-tcja-corporate-rate --event-column adoption_date --index-name "^GSPC"
```

Cette estimation exige, pour le territoire concerné, au moins trois entreprises traitées avec `company_exposures.exposure_score >= 0.5` et trois entreprises témoins comparables avec `exposure_score <= 0.1`. Pour une réforme d’État, ajoute également les entreprises témoins hors de l’État au même territoire de réforme (`company_exposures.territory_id`), avec une exposition à la politique étayée par des sources ; complète `companies.sector`, ainsi que `company_exposures.source_id` et `source_page` pour chaque score. Les scores doivent être documentés à partir de données antérieures à la réforme (par exemple, part des bénéfices ou impôts concernés), pas attribués en fonction des cours observés après l’événement. Enregistre d’abord la source du rapport dans `sources`. Les sociétés candidates importées par `fetch_event_data.py` ont volontairement un score vide ; elles ne suffisent donc pas à former ces groupes. Renseigne des témoins et leur exposition à partir de rapports vérifiables avant de lancer l’estimation.

Par défaut, le script compare ±5 séances, examine les 60 séances préalables en excluant les cinq immédiatement avant l’événement du test de pré-tendance, et teste un placebo 20 séances avant. Les dates de cotation de l’indice définissent le calendrier. Un intervalle de confiance ou une p-valeur ne prouve pas la causalité : avec peu d’entreprises, les erreurs-types clusterisées restent fragiles ; les tendances parallèles, l’absence d’autres chocs et la bonne mesure d’exposition doivent aussi être défendues.

## 11. Étude exploratoire de l’emploi local à Seattle

Le script `scripts/fetch_qcew_local_panel.py` télécharge auprès du Bureau of Labor Statistics les données trimestrielles QCEW d’emploi privé moyen et de salaire hebdomadaire moyen, tous secteurs, pour King County et cinq comtés de comparaison. Il enregistre directement la source, les territoires et les indicateurs dans PostgreSQL. La base doit déjà avoir reçu `sql/001_schema.sql` et `sql/002_views.sql`, et les variables de connexion doivent être configurées dans `.env`.

```powershell
python scripts/fetch_qcew_local_panel.py --start-year 2015 --end-year 2025
python scripts/local_employment_did.py --indicator employment --post-quarter 2020-Q3
python scripts/local_employment_did.py --indicator employment --post-quarter 2021-Q1 --adoption-quarter 2020-Q3
python scripts/local_employment_did.py --indicator weekly-wage --post-quarter 2020-Q3
python scripts/local_employment_did.py --indicator weekly-wage --post-quarter 2021-Q1 --adoption-quarter 2020-Q3
```

Cette analyse est **exploratoire, pas une estimation causale fiable de l’effet de la taxe Seattle** : le QCEW public est au niveau du comté, de sorte que King County est un proxy imparfait de la ville. Les comparaisons portent sur cinq autres comtés de Washington et six grappes seulement ; les erreurs-types et p-valeurs sont fragiles. Il faut aussi examiner les tendances préalables et les effets de la pandémie. En particulier, des tendances salariales préalables divergentes invalident l’interprétation DiD simple, même si l’estimation affiche une p-valeur faible.

Le téléchargement inclut également les séries QCEW de secteurs (information, finance, services professionnels, gestion, santé, hébergement/restauration, etc.). Les codes `--indicator` détaillés sont affichés par `python scripts/local_employment_did.py --help`. Pour tester des pseudo-dates antérieures à la taxe sur une période strictement pré-politique :

```powershell
python scripts/local_employment_did.py --indicator employment --post-quarter 2018-Q1 --adoption-quarter 2018-Q1 --start-quarter 2016-Q1 --end-quarter 2019-Q4
python scripts/local_employment_did.py --indicator employment-professional-scientific-technical --post-quarter 2018-Q1 --adoption-quarter 2018-Q1 --start-quarter 2016-Q1 --end-quarter 2019-Q4
```

### Contexte médiatique avec GDELT

Une série mensuelle de volume d’articles GDELT peut être récupérée comme chronologie de l’attention médiatique autour de JumpStart :

```powershell
python scripts/fetch_gdelt_context.py --start-date 2019-01-01 --end-date 2022-12-31
```

Cette série ne mesure ni l’emploi ni l’impact causal. L’API a renvoyé HTTP 429 lors de la collecte de ce projet ; en cas de 429, attendre avant de réessayer et ne pas lancer de boucles de requêtes. Aucune donnée GDELT n’a pour l’instant été importée dans la base.

## Limites
Cette version ne collecte pas automatiquement les sources. Le script DiD produit une estimation conditionnelle aux données fournies, mais n’établit pas à lui seul un effet causal. Les comptes consolidés mondiaux ne mesurent pas directement les effets locaux. Conservez une URL, un périmètre et une période pour chaque donnée. Une valeur inconnue doit rester vide, jamais être inventée.
