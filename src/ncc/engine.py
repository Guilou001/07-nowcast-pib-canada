"""Le protocole d'évaluation : chaque trimestre est nowcasté trois fois, aux mois 1, 2 et 3.

Fenêtre extensible : le premier nowcast tombe en 2011T1, les modèles sont réestimés à chaque date
avec l'information de l'époque, et l'évaluation court jusqu'au dernier trimestre couvert par le
panel. Le juge est le RMSFE, la racine de l'erreur quadratique moyenne de prévision, rapportée en
ratio sur l'AR (moins de 1 = mieux que l'AR), avec le test de Diebold-Mariano (correction de
Harvey) pour dire si l'écart est distinguable du hasard. La COVID écrase tout au carré : chaque
tableau existe avec et sans 2020T1-2020T3, les deux sont montrés.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from ncc.models import (
    InfoSet,
    ar_nowcast,
    bridge_nowcast,
    elastic_net_nowcast,
    factor_nowcast,
    feature_table,
    random_forest_nowcast,
)

COVID = [pd.Period(q, freq="Q") for q in ("2020Q1", "2020Q2", "2020Q3")]
FEATURE_START = pd.Period("2002Q1", freq="Q")


def run_backtest(y: pd.Series, mgdp_level: pd.Series, panel_stat: pd.DataFrame,
                 us_panel: pd.DataFrame | None, start: pd.Period, end: pd.Period,
                 log=print) -> pd.DataFrame:
    """Une ligne par (trimestre, mois d'information, modèle) : nowcast et valeur réalisée."""
    rows = []
    quarters = pd.period_range(start, end, freq="Q")
    for t in quarters:
        for m in (1, 2, 3):
            info = InfoSet(t, m)
            x, targets, x_now = feature_table(y, panel_stat, mgdp_level, info, FEATURE_START)
            preds = {
                "ar": ar_nowcast(y, info),
                "bridge": bridge_nowcast(y, mgdp_level, info),
                "facteurs": factor_nowcast(x, targets, x_now),
                "elastic_net": elastic_net_nowcast(x, targets, x_now),
                "foret": random_forest_nowcast(x, targets, x_now),
            }
            if us_panel is not None:
                x2, t2, x2_now = feature_table(y, panel_stat, mgdp_level, info, FEATURE_START,
                                               us_panel=us_panel)
                preds["facteurs_plus_us"] = factor_nowcast(x2, t2, x2_now)
            for model, value in preds.items():
                rows.append({"trimestre": str(t), "mois": m, "modele": model,
                             "nowcast": value, "realise": float(y[t])})
        log(f"  {t} fait")
    return pd.DataFrame(rows)


def dm_pvalue(e1: np.ndarray, e2: np.ndarray, h: int = 1) -> float:
    """Diebold-Mariano bilatéral, perte quadratique, petite correction d'échantillon de Harvey.

    e1 est le modèle jugé, e2 la référence : une statistique négative favorise le modèle jugé.
    """
    d = e1**2 - e2**2
    n = len(d)
    d_bar = d.mean()
    gamma = [np.sum((d[k:] - d_bar) * (d[:n - k] - d_bar)) / n for k in range(h)]
    var_d = (gamma[0] + 2.0 * sum(gamma[1:])) / n
    if var_d <= 0:
        return np.nan
    dm = d_bar / np.sqrt(var_d)
    harvey = np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    return float(2.0 * stats.t.sf(abs(dm * harvey), df=n - 1))


def summary(results: pd.DataFrame, exclude_covid: bool = False) -> pd.DataFrame:
    """RMSFE par modèle et par mois d'information, en ratio sur l'AR, avec le p de Diebold-Mariano."""
    df = results.copy()
    if exclude_covid:
        df = df[~df["trimestre"].isin([str(q) for q in COVID])]
    out = []
    for m in sorted(df["mois"].unique()):
        sub = df[df["mois"] == m].pivot(index="trimestre", columns="modele", values="nowcast")
        real = df[df["mois"] == m].pivot(index="trimestre", columns="modele", values="realise").iloc[:, 0]
        err = sub.sub(real, axis=0)
        rmse_ar = float(np.sqrt((err["ar"] ** 2).mean()))
        for model in sub.columns:
            e = err[model].to_numpy()
            row = {"mois": m, "modele": model,
                   "rmsfe": float(np.sqrt((e**2).mean())),
                   "ratio_ar": float(np.sqrt((e**2).mean())) / rmse_ar,
                   "p_dm_vs_ar": np.nan if model == "ar"
                   else dm_pvalue(e, err["ar"].to_numpy(), h=2 if m == 1 else 1)}
            out.append(row)
    return pd.DataFrame(out)
