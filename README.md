# Prévoir le PIB canadien avant sa publication

Le produit intérieur brut trimestriel décrit l'évolution de l'économie canadienne, mais il est publié avec retard. Lorsqu'un trimestre se termine, les décideurs doivent donc agir avant de connaître sa croissance officielle. Le présent projet cherche à produire une estimation pendant le trimestre en utilisant seulement l'information disponible à chaque date.

Nous comparons une prévision fondée sur le passé du PIB à des modèles qui ajoutent le PIB mensuel, environ 400 séries canadiennes et un ensemble de données américaines. Cette comparaison est menée comme elle l'aurait été en temps réel : une série publiée trop tard n'entre pas dans la prévision.

**Résultat principal.** Sur 52 trimestres de 2011 à 2023, le modèle qui agrège le PIB mensuel réduit l'erreur de 57 % au troisième mois du trimestre, comparativement au modèle autorégressif. L'écart reste statistiquement mesurable lorsque la période de la pandémie est retirée, avec une probabilité critique de 0,027. En revanche, le modèle alimenté par les 400 séries canadiennes fait légèrement pire que la référence, et l'ajout du bloc américain dégrade fortement la prévision du premier mois.

Afin de comprendre ce résultat, nous présenterons d'abord le calendrier de publication des données. Dans un deuxième temps, nous expliquerons les modèles et la manière dont chaque prévision respecte ce calendrier. Ensuite, nous comparerons leurs erreurs selon le mois du trimestre et la période étudiée. Enfin, nous montrerons comment produire l'estimation courante, puis nous présenterons les limites et les commandes de reproduction.

