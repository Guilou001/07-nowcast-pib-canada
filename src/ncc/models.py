"""Cinq modèles de nowcast, tous nourris par le même ensemble d'information daté.

Un nowcast est une prévision du trimestre EN COURS, faite avant la publication officielle qui
n'arrive que deux mois après la fin du trimestre. L'ensemble d'information (info set) fige ce qui
est réellement connu au moment de la prévision : le dernier trimestre de PIB publié, et le panel
mensuel arrêté deux mois avant la date du nowcast (délai uniforme, choix conservateur déclaré).

1. **AR** : le PIB expliqué par ses propres retards, la référence à battre.
2. **Bridge** : le PIB mensuel par industrie, agrégé au trimestre, mois manquants prolongés par un
   AR(1) mensuel ; c'est le pont entre les fréquences.
3. **Facteurs** : les composantes principales du panel LCDMA (les quelques forces communes qui
   résument 400 séries), moyennées sur les trois derniers mois disponibles.
4. **Elastic net** : régression linéaire pénalisée sur les facteurs, le bridge et le dernier PIB
   connu ; la pénalité choisie par validation croisée temporelle dans la fenêtre d'entraînement.
5. **Forêt aléatoire** : la même table de traits, sans hypothèse de linéarité, réglages fixes
   déclarés (500 arbres).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

PANEL_LAG = 2         # mois entre la date du nowcast et la dernière observation du panel
GDP_RELEASE_LAG = 2   # le PIB du trimestre T est publié à la fin du mois 2 du trimestre T+1
N_FACTORS = 10


@dataclass(frozen=True)
class InfoSet:
    """Ce qui est connu à la fin du mois `month_idx` (1, 2 ou 3) du trimestre `quarter`."""
    quarter: pd.Period            # le trimestre à prévoir (fréquence Q)
    month_idx: int                # 1, 2 ou 3 : le mois du trimestre où l'on se place

    @property
    def now_month(self) -> pd.Period:
        return self.quarter.asfreq("M", how="start") + (self.month_idx - 1)

    @property
    def panel_through(self) -> pd.Period:
        return self.now_month - PANEL_LAG

    @property
    def gdp_through(self) -> pd.Period:
        """Le dernier trimestre publié : T-1 à partir de la fin du mois 2 de T, T-2 avant."""
        return self.quarter - 1 if self.month_idx >= 2 else self.quarter - 2

    @property
    def horizon(self) -> int:
        return (self.quarter - self.gdp_through).n


def _ols(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    xx = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(xx, y, rcond=None)
    return beta


def _predict(beta: np.ndarray, x_new: np.ndarray) -> float:
    return float(beta[0] + x_new @ beta[1:])


def ar_nowcast(y: pd.Series, info: InfoSet, p: int = 2) -> float:
    """AR(p) estimé par moindres carrés sur les trimestres publiés, itéré jusqu'à T."""
    hist = y[y.index <= info.gdp_through].dropna()
    lagged = np.column_stack([hist.shift(k).to_numpy() for k in range(1, p + 1)])
    keep = ~np.isnan(lagged).any(axis=1)
    beta = _ols(lagged[keep], hist.to_numpy()[keep])
    values = list(hist.iloc[-p:][::-1].to_numpy())    # [y_{t}, y_{t-1}, ...] le plus récent d'abord
    for _ in range(info.horizon):
        nxt = _predict(beta, np.array(values[:p]))
        values.insert(0, nxt)
    return float(values[0])


def bridge_quarterly_growth(mgdp_level: pd.Series, info: InfoSet) -> float:
    """La croissance trimestrielle annualisée du PIB mensuel pour T, mois manquants prolongés.

    Les mois connus vont jusqu'à `panel_through` ; les mois restants de T sont prolongés par un
    AR(1) sur la croissance mensuelle, puis les niveaux se moyennent par trimestre. Mémoïsé par
    (série, trimestre, date d'arrêt).
    """
    key = (id(mgdp_level), info.quarter, info.panel_through)
    hit = _BRIDGE_CACHE.get(key)
    if hit is not None and hit[0] is mgdp_level:
        return hit[1]
    level = mgdp_level[mgdp_level.index <= info.panel_through].dropna()
    growth = 100.0 * level.pct_change().dropna()
    g = growth.to_numpy()
    beta = _ols(g[:-1].reshape(-1, 1), g[1:])
    months_t = [info.quarter.asfreq("M", how="start") + k for k in range(3)]
    last_level = float(level.iloc[-1])
    last_growth = float(growth.iloc[-1])
    levels = dict(level.items())
    cur_month = level.index[-1]
    while cur_month < months_t[-1]:
        cur_month += 1
        last_growth = _predict(beta, np.array([last_growth]))
        last_level = last_level * (1.0 + last_growth / 100.0)
        levels[cur_month] = last_level
    series = pd.Series(levels)
    q_level = series.groupby(series.index.asfreq("Q")).mean()
    ratio = q_level[info.quarter] / q_level[info.quarter - 1]
    value = float(100.0 * (ratio**4 - 1.0))
    _BRIDGE_CACHE[key] = (mgdp_level, value)
    return value


def bridge_nowcast(y: pd.Series, mgdp_level: pd.Series, info: InfoSet) -> float:
    """Régression du PIB trimestriel sur l'agrégat bridge, estimée aux trimestres publiés."""
    hist = y[y.index <= info.gdp_through].dropna()
    x_hist, y_hist = [], []
    for s in hist.index[hist.index >= pd.Period("2001Q1", freq="Q")]:
        x_hist.append(bridge_quarterly_growth(mgdp_level, InfoSet(s, info.month_idx)))
        y_hist.append(hist[s])
    beta = _ols(np.array(x_hist).reshape(-1, 1), np.array(y_hist))
    return _predict(beta, np.array([bridge_quarterly_growth(mgdp_level, info)]))


