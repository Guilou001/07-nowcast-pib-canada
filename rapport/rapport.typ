#set document(title: "Estimer la croissance du Canada avant la publication du chiffre officiel", author: "Guillaume Vaudescal")
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
// la table NE DOIT PAS être enfermée dans un par() : Typst 0.15 la supprime alors
// entièrement, sans erreur. Le réglage se pose donc dans la portée du bloc.
#show table: it => block(above: 1.1em, below: 1.1em,
  [#set par(justify: false); #text(size: 8.8pt, it)])
#show figure: it => block(above: 1.4em, below: 1.4em, it)
#show figure.caption: it => text(size: 8.5pt, fill: luma(70), it)
#show link: it => text(fill: rgb("#0072B2"), it)

#align(center)[
  #block(width: 100%)[
    #text(size: 18pt, weight: "bold")[Estimer la croissance du Canada avant la publication du chiffre officiel]
    #v(0.6em)
    #text(size: 10pt, fill: luma(70))[Guillaume Vaudescal · 2026-09-08 · #link("https://github.com/Guilou001/07-nowcast-pib-canada")[Guilou001/07-nowcast-pib-canada]]
  ]
]
#v(1.2em)
#line(length: 100%, stroke: 0.6pt + luma(190))
#v(0.8em)

L'activité économique du trimestre en cours n'est pas encore connue lorsque les entreprises et les banques doivent décider. Le produit intérieur brut, ou PIB, mesure la valeur de la production. Son chiffre officiel arrive avec retard.

Ce projet estime la croissance canadienne en utilisant les informations déjà publiées selon un calendrier simplifié. Il compare une règle fondée sur le passé du PIB à des modèles qui ajoutent des données mensuelles.

*Le PIB mensuel aide davantage que le grand ensemble d'indicateurs dans ce test.* Le résultat porte sur les prévisions de 2011 à 2023.

== Davantage de données ne signifie pas toujours moins d'erreur

#table(
  columns: 3,
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt) } else { none },
  align: left + top,
  inset: 5pt,
    [*Informations utilisées*],
    [*Erreur au premier mois*],
    [*Erreur au troisième mois*],
    [Passé du PIB seul, référence],
    [1,00],
    [1,00],
    [PIB mensuel ajouté],
    [0,87],
    [0,43],
    [Grand ensemble d'indicateurs canadiens],
    [1,22],
    [1,09],
    [Indicateurs canadiens et américains],
    [1,71],
    [0,89],
)

L'erreur de la référence est ramenée à 1. Une valeur de 0,43 signifie une erreur *57 % plus faible*. Cette mesure donne davantage de poids aux grosses erreurs. Les trois premiers trimestres de 2020 sont retirés de ce tableau pour éviter qu'ils dominent toute la comparaison. #link("results/tables/rmsfe_hors_covid.csv")[Données du tableau].

#figure(image("../results/figures/presentation.png", width: 100%), caption: [Erreur des modèles selon le mois du trimestre])

Les barres comparent les modèles aux trois dates de prévision. Sous la ligne de référence, l'erreur est plus faible. L'arrivée des données de PIB mensuel améliore nettement la prévision au fil du trimestre.

== Comment prévoir un trimestre incomplet

Le programme produit une estimation à la fin de chacun des trois mois. Il prolonge les mois de PIB encore inconnus, puis relie les chiffres mensuels à la croissance trimestrielle.

Les autres modèles utilisent aussi des indicateurs économiques, résumés ou sélectionnés automatiquement. Tous respectent les délais imposés par le protocole.

== Une limite importante du test historique

Les délais sont simulés, mais les valeurs économiques sont celles d'historiques révisés. Ce n'est donc pas une reconstitution exacte de tout ce qu'un prévisionniste savait à l'époque.

Le résultat ne reproduit pas à l'identique le modèle dynamique de Chernis et Sekkel. Il compare les méthodes effectivement présentes dans ce dépôt. Les résultats avec la pandémie incluse restent dans la #link("results/tables/rmsfe.csv")[table complète].

== Refaire les calculs

#raw("uv sync --locked --all-extras\nuv run ncc fetch\nuv run ncc report\nuv run pytest", block: true, lang: "bash")

Le test historique complet utilise #raw("uv run ncc backtest") après dépôt manuel des fichiers LCDMA et FRED-MD décrit dans l'étude détaillée. Le rapport courant n'a pas besoin de ces fichiers. Le graphique de présentation se régénère hors réseau avec #raw("uv run python scripts/figure_presentation.py"), depuis les tableaux publiés.

== Pour aller plus loin

#link("docs/ETUDE_DETAILLEE.md")[Méthodes, résultats complets et références] · #link("rapport/rapport.pdf")[Présentation en PDF] · #link("CITATION.cff")[Citer le projet] · #link("LICENSE")[Licence].

== English summary

Monthly GDP improves Canadian growth estimates in this pseudo real-time comparison. Revised data and simplified publication lags limit historical realism. The main table excludes the first three quarters of 2020.
