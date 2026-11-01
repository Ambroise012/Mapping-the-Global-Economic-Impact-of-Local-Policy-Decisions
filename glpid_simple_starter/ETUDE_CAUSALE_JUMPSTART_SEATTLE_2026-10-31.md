# Étude causale exploratoire — JumpStart de Seattle

**Date d’exécution :** 31 octobre 2026  
**Question :** les séries économiques publiques disponibles montrent-elles une variation d’emploi ou de salaire à King County après la mise en œuvre de la taxe JumpStart de Seattle ?  
**Conclusion courte :** les estimations disponibles ne permettent pas d’établir une causalité. L’effet estimé sur l’emploi total est petit, non significatif et sensible au groupe témoin. Le salaire hebdomadaire moyen augmente relativement aux comtés témoins, mais les tendances salariales divergeaient déjà avant la réforme ; cette estimation ne peut donc pas être attribuée à la taxe.

## Données et traitement

- **Politique :** Seattle JumpStart Payroll Expense Tax ; adoption enregistrée le 6 juillet 2020 et entrée en vigueur enregistrée le 1er janvier 2021. La référence en base est `policy-seattle-jumpstart-2021`, avec la source municipale `source-seattle-jumpstart` (ordonnance 126109).
- **Résultats :** emploi privé moyen et salaire hebdomadaire moyen par trimestre, séries QCEW du Bureau of Labor Statistics, tous secteurs privés.
- **Géographie :** King County est utilisé comme proxy de Seattle parce que le QCEW public utilisé ici ne fournit pas l’unité urbaine pertinente. Cinq comtés de Washington servent de témoins : Clark, Spokane, Thurston, Whatcom et Yakima.
- **Panel en base :** 44 trimestres, de 2015-Q1 à 2025-Q4, 6 comtés, soit 264 valeurs par indicateur pour les deux indicateurs totaux (528 cellules territoire-indicateur-période). Les deux séries totales testées sont complètes.
- **Modèle :** DiD sur le logarithme de l’indicateur, effets fixes de territoire et de trimestre, erreurs-types regroupées par comté. La spécification principale traite 2021-Q1 et après comme période postérieure, tout en excluant 2020-Q3 et 2020-Q4 comme transition.

Les résultats sont des écarts relatifs agrégés entre comtés, pas des résultats au niveau de Seattle, de l’établissement ou de l’employeur redevable. Le QCEW ne précise pas quels employeurs paient la taxe.

## Résultats principaux exécutés

| Indicateur | Début du post | Trimestres de transition exclus | Variation relative estimée | IC 95 % | p-valeur | Pré-tendance traitée × temps |
|---|---|---|---:|---:|---:|---:|
| Emploi privé total | 2020-Q3 | aucun | −1,99 % | [−6,51 % ; +2,75 %] | 0,4050 | p=0,0806 |
| Salaire hebdomadaire moyen | 2020-Q3 | aucun | +11,69 % | [+8,42 % ; +15,05 %] | <0,0001 | p<0,0001 |
| Emploi privé total | 2021-Q1 | 2020-Q3 et 2020-Q4 | −2,09 % | [−6,94 % ; +3,01 %] | 0,4156 | p=0,0806 |
| Salaire hebdomadaire moyen | 2021-Q1 | 2020-Q3 et 2020-Q4 | +11,63 % | [+8,15 % ; +15,23 %] | <0,0001 | p<0,0001 |

### Lecture causale

1. **Emploi total :** les intervalles comprennent zéro et les p-valeurs ne montrent pas d’effet détectable. La conclusion est « pas d’effet discernable dans ces données », pas « preuve qu’il n’y a aucun effet ».
2. **Salaire moyen :** le coefficient positif est statistiquement précis sous le modèle, mais le test de tendance préalable est fortement significatif. L’hypothèse de tendances parallèles est donc mise en défaut. Une hausse de salaire moyen peut également résulter d’une modification de la composition de l’emploi, sans hausse équivalente du salaire des salariés déjà en poste.
3. **Attribution :** les dates choisies coïncident avec la pandémie et des changements du marché du travail. Le modèle agrégé ne sépare pas les effets de ces chocs, les retombées vers les comtés voisins, les autres politiques locales et la taxe.

