#set document(title: "Nowcaster le PIB canadien : le pont mensuel bat l'autorégression, le bloc américain n'ajoute rien", author: "Guillaume Vaudescal")
#set page(
  paper: "a4",
  margin: (x: 2.2cm, y: 2.4cm),
  numbering: "1 / 1",
  footer: context [
    #set text(size: 8pt, fill: luma(90))
    #grid(columns: (1fr, auto), align: (left, right),
      [nowcast-canada], [#counter(page).display("1 / 1", both: true)])
  ],
)
#set text(font: ("Helvetica", "Arial", "DejaVu Sans"), size: 10pt, lang: "fr")
#set par(justify: true, leading: 0.68em, spacing: 1.1em)
#set heading(numbering: none)
#show heading.where(level: 2): it => block(above: 1.6em, below: 0.8em, text(size: 13pt, it))
#show heading.where(level: 3): it => block(above: 1.2em, below: 0.6em, text(size: 11pt, it))
#show raw.where(block: true): it => block(
  fill: luma(246), inset: 8pt, radius: 3pt, width: 100%, text(size: 8.5pt, it))
#show raw.where(block: false): it => text(size: 9pt, fill: rgb("#1a3f66"), it)
#show quote.where(block: true): it => block(
  inset: (left: 10pt), stroke: (left: 1.5pt + luma(180)),
  text(style: "italic", fill: luma(45), it.body))
#show table: it => block(above: 1.1em, below: 1.1em,
  par(justify: false, text(size: 8.8pt, it)))
#show figure: it => block(above: 1.4em, below: 1.4em, it)
#show figure.caption: it => text(size: 8.5pt, fill: luma(70), it)
#show link: it => text(fill: rgb("#0072B2"), it)

#align(center)[
  #block(width: 100%)[
    #text(size: 18pt, weight: "bold")[Nowcaster le PIB canadien : le pont mensuel bat l'autorégression, le bloc américain n'ajoute rien]
    #v(0.6em)
    #text(size: 10pt, fill: luma(70))[Guillaume Vaudescal · 2026-08-29 · #link("https://github.com/Guilou001/07-nowcast-pib-canada")[Guilou001/07-nowcast-pib-canada]]
  ]
]
#v(1.2em)
#line(length: 100%, stroke: 0.6pt + luma(190))
#v(0.8em)

Le PIB trimestriel canadien arrive avec deux mois de retard ; ce dépôt le prévoit pendant le trimestre même, avec l'information réellement disponible à chaque date, et mesure qui de l'autorégression, du PIB mensuel, des 400 séries de la LCDMA ou de l'apprentissage machine fait le meilleur travail.

Le même contenu en PDF : #link("rapport/rapport.pdf")[rapport/rapport.pdf].

*Résultat en une phrase.* Sur 52 trimestres hors échantillon (2011-2023), le modèle bridge, la simple agrégation du PIB mensuel par industrie, *réduit l'erreur de prévision de 57 % par rapport à l'autorégression au troisième mois du trimestre* (ratio de RMSFE 0,43, p de Diebold-Mariano 0,027, hors COVID) ; le modèle sur les 400 séries de la LCDMA fait PIRE que l'autorégression au même mois (ratio 1,09), et le bloc américain de FRED-MD dégrade fortement le premier mois (1,71 contre 1,22).

_English summary._ Pseudo real-time nowcasting of Canadian quarterly GDP growth, 2011-2023, with publication lags enforced at every date: an AR benchmark, a monthly-GDP bridge, principal-component factors from the LCDMA panel (one PCA per forecast origin, Stock-Watson style), elastic net and random forest, plus a US-block test with FRED-MD factors. Measured verdict: the humble bridge cuts RMSFE by 57 % versus the AR by month 3 (ratio 0.43, DM p = 0.027, ex-COVID); the 400-series factor model does WORSE than the AR at that same month (ratio 1.09), and the US block sharply hurts month 1 (1.71 vs 1.22). A #raw("ncc report") command produces the current-quarter nowcast from fresh Statistics Canada data.

== 1. La question posée

Un nowcast, une prévision du trimestre EN COURS faite avant sa publication officielle, est le pain quotidien des banques centrales : la Banque du Canada décide en octobre avec un PIB officiel arrêté en juin. En mots simples : peut-on deviner la croissance du trimestre où l'on se trouve, en n'utilisant que ce qui est déjà publié, et qu'est-ce qui aide le plus, le passé du PIB lui-même, le PIB mensuel par industrie, un grand panel de 400 indicateurs, ou des modèles d'apprentissage machine ? Et la question de Chernis et Sekkel (2017), reposée dix ans plus tard : les données américaines améliorent-elles le nowcast canadien ?

