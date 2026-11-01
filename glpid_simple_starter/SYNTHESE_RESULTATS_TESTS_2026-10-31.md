# Synthèse des tests exécutés — 31 octobre 2026

## Résumé

Les commandes du plan ont été lancées avec l’environnement Python du projet et la base PostgreSQL configurée dans `.env`.

- Schéma vérifié/appliqué ; 30 sources, 24 territoires et 3 politiques de référence importés ou mis à jour.
- Cours téléchargés pour les six cas boursiers (`us`, `uk`, `ie`, `pa`, `ny`, `fr`) ; la période du Royaume-Uni a aussi été prolongée jusqu’en 2023 pour tester sa date d’entrée en vigueur.
- Panel officiel QCEW téléchargé : 5 802 indicateurs, 44 trimestres, 6 comtés (King County et cinq témoins).
- Seize spécifications d’étude événementielle ont abouti. Elles mesurent des rendements boursiers anormaux descriptifs autour de dates de réforme.
- Sept DiD locales Seattle/placebos ont abouti. Les résultats d’emploi total sont non concluants ; l’estimation de salaire présente une pré-tendance marquée.
- Les trois commandes de DiD boursière ont été lancées mais ont refusé l’estimation : les entreprises candidates n’ont pas de scores d’exposition documentés.
- GDELT a importé 48 comptages mensuels, qui mesurent l’attention médiatique et non l’activité économique.
- Tests du projet : **11 réussis**.

## Études événementielles boursières

Les valeurs ci-dessous sont les moyennes arithmétiques des CAR des sociétés candidates, calculées par `scripts/event_study.py` et arrondies à 0,001 point de pourcentage. Les fenêtres sont en jours calendaires ; le nombre de séances réellement utilisé dépend des jours de marché. Les bornes indiquent les CAR minimum et maximum individuels de la fenêtre.

| Cas | Date testée | Fenêtre | Séances | CAR moyen | Étendue entre sociétés |
|---|---|---:|---:|---:|---:|
| États-Unis fédéral — TCJA | Adoption, 22/12/2017 | ±5 jours | 7 | −1,306 % | −2,163 % à +0,720 % |
| États-Unis fédéral — TCJA | Effet, 01/01/2018 | ±5 jours | 7 | +0,805 % | −0,107 % à +1,808 % |
| Royaume-Uni — Corporation Tax | Annonce, 03/03/2021 | ±5 jours | 7 | +2,711 % | −1,085 % à +8,255 % |
| Royaume-Uni — Corporation Tax | Effet, 01/04/2023 | ±5 jours | 9 | +2,438 % | −1,841 % à +8,136 % |
| Irlande — Pillar Two | Adoption, 18/12/2023 | ±5 jours | 8 | −3,345 % | −10,299 % à +0,485 % |
| Irlande — Pillar Two | Effet, 31/12/2023 | ±5 jours | 7 | +1,597 % | −2,839 % à +5,803 % |
| Pennsylvanie — baisse de l’impôt sur les sociétés | Adoption, 08/07/2022 | ±1 jour | 2 | −1,482 % | −3,865 % à −0,095 % |
| Pennsylvanie | Adoption | ±5 jours | 7 | −1,254 % | −4,420 % à +0,677 % |
| Pennsylvanie | Effet, 01/01/2023 | ±5 jours | 8 | +2,093 % | −5,742 % à +7,073 % |
| Pennsylvanie | Effet | ±10 jours | 13 | +2,510 % | −5,987 % à +6,547 % |
| État de New York — surtaxe | Adoption, 19/04/2021 | ±1 jour | 2 | +1,038 % | −1,829 % à +4,645 % |
| État de New York | Adoption | ±5 jours | 8 | +1,659 % | −3,424 % à +7,445 % |
| État de New York | Effet inscrit, 01/01/2021 | ±5 jours | 7 | +2,930 % | −2,288 % à +9,822 % |
| État de New York | Effet inscrit | ±10 jours | 13 | +2,905 % | −5,203 % à +10,862 % |
| France — taux normal d’IS à 25 % | Adoption, 30/12/2017 | ±5 jours | 6 | −0,779 % | −2,463 % à +0,619 % |
| France — taux normal d’IS à 25 % | Effet, 01/01/2022 | ±5 jours | 9 | +0,306 % | −4,441 % à +4,931 % |