On ne peut donc pas conclure, à partir de cette étude, que la taxe JumpStart a causé la variation du salaire ou de l’emploi observée.

## Sensibilité au choix des comtés témoins

Pour vérifier si un seul comté pilote l’estimation principale, le modèle post-2021-Q1 a été réestimé cinq fois en retirant successivement chaque témoin. Les autres paramètres sont inchangés.

| Témoin retiré | Emploi : variation (IC 95 %) | p-valeur emploi | p pré-tendance emploi | Salaire : variation (IC 95 %) | p-valeur salaire | p pré-tendance salaire |
|---|---|---:|---:|---|---:|---:|
| Clark | −0,41 % [−4,92 % ; +4,32 %] | 0,8628 | 0,0171 | +11,97 % [+7,54 % ; +16,60 %] | <0,0001 | <0,0001 |
| Spokane | −1,65 % [−7,84 % ; +4,95 %] | 0,6160 | 0,1890 | +11,37 % [+6,92 % ; +16,00 %] | <0,0001 | <0,0001 |
| Thurston | −1,55 % [−7,69 % ; +5,00 %] | 0,6342 | 0,0579 | +12,77 % [+9,42 % ; +16,23 %] | <0,0001 | <0,0001 |
| Whatcom | −3,20 % [−8,66 % ; +2,59 %] | 0,2726 | 0,2496 | +11,82 % [+7,32 % ; +16,51 %] | <0,0001 | <0,0001 |
| Yakima | −3,60 % [−8,32 % ; +1,36 %] | 0,1526 | 0,2518 | +10,25 % [+7,80 % ; +12,75 %] | <0,0001 | <0,0001 |

La sensibilité confirme que l’estimation d’emploi reste non significative, mais sa valeur varie de −0,41 % à −3,60 %. Le coefficient du salaire moyen reste positif, mais sa pré-tendance échoue pour chacune des variantes. La significativité du salaire après retrait successif des témoins ne corrige pas ce défaut d’identification.

## Tests placebo avant la politique

Trois estimations avec une pseudo-date en 2018-Q1, limitées à 2016-Q1–2019-Q4 :

| Indicateur | Variation placebo | IC 95 % | p-valeur | p pré-tendance |
|---|---:|---:|---:|---:|
| Emploi total | +1,29 % | [−0,31 % ; +2,91 %] | 0,1137 | 0,9842 |
| Emploi, services professionnels/scientifiques/techniques | +0,83 % | [−4,50 % ; +6,45 %] | 0,7662 | 0,7521 |
| Emploi, hébergement/restauration | −0,31 % | [−2,01 % ; +1,43 %] | 0,7288 | 0,0777 |

Ces placebos n’ont pas d’effet détectable aux seuils usuels dans les modèles exécutés. Ils ne démontrent pas que les tendances seraient parallèles après 2020, ne résolvent pas le problème de géographie et ne neutralisent pas la pandémie.

## Base de données

La base PostgreSQL configurée dans `.env` était accessible et déjà contenait la politique `policy-seattle-jumpstart-2021`, sa source municipale, les six comtés et les données QCEW nécessaires. Le script `fetch_qcew_local_panel.py` a rafraîchi les données de 2015-Q1 à 2025-Q4 et a indiqué **5 802 indicateurs mis à jour/importés pour les séries sectorielles et totales**. Aucun score d’exposition ou faux niveau de traitement n’a été ajouté : le panel QCEW ne permet pas de déterminer quels employeurs sont effectivement assujettis.

Pour une base existante, aucune autre modification manuelle n’est nécessaire. Pour remplir/rafraîchir les données sur une nouvelle base après installation, application du schéma et configuration de `.env` :

```powershell
python scripts\fetch_qcew_local_panel.py --start-year 2015 --end-year 2025
```