== 2. D'où vient le projet, et ce qu'il apporte

Le nowcasting moderne date de Giannone, Reichlin et Small (2008) ; pour le Canada, Chernis et Sekkel (2017) ont montré qu'un modèle à facteurs dynamiques battait les références et que le bloc américain aidait. Le panel utilisé ici est la LCDMA (Fortin-Gagnon, Leroux, Stevanovic et Surprenant, 2022), le grand panel mensuel canadien, et son pendant américain FRED-MD (McCracken et Ng, 2016). Ce que ce dépôt apporte :

- *Les délais de publication imposés partout.* À chaque date de nowcast, chaque modèle ne voit

que le panel arrêté deux mois plus tôt et le dernier PIB réellement publié à cette date ; un test choque les mois postérieurs à la coupure et vérifie qu'aucune prévision ne bouge.

- *La même table d'information pour tous les modèles*, du plus simple au plus riche : la

comparaison mesure l'apport des données et des méthodes, pas des différences de protocole.

- *Des verdicts mesurés qui contrarient l'intuition* : le pont mensuel bat le panel de 400 séries,

qui fait pire que l'autorégression au mois 3, et le gain américain de 2017 ne se retrouve pas sur ce protocole.

- *Un nowcast du trimestre en cours régénérable en une commande*, sur données fraîches de l'API

de Statistique Canada.

== 3. Les données, leurs délais, leurs licences

#table(
  columns: 4,
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
  align: left + top,
  inset: 5pt,
    [*Source*],
    [*Contenu*],
    [*Délai imposé*],
    [*Licence et accès*],
    [Statistique Canada, table 36-10-0104 (v62305752)],
    [PIB trimestriel réel, prix du marché, enchaîné 2017, désaisonnalisé au taux annuel : la cible],
    [publié 2 mois après la fin du trimestre],
    [licence ouverte, API, #raw("ncc fetch")],
    [Statistique Canada, table 36-10-0434 (v65201210)],
    [PIB mensuel réel par industrie, depuis 1997],
    [2 mois],
    [licence ouverte, API, #raw("ncc fetch")],
    [LCDMA (CAN-MD)],
    [410 séries mensuelles canadiennes depuis 1981],
    [2 mois, uniforme et conservateur (déclaré)],
    [non commerciale : dépôt MANUEL dans #raw("data/raw/"), jamais commité ; millésimes publics sur #link("https://borealisdata.ca/dataset.xhtml?persistentId=doi:10.5683/SP3/59JYPU")[Borealis] jusqu'en 2021-08 ; snapshot utilisé arrêté à 2024-04, date dans le nom du fichier],
    [FRED-MD],
    [126 séries mensuelles américaines],
    [2 mois],
    [dépôt manuel, snapshot 2024-05],
)

La cible est la croissance trimestrielle annualisée en pourcent, la convention nord-américaine : +2 % signifie « si ce rythme durait un an, le PIB gagnerait 2 % ». Le millésime du PIB est le millésime FINAL, pas celui de l'époque : le protocole est un pseudo temps réel (délais respectés, révisions non modélisées), la différence avec le vrai temps réel est déclarée en limites.

== 4. La méthode, pas à pas

Chaque trimestre T est nowcasté trois fois : à la fin de son mois 1, de son mois 2 et de son mois

+ À chaque date, l'ensemble d'information contient le panel mensuel arrêté deux mois plus tôt, et

le dernier trimestre de PIB publié (T-2 au mois 1, T-1 ensuite). Fenêtre extensible : tout se réestime à chaque date, l'évaluation commence en 2011T1. Les cinq modèles :

+ *AR*, l'autorégression : le PIB expliqué par ses deux derniers trimestres publiés. C'est la référence à battre, et elle est difficile à battre au mois 1.
+ *Bridge* : le PIB mensuel par industrie, moyenné par trimestre (les mois manquants prolongés par une autorégression mensuelle), puis converti en croissance trimestrielle ; une régression relie cette croissance mensuelle agrégée à la cible.
+ *Facteurs* : les dix composantes principales de la LCDMA, les quelques forces communes qui résument le panel, dans une régression linéaire avec le bridge et le dernier PIB connu. Une SEULE analyse en composantes principales par origine de prévision (Stock et Watson, 2002) : les lignes historiques de la régression lisent toutes ce même ajustement, sans quoi le signe et l'ordre des composantes, arbitraires d'un ajustement à l'autre, brouilleraient les colonnes. Seules les séries encore observées à la coupure entrent dans l'analyse.
+ *Elastic net* : la même table de traits, avec une pénalité qui rétrécit les coefficients inutiles, choisie par validation croisée temporelle dans la fenêtre d'entraînement.
+ *Forêt aléatoire* : la même table, sans hypothèse de linéarité (500 arbres, réglages fixes).

La variante « facteurs + bloc américain » ajoute cinq composantes principales de FRED-MD : c'est le test de Chernis et Sekkel. Le juge est le RMSFE, la racine de l'erreur quadratique moyenne de prévision, en ratio sur celle de l'AR (moins de 1 = mieux que l'AR), avec le test de Diebold-Mariano, qui dit si l'écart entre deux modèles dépasse ce que le hasard produirait.

== 5. Les résultats : le pont mensuel gagne, le panel et le bloc américain déçoivent (mesuré)

Tous les chiffres viennent de #raw("results/tables/rmsfe_hors_covid.csv") et #raw("rmsfe.csv"), régénérés par #raw("uv run ncc backtest") ; 52 trimestres, 936 nowcasts, hors COVID = sans 2020T1 à 2020T3.

#table(
  columns: 5,
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
  align: left + top,
  inset: 5pt,
    [*Modèle*],
    [*Mois 1*],
    [*Mois 2*],
    [*Mois 3*],
    [*p DM (mois 3)*],
    [Bridge PIB mensuel],
    [0,87],
    [0,76],
    [*0,43*],
    [*0,027*],
    [Forêt aléatoire],
    [1,00],
    [0,92],
    [0,56],
    [0,022],
    [Elastic net],
    [1,09],
    [0,86],
    [0,94],
    [0,652],
    [Facteurs LCDMA],
    [1,22],
    [0,91],
    [1,09],
    [0,621],
    [Facteurs + bloc américain],
    [1,71],
    [0,89],
    [0,89],
    [0,392],
)