### Interprétation

Ces CAR décrivent les variations des actions par rapport à l’indice associé ; ils ne mesurent pas les recrutements, salaires, investissements ou comptes des filiales locales. Les sociétés importées sont des candidates fondées notamment sur leur siège, et non des entreprises dont l’assujettissement ou l’intensité d’exposition a été vérifié. Les signes différents selon les sociétés, les fenêtres et les dates interdisent de lire ces moyennes comme un effet causal de la fiscalité. Certaines dates d’effet sont anticipées, rétroactives ou tombent un jour sans séance.

## Seattle : emploi et salaire au niveau du comté

Les estimations emploient King County comme proxy imparfait de Seattle, avec cinq comtés témoins, des indicateurs QCEW trimestriels et une spécification en logarithmes. Les intervalles sont à 95 % et les erreurs-types sont regroupées sur six comtés seulement.

| Indicateur et spécification | Variation estimée | IC 95 % | p-valeur | Écart de pré-tendance linéaire |
|---|---:|---:|---:|---:|
| Emploi total, post dès 2020-Q3 | −1,99 % | [−6,51 % ; +2,75 %] | 0,4050 | p=0,0806 |
| Salaire hebdomadaire moyen, post dès 2020-Q3 | +11,69 % | [+8,42 % ; +15,05 %] | <0,0001 | p<0,0001 |
| Emploi total, post dès 2021-Q1 ; transition 2020-Q3/Q4 exclue | −2,09 % | [−6,94 % ; +3,01 %] | 0,4156 | p=0,0806 |
| Salaire hebdomadaire moyen, post dès 2021-Q1 ; transition exclue | +11,63 % | [+8,15 % ; +15,23 %] | <0,0001 | p<0,0001 |

L’estimation d’emploi total n’est pas statistiquement discernable de zéro dans ces spécifications. Le salaire montre un écart estimé, mais sa pré-tendance significative indique que King County et les témoins évoluaient déjà différemment avant la réforme ; cette DiD ne justifie donc pas une interprétation causale du résultat salarial. Les erreurs-types sur six comtés sont fragiles, la pandémie coïncide avec la période et le QCEW n’identifie pas les employeurs assujettis.

### Placebos antérieurs à la réforme

Les trois pseudo-réformes commencent en 2018-Q1 et utilisent uniquement 2016-Q1 à 2019-Q4 :

| Indicateur placebo | Variation estimée | IC 95 % | p-valeur | Pré-tendance |
|---|---:|---:|---:|---:|
| Emploi total | +1,29 % | [−0,31 % ; +2,91 %] | 0,1137 | p=0,9842 |
| Emploi, services professionnels/scientifiques/techniques | +0,83 % | [−4,50 % ; +6,45 %] | 0,7662 | p=0,7521 |
| Emploi, hébergement/restauration | −0,31 % | [−2,01 % ; +1,43 %] | 0,7288 | p=0,0777 |

Ces placebos n’affichent pas d’effet détectable, mais ne valident pas à eux seuls l’hypothèse causale de l’analyse principale.

## DiD boursière traités/témoins

Les trois commandes prévues pour la Pennsylvanie (adoption et date d’effet) et l’État de New York (adoption) ont toutes été lancées. Elles s’arrêtent avec le message indiquant qu’il faut au moins trois entreprises traitées et trois témoins documentés. Pour chaque politique, les cinq sociétés importées ont un score d’exposition manquant : **0 traité, 0 témoin, 5 scores manquants**.

Ce refus est attendu et préférable à l’attribution de scores arbitraires. La DiD ne pourra être exécutée qu’après avoir renseigné des mesures d’exposition pré-réforme, leurs sources et pages, et ajouté des témoins comparables.

## Autres commandes exécutées ou non exécutables

