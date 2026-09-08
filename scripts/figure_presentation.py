"""Draw the README figure from published results, without rerunning the study.

Run from the repository with ``uv run python scripts/figure_presentation.py``.
The input tables remain the numerical source of truth.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]
BLUE, ORANGE, GREEN, GREY = "#176B96", "#C56628", "#14816D", "#718096"
plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 15,
        "axes.labelsize": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#CBD5E0",
        "text.color": "#172B3A",
        "axes.labelcolor": "#172B3A",
        "xtick.color": "#425466",
        "ytick.color": "#425466",
        "axes.axisbelow": True,
    }
)


def number(value, decimals=2):
    return f"{value:,.{decimals}f}".replace(",", " ").replace(".", ",")


def finish(fig, axes, title, note, path="results/figures/presentation.png"):
    for ax in np.asarray(axes, dtype=object).ravel():
        ax.grid(axis="x", color="#EDF0F3", linewidth=0.8)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}".replace(".", ",")))
    fig.suptitle(title, x=0.02, ha="left", fontweight="bold", fontsize=16)
    fig.text(0.02, 0.015, note, ha="left", va="bottom", fontsize=9, color="#526575")
    fig.tight_layout(rect=(0, 0.075, 1, 0.91))
    destination = ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    d = pd.read_csv(ROOT / "results/tables/rmsfe_hors_covid.csv")
    keys = ["bridge", "facteurs", "facteurs_plus_us"]
    labels = ["PIB mensuel", "Nombreux indicateurs canadiens", "Indicateurs canadiens et américains"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 5), sharex=True, sharey=True)
    for month, ax in enumerate(axes, start=1):
        row = d[d.mois == month].set_index("modele")
        values = row.loc[keys, "ratio_ar"].to_numpy()
        ax.barh([2, 1, 0], values, color=[BLUE, GREY, ORANGE], height=0.55)
        ax.axvline(1, color="#425466", linestyle="--", linewidth=1)
        for y, v in zip([2, 1, 0], values, strict=True):
            ax.text(v + 0.04, y, number(v), va="center", fontsize=10)
        ax.set_yticks([2, 1, 0], labels)
        ax.set_xlim(0, 2)
        ax.set_title(f"Mois {month} du trimestre", fontsize=12)
        ax.set_xlabel("Erreur relative au modèle simple")
    finish(
        fig,
        axes,
        "L'information mensuelle sur le PIB améliore la prévision",
        "Canada · 2011 à 2023, hors les trois premiers trimestres de 2020 · 49 trimestres évalués\n"
        "Sous 1 signifie une erreur plus faible. Historiques révisés et délais de disponibilité simulés.",
    )


if __name__ == "__main__":
    main()