Comment lire ce tableau, en trois constats (les cellules sont des ratios de RMSFE sur l'AR, hors COVID). D'abord, l'information mensuelle paie au fil du trimestre, mais seulement quand le canal est direct : au mois 3, le bridge enlève 57 % de l'erreur de l'AR (1,24 point de croissance annualisée contre 2,90, mesuré dans le même fichier) et la forêt, dont la table de traits contient le bridge, 44 % ; ce sont les deux seuls écarts statistiquement nets du tableau. Ensuite, le grand panel déçoit : le modèle à facteurs fait PIRE que l'AR aux mois 1 et 3, et l'elastic net ne rattrape presque rien ; 400 séries résumées en dix composantes n'ajoutent rien que le PIB mensuel ne dise déjà, en cohérence avec la leçon des autres dépôts du portfolio. Enfin, le bloc américain est à double tranchant : il aggrave nettement le mois 1 (1,71 contre 1,22, la composante américaine ajoute du bruit quand l'information canadienne est rare) et adoucit le mois 3 (0,89 contre 1,09) sans jamais approcher le bridge seul ; le gain net de Chernis et Sekkel (2017), obtenu en vrai temps réel avec un modèle à facteurs dynamiques, ne se retrouve pas sur ce protocole, et l'écart de protocole est déclaré plutôt que masqué.

#figure(image("../results/figures/nowcast_vs_realise.png", width: 100%), caption: [Nowcast contre réalisé])

Comment lire cette figure : le trait noir est la croissance réalisée, les deux courbes les nowcasts du mois 3 ; la courbe bleue (AR) rate 2020 dans les deux sens, d'abord aveugle à la chute puis aveugle au rebond, tandis que le bridge (vermillon) voit les deux, en amplifiant la chute (−78,7 pour un réalisé de −37,3 % annualisé au 2020T2) et en sous-estimant le rebond (+25,0 pour +41,6 au 2020T3). La forêt aléatoire, absente de la figure, dit −2,2 au 2020T2 : un modèle d'arbres ne peut pas prédire en dehors de la plage qu'il a vue à l'entraînement, et 2020 était hors de toute plage.

#figure(image("../results/figures/rmsfe_par_mois.png", width: 100%), caption: [RMSFE par mois d'information])

Comment lire cette figure : chaque groupe de barres est un modèle, chaque barre un mois du trimestre, la hauteur le ratio de RMSFE sur l'AR hors COVID ; sous la ligne pointillée, le modèle bat l'AR. Les barres du bridge et de la forêt descendent nettement du mois 1 au mois 3, celles des modèles à facteurs restent autour de la ligne : c'est l'arrivée des données mensuelles de PIB qui crée le nowcast, pas la taille du panel.

#figure(image("../results/figures/bloc_americain.png", width: 100%), caption: [Le bloc américain])

Comment lire cette figure : à chaque mois du trimestre, la barre verte est le modèle à facteurs canadien, la vermillon le même modèle avec cinq facteurs américains de FRED-MD en plus. La vermillon dépasse largement la verte au mois 1 et passe dessous aux mois 2 et 3, sans jamais descendre au niveau du bridge seul (0,43) : le bloc américain déplace du bruit plus qu'il n'apporte du signal.

Avec la COVID incluse (#raw("rmsfe.csv")), les ratios des modèles à données mensuelles s'écrasent au mois 2 (0,35 à 0,51, contre 0,84 pour la forêt qui ne sait pas extrapoler) : trois trimestres extrêmes dominent toute somme de carrés, c'est précisément pourquoi les deux tableaux sont publiés.

== 6. Le nowcast du trimestre en cours, en une commande

#raw("uv run ncc report") interroge l'API de Statistique Canada et produit le nowcast du trimestre en cours par l'AR et le bridge (les deux modèles qui ne demandent aucun dépôt manuel). Sortie du 28 août 2026, mesurée : trimestre visé 2026T3, information du mois 2, *bridge +2,2 %* et AR +3,0 % en taux annualisé, dernier trimestre publié 2026T2 à +3,3 %.

== 7. Reproduire

#raw("uv sync --locked --all-extras     # environnement verrouillé (Python 3.12, scikit-learn, pandas 3)\nuv run pytest                     # 8 tests synthétiques, sans réseau (calendrier, AR, bridge, fuite, DM)\nuv run ncc fetch                  # PIB trimestriel et mensuel par l'API de Statistique Canada\n# déposer CAN_MD (LCDMA) et FRED-MD dans data/raw/ (voir section 3, licences non commerciales)\nuv run ncc backtest               # 936 nowcasts, tables + 3 figures (35 s mesurées)\nuv run ncc report                 # le nowcast du trimestre en cours (PIB seulement, sans dépôt manuel)", block: true, lang: "bash")

== 8. Limites, avec leur statut

#table(
  columns: 2,
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
  align: left + top,
  inset: 5pt,
    [*Limite*],
    [*Statut*],
    [Pseudo temps réel : délais de publication imposés, mais millésime FINAL du PIB et du panel (les révisions ne sont pas modélisées) ; les vrais millésimes LCDMA 2019-2021 de Borealis permettraient une évaluation en vrai temps réel],
    [déclaré ; extension naturelle],
    [Le snapshot LCDMA s'arrête en 2024-04, l'évaluation en 2023T4 ; le nowcast courant (section 6) n'utilise que l'API],
    [mesuré et déclaré],
    [Délai uniforme de 2 mois pour tout le panel, conservateur (l'emploi sort à 1 mois, les marchés à 0) : le vrai calendrier série par série affinerait les mois 1 et 2],
    [choix déclaré],
    [Pas de modèle à facteurs dynamiques à fréquences mixtes (le DFM de Chernis-Sekkel) : la comparaison avec leur résultat est indicative, pas une réplication],
    [reconnu ; c'est la suite logique du dépôt],
    [Stationnarisation de la LCDMA par une règle simple (différence de log si positif, différence sinon) au lieu des codes officiels du fichier de description],
    [approximation déclarée],
    [Les trous restants du panel (après retrait des séries discontinuées à la coupure) sont imputés à la moyenne via la standardisation ; moins de 0,1 % des cellules],
    [choix déclaré],
    [La cible est le PIB aux prix du marché (dépenses) alors que le bridge agrège le PIB par industrie (production) : l'écart conceptuel entre les deux mesures est ignoré],
    [reconnu, standard dans la littérature bridge],
)

== 9. Crédits, licence, citation

Giannone, D., Reichlin, L. et Small, D. (2008), « Nowcasting: The real-time informational content of macroeconomic data » ; Chernis, T. et Sekkel, R. (2017), « A dynamic factor model for nowcasting Canadian GDP growth » ; Fortin-Gagnon, O., Leroux, M., Stevanovic, D. et Surprenant, S. (2022), « A large Canadian database for macroeconomic analysis » ; McCracken, M. et Ng, S. (2016), « FRED-MD » ; Diebold, F. et Mariano, R. (1995) ; Harvey, D., Leybourne, S. et Newbold, P. (1997). Données : Statistique Canada (licence ouverte), LCDMA et FRED-MD (non commerciales, jamais redistribuées ici). Code : Guillaume Vaudescal, 2026, licence MIT.