- **Collecte des cas boursiers :** téléchargements réussis pour `us`, `uk`, `ie`, `pa`, `ny` et `fr` ; téléchargement UK prolongé au 30/06/2023 pour inclure la date d’effet.
- **QCEW :** collecte réussie de 2015-Q1 à 2025-Q4, 5 802 observations importées/mises à jour.
- **GDELT :** collecte réussie de 48 comptages mensuels. Cette série ne représente que l’attention médiatique.
- **Tests automatiques :** `python -m unittest discover -s tests` — 11 tests réussis.
- **Modèles `within-firm`, `continuous-did` et `rdd` :** non exécutés, car les fichiers `data\local_cases\policy\within_firm.csv`, `exposure_panel.csv` et `threshold.csv` n’existent pas. Ces modèles requièrent des observations réelles, autorisées et documentées.
- **San Francisco et CFE :** aucune estimation exécutée ; les données nécessaires (exposition et indicateurs pré/post) n’ont pas été collectées. Les gabarits vides ne produisent pas de résultats.

## Conclusion

Les commandes ont produit des réactions boursières descriptives pour six cas et des DiD exploratoires d’emploi/salaire pour le proxy régional de Seattle. À ce stade, **aucun résultat ne mesure l’impact économique mondial causal d’un changement fiscal local**. Les sorties boursières portent sur des sociétés mondiales candidates ; les sorties Seattle agrègent un comté et ne distinguent pas les employeurs imposés. Une conclusion causale exige des résultats locaux adaptés, une exposition documentée avant la réforme, des témoins crédibles et des tests de robustesse.

Une analyse complémentaire des tendances préalables et de la sensibilité aux comtés témoins est documentée dans [l’étude JumpStart de Seattle](./ETUDE_CAUSALE_JUMPSTART_SEATTLE_2026-10-31.md).

## Cas empiriques documentés dans la littérature

Pour aller au-delà des exemples de cours boursiers, les études suivantes observent des résultats économiques d’entreprises ou de travailleurs après des variations fiscales ou réglementaires infranationales. Elles montrent qu’on peut observer des effets localisés, mais leurs populations et leurs unités d’analyse ne sont pas interchangeables.

