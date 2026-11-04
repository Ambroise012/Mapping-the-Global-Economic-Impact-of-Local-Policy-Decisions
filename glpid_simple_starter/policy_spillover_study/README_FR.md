# Étude pilote — diffusion des politiques publiques

Cette extension documente douze cas répartis dans six familles, aux États-Unis et dans plusieurs pays européens : transparence salariale, droit à la réparation, confidentialité des données, sécurité de l’IA, fiscalité numérique et devoir de vigilance des entreprises. Les deux nouveaux cas comparent la taxe française sur les services numériques avec des taxes nationales similaires et suivent le devoir de vigilance français, la loi allemande de diligence et la directive européenne. Les analogies partielles, propositions, adoptions et textes successeurs restent distingués; une ressemblance ou une succession temporelle ne prouve pas une diffusion directe.

## Installation dans la base GLPID

Depuis `glpid_simple_starter`, avec PostgreSQL et `.env` configurés :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
psql -U postgres -d glpid -f policy_spillover_study\sql\003_policy_diffusion.sql
psql -U postgres -d glpid -f policy_spillover_study\sql\004_national_diffusion_level.sql
.\.venv\Scripts\python.exe policy_spillover_study\scripts\seed_study.py
```

La migration 004 ajoute le niveau juridique « national », nécessaire pour distinguer les lois nationales des États fédérés et des textes supranationaux. Les migrations et le script d’initialisation sont idempotents. Le seed contient 12 cas et 46 lignes de chronologie, dont 9 événements pour les deux cas ajoutés, reliés à des sources officielles. Il n’efface ni ne remplace les données GLPID existantes.

## Visualiser la propagation géographique

L’interface comprend une carte choroplèthe mondiale pour les cas nationaux (taxes numériques et diligence raisonnable) et une carte des États-Unis avec curseur annuel pour la séquence de confidentialité. Choisissez un cas puis déplacez l’année pour voir les jalons documentés. Les cartes n’affichent que les juridictions présentes dans le cas sélectionné; les autres territoires ne sont pas réputés dépourvus de loi.

La séquence CCPA documente six États américains. La carte mondiale compare des textes nationaux aux périmètres différents; la diligence allemande est marquée comme analogue partiel, alors que la séquence supranationale européenne est consultable dans la chronologie. Les dates visualisent l’ordre des événements, pas une causalité.

## Collecter l’attention médiatique GDELT

Les séries mensuelles sont des volumes bruts de résultats de recherche, pas une mesure de soutien public, de causalité ou d’adoption législative. La collecte requiert une connexion Internet ; les comptes varient selon les termes de requête et la couverture de GDELT.

```powershell
.\.venv\Scripts\python.exe policy_spillover_study\scripts\fetch_attention.py --start-date 2019-01-01 --end-date 2026-10-31
```

La commande interroge chaque famille par tranches calendaires annuelles pour limiter la taille des réponses. Les termes alternatifs `OR` des requêtes sont groupés entre parenthèses, comme l’exige la syntaxe GDELT. Chaque tranche annuelle est enregistrée séparément dans `policy_diffusion_attention`. En cas de limitation, relancez la même commande : les tranches déjà complètes sont détectées et ignorées, la collecte reprend à la première tranche manquante. Toute mise à jour est idempotente.

Lors de l’import initial, GDELT a renvoyé une réponse temporairement limitée (HTTP 429 / réponse non JSON) ; aucune série d’attention n’a donc été inventée ou insérée. Relancez la commande lorsque l’API est disponible.

## Vérifier et documenter les sources

Pour contrôler les URL officielles reliées aux événements et enregistrer leur disponibilité actuelle dans PostgreSQL :

```powershell
.\.venv\Scripts\python.exe policy_spillover_study\scripts\verify_sources.py
```

Le collecteur applique une pause entre hôtes, respecte `Retry-After` et conserve le statut HTTP, l’URL finale, le type MIME, le titre/la description HTML et le SHA-256 du contenu reçu. Il **ne stocke pas le corps des pages**. Les pages qui refusent les accès automatisés (403), bloquent temporairement (429) ou sont indisponibles restent signalées comme non vérifiées, pas comme validées.

État du dernier contrôle : 30 URL examinées, dont 12 réponses HTTP 200, 10 refus HTTP 403 et 8 réponses HTTP 202 de passerelle EUR-Lex. Les réponses 202 ne valident pas les pages juridiques. Deux pages françaises Légifrance ont renvoyé 403; les deux références EUR-Lex de diligence ont renvoyé 202. Les textes autrichien, italien, britannique, espagnol et allemand ont renvoyé 200. L’audit enregistre les réponses dans `policy_diffusion_source_checks`.

## Lancer l’interface

```powershell
.\.venv\Scripts\python.exe -m streamlit run policy_spillover_study\dashboard.py
```

L’interface affiche les événements législatifs avec leurs sources, le statut de vérification des URL, les volumes GDELT et les délais entre l’ancre et les événements ultérieurs. Les cartes rendent visibles les séquences américaine et internationale. Plusieurs cas partagent les mêmes textes; ils ne constituent pas des observations indépendantes. L’échantillon sélectionné reste trop petit pour estimer ou valider un modèle prédictif. Les deux nouvelles familles n’ont pas encore de séries GDELT collectées; les requêtes sont enregistrées dans le seed et peuvent être collectées avec `fetch_attention.py`.

## Méthode et limites

- Les fenêtres de 12 et 36 mois sont des résultats temporels bruts : une adoption internationale ultérieure est comptée même si le processus de proposition avait commencé avant la loi d’origine. Les dates de proposition et les notes rendent ce problème de causalité visible.
- Le tableau distingue l’ordre temporel brut d’une séquence plus stricte : proposition postérieure à l’ancre au niveau cible, puis adoption dans la fenêtre. Dans le seed daté du 4 novembre 2026, cette séquence stricte apparaît dans 2/12 fenêtres mûres à 12 mois et 4/11 fenêtres mûres à 36 mois (une fenêtre de 36 mois reste ouverte). Cela reste exploratoire et ne prouve aucune influence.
- Les niveaux cibles varient : État fédéré, niveau international ou national. Le niveau « national » identifie une loi d’un pays; « international » reste réservé aux instruments supranationaux. La carte mondiale écarte les textes UE de la carte des pays.
- Les douze cas sont liés à six familles. Les trois cas de confidentialité suivent des lois communes (notamment le Colorado Privacy Act) et représentent une séquence politique largement partagée, pas trois observations indépendantes. Les cartes distinguent les adoptions nationales des instruments supranationaux et des analogies partielles.
- Une même loi peut être reliée à plusieurs cas. Les 46 événements sont des lignes cas–événement, pas 46 textes de loi uniques.
- Les fenêtres de 12 et 36 mois sont calculées depuis la date d’ancrage affichée. Les adoptions ultérieures sont distinguées des textes seulement proposés, rejetés ou vetoés.
- Les exemples couvrent des niveaux juridiques différents. Les résultats d’un État à un autre sont une diffusion horizontale, pas une adoption fédérale.
- L’absence d’un événement dans la chronologie n’établit pas l’absence d’une politique comparable : la couverture législative du jeu de données n’est pas exhaustive.
- SB 1047 a été vetoé ; son adoption ne peut pas être codée comme un résultat positif. L’AI Act et la Convention du Conseil de l’Europe sont conservés comme analogues partiels, non comme adoptions directes.
- Il faut élargir le nombre de familles, définir des juridictions à risque et documenter les non-adoptions avant toute classification prédictive. GDELT ne remplace pas ces données de résultat.

Les migrations sont `sql/003_policy_diffusion.sql` et `sql/004_national_diffusion_level.sql`; les données de départ sont dans `data/seed_cases.json`, et les tests se trouvent dans `tests/`.