[![ci](https://github.com/Guilou001/07-nowcast-pib-canada/actions/workflows/ci.yml/badge.svg)](https://github.com/Guilou001/07-nowcast-pib-canada/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.12-blue)
![licence](https://img.shields.io/badge/code-MIT-green)

Le même contenu en PDF : [rapport/rapport.pdf](rapport/rapport.pdf).

<details>
<summary>Résumé en anglais</summary>

*English summary.* Pseudo real-time nowcasting of Canadian quarterly GDP growth, 2011-2023, with
publication lags enforced at every date: an AR benchmark, a monthly-GDP bridge, principal-component
factors from the LCDMA panel (one PCA per forecast origin, Stock-Watson style), elastic net and
random forest, plus a US-block test with FRED-MD factors. Measured verdict: the humble bridge cuts
RMSFE by 57 % versus the AR by month 3 (ratio 0.43, DM p = 0.027, ex-COVID); the 400-series factor
model does WORSE than the AR at that same month (ratio 1.09), and the US block sharply hurts month 1
(1.71 vs 1.22). A `ncc report` command produces the current-quarter nowcast from fresh Statistics
Canada data.

</details>
## 1. La question en détail

Un nowcast, une prévision du trimestre EN COURS faite avant sa publication officielle, est le pain
quotidien des banques centrales : la Banque du Canada décide en octobre avec un PIB officiel arrêté
en juin. En mots simples : peut-on deviner la croissance du trimestre où l'on se trouve, en
n'utilisant que ce qui est déjà publié, et qu'est-ce qui aide le plus, le passé du PIB lui-même, le
PIB mensuel par industrie, un grand panel de 400 indicateurs, ou des modèles d'apprentissage
machine ? Et la question de Chernis et Sekkel (2017), reposée dix ans plus tard : les données
américaines améliorent-elles le nowcast canadien ?

## 2. D'où vient le projet, et ce qu'il apporte

Le nowcasting moderne date de Giannone, Reichlin et Small (2008) ; pour le Canada, Chernis et
Sekkel (2017) ont montré qu'un modèle à facteurs dynamiques battait les références et que le bloc
américain aidait. Le panel utilisé ici est la LCDMA (Fortin-Gagnon, Leroux, Stevanovic et
Surprenant, 2022), le grand panel mensuel canadien, et son pendant américain FRED-MD (McCracken et
Ng, 2016). Ce que ce dépôt apporte :

- **Les délais de publication imposés partout.** À chaque date de nowcast, chaque modèle ne voit
  que le panel arrêté deux mois plus tôt et le dernier PIB réellement publié à cette date ; un test
  choque les mois postérieurs à la coupure et vérifie qu'aucune prévision ne bouge.
- **La même table d'information pour tous les modèles**, du plus simple au plus riche : la
  comparaison mesure l'apport des données et des méthodes, pas des différences de protocole.
- **Des verdicts mesurés qui contrarient l'intuition** : le pont mensuel bat le panel de 400 séries,
  qui fait pire que l'autorégression au mois 3, et le gain américain de 2017 ne se retrouve pas sur
  ce protocole.
- **Un nowcast du trimestre en cours régénérable en une commande**, sur données fraîches de l'API
  de Statistique Canada.

## 3. Les données, leurs délais, leurs licences

| Source | Contenu | Délai imposé | Licence et accès |
|---|---|---|---|
| Statistique Canada, table 36-10-0104 (v62305752) | PIB trimestriel réel, prix du marché, enchaîné 2017, désaisonnalisé au taux annuel : la cible | publié 2 mois après la fin du trimestre | licence ouverte, API, `ncc fetch` |
| Statistique Canada, table 36-10-0434 (v65201210) | PIB mensuel réel par industrie, depuis 1997 | 2 mois | licence ouverte, API, `ncc fetch` |
| LCDMA (CAN-MD) | 410 séries mensuelles canadiennes depuis 1981 | 2 mois, uniforme et conservateur (déclaré) | non commerciale : dépôt MANUEL dans `data/raw/`, jamais commité ; millésimes publics sur [Borealis](https://borealisdata.ca/dataset.xhtml?persistentId=doi:10.5683/SP3/59JYPU) jusqu'en 2021-08 ; snapshot utilisé arrêté à 2024-04, date dans le nom du fichier |
| FRED-MD | 126 séries mensuelles américaines | 2 mois | dépôt manuel, snapshot 2024-05 |

La cible est la croissance trimestrielle annualisée en pourcent, la convention nord-américaine :
+2 % signifie « si ce rythme durait un an, le PIB gagnerait 2 % ». Le millésime du PIB est le
millésime FINAL, pas celui de l'époque : le protocole est un pseudo temps réel (délais respectés,
révisions non modélisées), la différence avec le vrai temps réel est déclarée en limites.

## 4. La méthode, pas à pas

Chaque trimestre T est nowcasté trois fois : à la fin de son mois 1, de son mois 2 et de son mois
3. À chaque date, l'ensemble d'information contient le panel mensuel arrêté deux mois plus tôt, et
le dernier trimestre de PIB publié (T-2 au mois 1, T-1 ensuite). Fenêtre extensible : tout se
réestime à chaque date, l'évaluation commence en 2011T1. Les cinq modèles :

1. **AR**, l'autorégression : le PIB expliqué par ses deux derniers trimestres publiés. C'est la
   référence à battre, et elle est difficile à battre au mois 1.
2. **Bridge** : le PIB mensuel par industrie, moyenné par trimestre (les mois manquants prolongés
   par une autorégression mensuelle), puis converti en croissance trimestrielle ; une régression
   relie cette croissance mensuelle agrégée à la cible.
3. **Facteurs** : les dix composantes principales de la LCDMA, les quelques forces communes qui
   résument le panel, dans une régression linéaire avec le bridge et le dernier PIB connu. Une
   SEULE analyse en composantes principales par origine de prévision (Stock et Watson, 2002) :
   les lignes historiques de la régression lisent toutes ce même ajustement, sans quoi le signe et
   l'ordre des composantes, arbitraires d'un ajustement à l'autre, brouilleraient les colonnes.
   Seules les séries encore observées à la coupure entrent dans l'analyse.
4. **Elastic net** : la même table de traits, avec une pénalité qui rétrécit les coefficients
   inutiles, choisie par validation croisée temporelle dans la fenêtre d'entraînement.
5. **Forêt aléatoire** : la même table, sans hypothèse de linéarité (500 arbres, réglages fixes).

La variante « facteurs + bloc américain » ajoute cinq composantes principales de FRED-MD : c'est le
test de Chernis et Sekkel. Le juge est le RMSFE, la racine de l'erreur quadratique moyenne de
prévision, en ratio sur celle de l'AR (moins de 1 = mieux que l'AR), avec le test de
Diebold-Mariano, qui dit si l'écart entre deux modèles dépasse ce que le hasard produirait.

## 5. Les résultats : le pont mensuel gagne, le panel et le bloc américain déçoivent (mesuré)

Tous les chiffres viennent de `results/tables/rmsfe_hors_covid.csv` et `rmsfe.csv`, régénérés par
`uv run ncc backtest` ; 52 trimestres, 936 nowcasts, hors COVID = sans 2020T1 à 2020T3.

| Modèle | Mois 1 | Mois 2 | Mois 3 | p DM (mois 3) |
|---|---:|---:|---:|---:|
| Bridge PIB mensuel | 0,87 | 0,76 | **0,43** | **0,027** |
| Forêt aléatoire | 1,00 | 0,92 | 0,56 | 0,022 |
| Elastic net | 1,09 | 0,86 | 0,94 | 0,652 |
| Facteurs LCDMA | 1,22 | 0,91 | 1,09 | 0,621 |
| Facteurs + bloc américain | 1,71 | 0,89 | 0,89 | 0,392 |

Comment lire ce tableau, en trois constats (les cellules sont des ratios de RMSFE sur l'AR, hors
COVID). D'abord, l'information mensuelle paie au fil du trimestre, mais seulement quand le canal
est direct : au mois 3, le bridge enlève 57 % de l'erreur de l'AR (1,24 point de croissance
annualisée contre 2,90, mesuré dans le même fichier) et la forêt, dont la table de traits contient
le bridge, 44 % ; ce sont les deux seuls écarts statistiquement nets du tableau. Ensuite, le grand
panel déçoit : le modèle à facteurs fait PIRE que l'AR aux mois 1 et 3, et l'elastic net ne
rattrape presque rien ; 400 séries résumées en dix composantes n'ajoutent rien que le PIB mensuel
ne dise déjà, en cohérence avec la leçon des autres dépôts du portfolio. Enfin, le bloc américain
est à double tranchant : il aggrave nettement le mois 1 (1,71 contre 1,22, la composante
américaine ajoute du bruit quand l'information canadienne est rare) et adoucit le mois 3 (0,89
contre 1,09) sans jamais approcher le bridge seul ; le gain net de Chernis et Sekkel (2017),
obtenu en vrai temps réel avec un modèle à facteurs dynamiques, ne se retrouve pas sur ce
protocole, et l'écart de protocole est déclaré plutôt que masqué.

![Nowcast contre réalisé](results/figures/nowcast_vs_realise.png)

Comment lire cette figure : le trait noir est la croissance réalisée, les deux courbes les
nowcasts du mois 3 ; la courbe bleue (AR) rate 2020 dans les deux sens, d'abord aveugle à la chute
puis aveugle au rebond, tandis que le bridge (vermillon) voit les deux, en amplifiant la chute
(−78,7 pour un réalisé de −37,3 % annualisé au 2020T2) et en sous-estimant le rebond (+25,0 pour
+41,6 au 2020T3). La forêt aléatoire, absente de la figure, dit −2,2 au 2020T2 : un modèle
d'arbres ne peut pas prédire en dehors de la plage qu'il a vue à l'entraînement, et 2020 était
hors de toute plage.

![RMSFE par mois d'information](results/figures/rmsfe_par_mois.png)

Comment lire cette figure : chaque groupe de barres est un modèle, chaque barre un mois du
trimestre, la hauteur le ratio de RMSFE sur l'AR hors COVID ; sous la ligne pointillée, le modèle
bat l'AR. Les barres du bridge et de la forêt descendent nettement du mois 1 au mois 3, celles des
modèles à facteurs restent autour de la ligne : c'est l'arrivée des données mensuelles de PIB qui
crée le nowcast, pas la taille du panel.

![Le bloc américain](results/figures/bloc_americain.png)

Comment lire cette figure : à chaque mois du trimestre, la barre verte est le modèle à facteurs
canadien, la vermillon le même modèle avec cinq facteurs américains de FRED-MD en plus. La
vermillon dépasse largement la verte au mois 1 et passe dessous aux mois 2 et 3, sans jamais
descendre au niveau du bridge seul (0,43) : le bloc américain déplace du bruit plus qu'il
n'apporte du signal.

Avec la COVID incluse (`rmsfe.csv`), les ratios des modèles à données mensuelles s'écrasent au
mois 2 (0,35 à 0,51, contre 0,84 pour la forêt qui ne sait pas extrapoler) : trois trimestres
extrêmes dominent toute somme de carrés, c'est précisément pourquoi les deux tableaux sont
publiés.

## 6. Le nowcast du trimestre en cours, en une commande

`uv run ncc report` interroge l'API de Statistique Canada et produit le nowcast du trimestre en
cours par l'AR et le bridge (les deux modèles qui ne demandent aucun dépôt manuel). Sortie du
28 août 2026, mesurée : trimestre visé 2026T3, information du mois 2, **bridge +2,2 %** et AR
+3,0 % en taux annualisé, dernier trimestre publié 2026T2 à +3,3 %.

## 7. Reproduire

```bash
uv sync --locked --all-extras     # environnement verrouillé (Python 3.12, scikit-learn, pandas 3)
uv run pytest                     # 8 tests synthétiques, sans réseau (calendrier, AR, bridge, fuite, DM)
uv run ncc fetch                  # PIB trimestriel et mensuel par l'API de Statistique Canada
# déposer CAN_MD (LCDMA) et FRED-MD dans data/raw/ (voir section 3, licences non commerciales)
uv run ncc backtest               # 936 nowcasts, tables + 3 figures (35 s mesurées)
uv run ncc report                 # le nowcast du trimestre en cours (PIB seulement, sans dépôt manuel)
```

## 8. Limites, avec leur statut

| Limite | Statut |
|---|---|
| Pseudo temps réel : délais de publication imposés, mais millésime FINAL du PIB et du panel (les révisions ne sont pas modélisées) ; les vrais millésimes LCDMA 2019-2021 de Borealis permettraient une évaluation en vrai temps réel | déclaré ; extension naturelle |
| Le snapshot LCDMA s'arrête en 2024-04, l'évaluation en 2023T4 ; le nowcast courant (section 6) n'utilise que l'API | mesuré et déclaré |
| Délai uniforme de 2 mois pour tout le panel, conservateur (l'emploi sort à 1 mois, les marchés à 0) : le vrai calendrier série par série affinerait les mois 1 et 2 | choix déclaré |
| Pas de modèle à facteurs dynamiques à fréquences mixtes (le DFM de Chernis-Sekkel) : la comparaison avec leur résultat est indicative, pas une réplication | reconnu ; c'est la suite logique du dépôt |
| Stationnarisation de la LCDMA par une règle simple (différence de log si positif, différence sinon) au lieu des codes officiels du fichier de description | approximation déclarée |
| Les trous restants du panel (après retrait des séries discontinuées à la coupure) sont imputés à la moyenne via la standardisation ; moins de 0,1 % des cellules | choix déclaré |
| La cible est le PIB aux prix du marché (dépenses) alors que le bridge agrège le PIB par industrie (production) : l'écart conceptuel entre les deux mesures est ignoré | reconnu, standard dans la littérature bridge |

## 9. Crédits, licence, citation

Giannone, D., Reichlin, L. et Small, D. (2008), « Nowcasting: The real-time informational content
of macroeconomic data » ; Chernis, T. et Sekkel, R. (2017), « A dynamic factor model for nowcasting
Canadian GDP growth » ; Fortin-Gagnon, O., Leroux, M., Stevanovic, D. et Surprenant, S. (2022),
« A large Canadian database for macroeconomic analysis » ; McCracken, M. et Ng, S. (2016),
« FRED-MD » ; Diebold, F. et Mariano, R. (1995) ; Harvey, D., Leybourne, S. et Newbold, P. (1997).
Données : Statistique Canada (licence ouverte), LCDMA et FRED-MD (non commerciales, jamais
redistribuées ici). Code : Guillaume Vaudescal, 2026, licence MIT.
