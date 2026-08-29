"""Trois figures : le nowcast contre le réalisé, le RMSFE par mois d'information, le bloc américain.

Style commun au portfolio : palette d'Okabe et Ito, axes étiquetés, virgule décimale, 200 ppp.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OKABE_ITO = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]
LABELS = {"ar": "AR (référence)", "bridge": "Bridge PIB mensuel", "facteurs": "Facteurs LCDMA",
          "elastic_net": "Elastic net", "foret": "Forêt aléatoire",
          "facteurs_plus_us": "Facteurs + bloc américain"}


def use_style():
    import matplotlib as mpl
    from cycler import cycler
    from matplotlib.ticker import FuncFormatter

    mpl.rcParams.update({
        "figure.dpi": 200, "savefig.dpi": 200, "figure.constrained_layout.use": True,
        "font.size": 11, "axes.titlesize": 12, "axes.prop_cycle": cycler(color=OKABE_ITO),
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.3, "grid.linewidth": 0.5,
        "legend.frameon": False, "lines.linewidth": 1.6,
    })
    return FuncFormatter(lambda v, _: f"{v:g}".replace(".", ","))


def fig_nowcast_vs_realise(results: pd.DataFrame, dest: Path) -> None:
    """Le réalisé contre deux nowcasts au mois 3, celui où l'information est la plus riche."""
    fr = use_style()
    sub = results[results["mois"] == 3].pivot(index="trimestre", columns="modele", values="nowcast")
    real = results[results["mois"] == 3].groupby("trimestre")["realise"].first()
    idx = pd.PeriodIndex(sub.index, freq="Q").to_timestamp()
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.plot(idx, real.to_numpy(), color="0.2", linewidth=2.0, label="Réalisé")
    ax.plot(idx, sub["ar"].to_numpy(), color=OKABE_ITO[0], linewidth=1.2, label=LABELS["ar"])
    ax.plot(idx, sub["bridge"].to_numpy(), color=OKABE_ITO[3], linewidth=1.4, label=LABELS["bridge"])
    ax.axhline(0, color="0.5", linewidth=0.7)
    ax.set_ylabel("Croissance trimestrielle annualisée (%)")
    ax.yaxis.set_major_formatter(fr)
    ax.set_title("Au mois 3, le bridge colle au PIB ; l'AR ne voit pas venir 2020")
    ax.legend(loc="lower left", fontsize=9)
    fig.savefig(dest)
    plt.close(fig)


def fig_rmsfe(summary_nc: pd.DataFrame, dest: Path) -> None:
    """Le RMSFE en ratio sur l'AR, par modèle et par mois d'information (hors COVID)."""
    fr = use_style()
    models = [m for m in LABELS if m != "ar" and m in set(summary_nc["modele"])]
    months = sorted(summary_nc["mois"].unique())
    width = 0.8 / len(months)
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    x = np.arange(len(models))
    for j, m in enumerate(months):
        vals = [float(summary_nc[(summary_nc.modele == mod) & (summary_nc.mois == m)]["ratio_ar"].iloc[0])
                for mod in models]
        ax.bar(x + (j - 1) * width, vals, width, label=f"Mois {m} du trimestre",
               color=OKABE_ITO[j])
    ax.axhline(1.0, color="0.2", linewidth=1.0, linestyle="--")
    ax.text(len(models) - 0.5, 1.0, "niveau de l'AR", ha="right", va="bottom", fontsize=8)
    ax.set_xticks(x, [LABELS[m] for m in models], fontsize=9)
    ax.set_ylabel("RMSFE / RMSFE de l'AR")
    ax.yaxis.set_major_formatter(fr)
    ax.set_title("Plus le trimestre avance, plus les données mensuelles paient (hors COVID)")
    ax.legend(fontsize=9)
    fig.savefig(dest)
    plt.close(fig)


def fig_us_block(summary_all: pd.DataFrame, summary_nc: pd.DataFrame, dest: Path) -> None:
    """L'apport du bloc américain : facteurs seuls contre facteurs plus FRED-MD, par mois."""
    fr = use_style()
    fig, ax = plt.subplots(figsize=(8, 4))
    months = sorted(summary_nc["mois"].unique())
    x = np.arange(len(months))
    for j, (label, key) in enumerate((("Facteurs LCDMA", "facteurs"),
                                      ("Facteurs + bloc américain", "facteurs_plus_us"))):
        vals = [float(summary_nc[(summary_nc.modele == key) & (summary_nc.mois == m)]["ratio_ar"].iloc[0])
                for m in months]
        ax.bar(x + (j - 0.5) * 0.35, vals, 0.35, label=label, color=OKABE_ITO[2 + j])
    ax.axhline(1.0, color="0.2", linewidth=1.0, linestyle="--")
    ax.set_xticks(x, [f"Mois {m}" for m in months])
    ax.set_ylabel("RMSFE / RMSFE de l'AR (hors COVID)")
    ax.yaxis.set_major_formatter(fr)
    ax.set_title("Le bloc américain de FRED-MD change-t-il le nowcast canadien ?")
    ax.legend(fontsize=9)
    fig.savefig(dest)
    plt.close(fig)