# Caches à référence FORTE : la clé retient l'objet lui-même (pas seulement son id), et un
# succès de cache exige l'identité `is` ; un id() réutilisé après libération ne peut donc jamais
# servir une valeur périmée. Hypothèse restante, déclarée : les panels ne sont pas mutés en place.
_FACTOR_CACHE: dict[tuple[int, pd.Period, int], tuple[pd.DataFrame, pd.DataFrame]] = {}
_BRIDGE_CACHE: dict[tuple[int, pd.Period, pd.Period], tuple[pd.Series, float]] = {}


def factor_history(panel_stat: pd.DataFrame, cutoff: pd.Period,
                   n_factors: int = N_FACTORS) -> pd.DataFrame:
    """UNE seule ACP par origine (Stock et Watson, 2002) : ajustée sur le panel arrêté à `cutoff`,
    elle produit l'historique mensuel complet des scores de facteurs vus de cette origine.

    Les lignes historiques de la table de traits lisent toutes CE fit : le signe et l'ordre des
    composantes, arbitraires d'un ajustement à l'autre, sont ainsi cohérents sur toute la colonne.
    Seules les séries encore observées à la coupure sont gardées (une série discontinuée serait
    sinon épinglée à sa moyenne) ; les trous restants sont mis à zéro après standardisation,
    c'est-à-dire imputés à la moyenne, choix déclaré.
    """
    key = (id(panel_stat), cutoff, n_factors)
    hit = _FACTOR_CACHE.get(key)
    if hit is not None and hit[0] is panel_stat:
        return hit[1]
    from sklearn.decomposition import PCA

    avail = panel_stat[panel_stat.index <= cutoff].loc[pd.Period("1982-01", freq="M"):]
    alive = avail.columns[avail.iloc[-3:].notna().any()]
    keep = [c for c in alive if avail[c].notna().mean() > 0.90]
    x = avail[keep]
    z = ((x - x.mean()) / x.std(ddof=1)).fillna(0.0)
    pca = PCA(n_components=n_factors, random_state=0)
    scores = pd.DataFrame(pca.fit_transform(z.to_numpy()), index=avail.index)
    _FACTOR_CACHE[key] = (panel_stat, scores)
    return scores


def _state(scores: pd.DataFrame, through: pd.Period) -> np.ndarray:
    """La moyenne des scores sur les trois mois se terminant à `through` (NaN si trop tôt)."""
    window = scores[scores.index <= through].iloc[-3:]
    if len(window) < 3:
        return np.full(scores.shape[1], np.nan)
    return window.mean(axis=0).to_numpy()


def feature_table(y: pd.Series, panel_stat: pd.DataFrame, mgdp_level: pd.Series, info: InfoSet,
                  start: pd.Period, n_factors: int = N_FACTORS,
                  us_panel: pd.DataFrame | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """La même table de traits pour facteurs, elastic net et forêt : une ligne par trimestre
    publié s, avec l'état des facteurs lu au mois que s aurait eu (dans l'ACP unique de l'origine),
    l'agrégat bridge et le dernier PIB connu à l'époque de s."""
    scores = factor_history(panel_stat, info.panel_through, n_factors)
    scores_us = factor_history(us_panel, info.panel_through, 5) if us_panel is not None else None
    hist = y[(y.index <= info.gdp_through) & (y.index >= start)].dropna()
    rows, targets = [], []
    for s in hist.index:
        past = InfoSet(s, info.month_idx)
        feats = [*_state(scores, past.panel_through),
                 bridge_quarterly_growth(mgdp_level, past),
                 float(y[past.gdp_through]) if past.gdp_through in y.index else np.nan]
        if scores_us is not None:
            feats.extend(_state(scores_us, past.panel_through))
        rows.append(feats)
        targets.append(hist[s])
    feats_now = [*_state(scores, info.panel_through),
                 bridge_quarterly_growth(mgdp_level, info),
                 float(y[info.gdp_through])]
    if scores_us is not None:
        feats_now.extend(_state(scores_us, info.panel_through))
    x = np.array(rows)
    keep = ~np.isnan(x).any(axis=1)
    return x[keep], np.array(targets)[keep], np.array(feats_now)


def factor_nowcast(x: np.ndarray, y: np.ndarray, x_now: np.ndarray) -> float:
    """Régression linéaire simple sur la table de traits (facteurs + bridge + dernier PIB)."""
    return _predict(_ols(x, y), x_now)


def elastic_net_nowcast(x: np.ndarray, y: np.ndarray, x_now: np.ndarray) -> float:
    from sklearn.linear_model import ElasticNetCV
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler().fit(x)
    model = ElasticNetCV(l1_ratio=[0.1, 0.5, 0.9], cv=TimeSeriesSplit(5), random_state=0,
                         max_iter=20000)
    model.fit(scaler.transform(x), y)
    return float(model.predict(scaler.transform(x_now.reshape(1, -1)))[0])


def random_forest_nowcast(x: np.ndarray, y: np.ndarray, x_now: np.ndarray) -> float:
    from sklearn.ensemble import RandomForestRegressor

    model = RandomForestRegressor(n_estimators=500, max_features="sqrt", random_state=0, n_jobs=-1)
    model.fit(x, y)
    return float(model.predict(x_now.reshape(1, -1))[0])