Cette commande crée ou met à jour la source QCEW, la source de l’ordonnance, la politique JumpStart, les territoires et les mesures de 6 comtés. Elle nécessite une connexion Internet.

## Commandes PowerShell pour reproduire l’étude

Lancer depuis le dossier `glpid_simple_starter`, avec `.venv` et `.env` configurés et PostgreSQL démarré.

### Spécifications principales

```powershell
# Mise à jour des données (facultative si le panel 2015–2025 est déjà en base)
python scripts\fetch_qcew_local_panel.py --start-year 2015 --end-year 2025

# Adoption / transition exclue, issue principale : emploi total
python scripts\local_employment_did.py --indicator employment --post-quarter 2021-Q1 --adoption-quarter 2020-Q3

# Même fenêtre, salaire hebdomadaire moyen
python scripts\local_employment_did.py --indicator weekly-wage --post-quarter 2021-Q1 --adoption-quarter 2020-Q3

# Spécification alternative, post dès le trimestre d’adoption
python scripts\local_employment_did.py --indicator employment --post-quarter 2020-Q3
python scripts\local_employment_did.py --indicator weekly-wage --post-quarter 2020-Q3
```

### Placebos

```powershell
python scripts\local_employment_did.py --indicator employment --post-quarter 2018-Q1 --adoption-quarter 2018-Q1 --start-quarter 2016-Q1 --end-quarter 2019-Q4
python scripts\local_employment_did.py --indicator employment-professional-scientific-technical --post-quarter 2018-Q1 --adoption-quarter 2018-Q1 --start-quarter 2016-Q1 --end-quarter 2019-Q4
python scripts\local_employment_did.py --indicator employment-accommodation-food-services --post-quarter 2018-Q1 --adoption-quarter 2018-Q1 --start-quarter 2016-Q1 --end-quarter 2019-Q4
```

### Sensibilité : retirer un témoin à la fois

Cette boucle reproduit les dix variantes de sensibilité (emploi et salaire) :

```powershell
$controls = @(
    "us-wa-clark-county",
    "us-wa-spokane-county",
    "us-wa-thurston-county",
    "us-wa-whatcom-county",
    "us-wa-yakima-county"
)

foreach ($indicator in @("employment", "weekly-wage")) {
    foreach ($omitted in $controls) {
        $remaining = @($controls | Where-Object { $_ -ne $omitted })
        Write-Output "Indicateur: $indicator ; témoin retiré: $omitted"
        python scripts\local_employment_did.py `
            --indicator $indicator `
            --post-quarter 2021-Q1 `
            --adoption-quarter 2020-Q3 `
            --control-ids $remaining
    }
}
```

Chaque exécution imprime le coefficient DiD, l’intervalle de confiance, la p-valeur, le test de pré-tendance et les réserves d’interprétation.

## Données nécessaires pour une étude plus probante

L’estimation actuelle répond à une question agrégée, pas à l’effet sur les employeurs légalement visés. Une analyse mieux identifiée demanderait :

1. emploi et rémunérations par établissement et trimestre, à Seattle et dans des zones de comparaison proches ;
2. une variable d’assujettissement documentée par employeur/établissement selon les règles de masse salariale, de rémunération et de travail effectué à Seattle, avant et après la réforme ;
3. des témoins non assujettis mais comparables, ou des établissements de mêmes groupes situés juste hors de la frontière, sans contamination importante ;
4. plusieurs années pré-réforme et post-réforme, tests dynamiques des coefficients avant traitement, placebos spatiaux/temporels et analyses de sensibilité ;
5. des erreurs-types adaptées au nombre réel d’unités de traitement. Six comtés ne suffisent pas à une inférence solide.

Ces données administratives sont soumises à des restrictions d’accès et de confidentialité. Ne pas importer de microdonnées individuelles dans PostgreSQL ou les exporter d’un environnement sécurisé sans autorisation. Sans accès à ces données, la conclusion correcte reste que les résultats publics testés ne démontrent pas un lien causal.