| Cas et réforme | Résultat observé dans l’étude | Méthode et source | Limites et intérêt pour ce projet |
|---|---|---|---|
| **Taux d’impôt des États américains sur les sociétés et le revenu** — étude publiée en 2019, portant sur un ensemble de variations de taux et non une réforme unique | Pour les C corporations, les auteurs rapportent des élasticités de court terme de l’emploi de **−0,4** et du nombre d’établissements de **−0,5** par rapport au taux d’impôt sur les sociétés. Pour les entreprises pass-through, l’élasticité de l’emploi au taux d’impôt sur le revenu est **−0,2**. Environ la moitié de la réponse estimée passe par la réallocation entre États. | Données administratives du Census sur les entreprises multi-établissements et leurs implantations. [Giroud et Rauh, *State Taxation and the Reallocation of Business Activity: Evidence from Establishment-Level Data*, NBER WP 21534](https://www.nber.org/papers/w21534), publié dans le *Journal of Political Economy* ([DOI](https://doi.org/10.1086/701357)). | Résultat directement pertinent pour l’emploi et la relocalisation d’établissements. Il porte sur des entreprises mobiles et ne dit pas que l’activité totale nationale ou mondiale augmente : une partie de l’effet est une redistribution entre territoires. Une réplication nécessite un panel multi-États, absent des données actuellement importées. |
| **Zones d’entreprise en Californie et incitations fiscales à l’embauche** — désignations et extensions de zones | L’étude ne trouve pas d’augmentation attribuable à ces zones de l’emploi total ni de réorientation de l’emploi vers les travailleurs à bas salaire visés. Il s’agit d’un résultat de précaution proche du nul, sans coefficient unique indiqué dans le résumé de l’article. | Données d’établissements géocodées et frontières des zones ; étude des désignations et comparaison spatiale. [Neumark et Kolko, *Do Enterprise Zones Create Jobs? Evidence from California’s Enterprise Zone Program*, NBER WP 14530](https://www.nber.org/papers/w14530), publié dans le *Journal of Urban Economics* ([DOI](https://doi.org/10.1016/j.jue.2010.01.002)). | Le résultat concerne un programme précis, pas toutes les incitations fiscales locales. Il illustre l’importance de vérifier la création nette d’emplois plutôt que de compter les emplois déclarés dans une zone. Non réplicable avec les séries QCEW agrégées par comté et les données actuelles du projet. |
| **Seattle — relèvements progressifs du salaire minimum**, de 9,47 $ à 11 $/h en 2015, puis vers 13 $/h en 2016 | Pour les emplois à bas salaire après la phase à 13 $, l’étude estime une réduction de **6–7 % des heures travaillées**, une hausse d’environ **3 % des salaires**, et une baisse de masse salariale d’environ **74 $ par emploi et par mois en 2016**. L’analyse sectorielle de la restauration estime toutefois un effet nul sur l’emploi. | Données administratives de l’Employment Security Department de l’État de Washington et méthodes quasi expérimentales. [Jardim et al., *Minimum Wage Increases, Wages, and Low-Wage Employment: Evidence from Seattle*, NBER WP 23532](https://www.nber.org/papers/w23532). | Ce n’est **pas une réforme fiscale**, mais un cas local utile pour comprendre le choix de l’issue mesurée et la sensibilité à l’agrégation. Le QCEW téléchargé ici permet d’examiner l’emploi et les salaires moyens du comté, pas les heures individuelles ou les travailleurs sous le seuil salarial étudiés dans cet article. |
| **New Jersey — hausse du salaire minimum de 4,25 $ à 5,05 $/h**, effective le 1er avril 1992 | Dans une enquête de 410 restaurants fast-food au New Jersey et en Pennsylvanie, l’emploi par restaurant au New Jersey évolue **13 % plus favorablement** que dans l’État témoin ; les restaurants déjà au-dessus du nouveau seuil ne présentent pas la même hausse relative. | Différences-en-différences avant/après entre établissements. [Card et Krueger, NBER WP 4509](https://www.nber.org/papers/w4509), article dans l’*American Economic Review* ([DOI](https://doi.org/10.1257/aer.84.4.772)). | Résultat classique mais contesté : Neumark et Wascher ont publié une critique utilisant des données de paie, à laquelle Card et Krueger ont répondu ([critique](https://doi.org/10.1257/aer.90.5.1362), [réponse](https://doi.org/10.1257/aer.90.5.1397)). Cela rappelle qu’un résultat peut dépendre de la source, de l’échantillon et de la définition de l’emploi. Un QCEW par secteur ne reproduirait pas les observations restaurant par restaurant. |

### Ce qu’on peut tester dans le projet maintenant

Le résultat le plus directement prolongeable est celui de Seattle, avec l’emploi et le salaire moyen trimestriels QCEW déjà téléchargés pour King County et cinq comtés témoins. C’est une **adaptation d’un résultat local à des données agrégées différentes**, pas une reproduction des études sur salaire minimum ou impôts des entreprises. Les données disponibles ne fournissent ni des heures individuelles, ni les employeurs assujettis à JumpStart, ni un panel multi-États d’établissements.

Pour reproduire plus fidèlement les études fiscales sur les entreprises multi-sites ou les zones d’entreprise, il faudrait obtenir les données d’établissement, les frontières des zones et les dates/règles de traitement correspondantes. Le jeu actuel de rendements boursiers ne convient pas à ces questions. Aucune des études externes ci-dessus ne transforme les estimations locales en preuve d’un effet causal mondial.

### Références principales

- Giroud, X. et Rauh, J. (2019), [*State Taxation and the Reallocation of Business Activity: Evidence from Establishment-Level Data*](https://www.nber.org/papers/w21534).
- Neumark, D. et Kolko, J. (2010), [*Do Enterprise Zones Create Jobs? Evidence from California’s Enterprise Zone Program*](https://www.nber.org/papers/w14530).
- Jardim, E. et al. (2017), [*Minimum Wage Increases, Wages, and Low-Wage Employment: Evidence from Seattle*](https://www.nber.org/papers/w23532).
- Card, D. et Krueger, A. (1993), [*Minimum Wages and Employment: A Case Study of the Fast Food Industry in New Jersey and Pennsylvania*](https://www.nber.org/papers/w4509).
