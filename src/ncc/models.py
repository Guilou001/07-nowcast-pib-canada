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
    if key in _BRIDGE_CACHE:
        return _BRIDGE_CACHE[key]
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
    _BRIDGE_CACHE[key] = float(100.0 * (ratio**4 - 1.0))
    return _BRIDGE_CACHE[key]


def bridge_nowcast(y: pd.Series, mgdp_level: pd.Series, info: InfoSet) -> float:
    """Régression du PIB trimestriel sur l'agrégat bridge, estimée aux trimestres publiés."""
    hist = y[y.index <= info.gdp_through].dropna()
    x_hist, y_hist = [], []
    for s in hist.index[hist.index >= pd.Period("2001Q1", freq="Q")]:
        x_hist.append(bridge_quarterly_growth(mgdp_level, InfoSet(s, info.month_idx)))
        y_hist.append(hist[s])
    beta = _ols(np.array(x_hist).reshape(-1, 1), np.array(y_hist))
    return _predict(beta, np.array([bridge_quarterly_growth(mgdp_level, info)]))


_FACTOR_CACHE: dict[tuple[int, pd.Period, int], np.ndarray] = {}
_BRIDGE_CACHE: dict[tuple[int, pd.Period, pd.Period], float] = {}


def factor_state(panel_stat: pd.DataFrame, info: InfoSet, n_factors: int = N_FACTORS) -> np.ndarray:
    """Les composantes principales du panel arrêté à `panel_through`, moyennées sur les trois
    derniers mois disponibles : l'état de l'économie tel que le panel le voit à cette date.

    Mémoïsé par (panel, date d'arrêt, nombre de facteurs) : l'état ne dépend que de la date
    d'arrêt, pas du trimestre visé, et le backtest revisite les mêmes dates des dizaines de fois.
    """
    key = (id(panel_stat), info.panel_through, n_factors)
    if key in _FACTOR_CACHE:
        return _FACTOR_CACHE[key]
    from sklearn.decomposition import PCA

    avail = panel_stat[panel_stat.index <= info.panel_through]
    avail = avail.loc[pd.Period("1982-01", freq="M"):]
    keep = avail.columns[avail.notna().mean() > 0.90]
    x = avail[keep]
    z = (x - x.mean()) / x.std(ddof=1)
    z = z.fillna(0.0)
    pca = PCA(n_components=n_factors, random_state=0)
    factors = pca.fit_transform(z.to_numpy())
    _FACTOR_CACHE[key] = factors[-3:].mean(axis=0)
    return _FACTOR_CACHE[key]


def feature_table(y: pd.Series, panel_stat: pd.DataFrame, mgdp_level: pd.Series, info: InfoSet,
                  start: pd.Period, n_factors: int = N_FACTORS,
                  us_panel: pd.DataFrame | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """La même table de traits pour facteurs, elastic net et forêt : une ligne par trimestre
    publié s, construite avec l'ensemble d'information que s aurait eu au même mois du trimestre
    (facteurs du panel, agrégat bridge, dernier PIB connu à l'époque)."""
    hist = y[(y.index <= info.gdp_through) & (y.index >= start)].dropna()
    rows, targets = [], []
    for s in hist.index:
        past = InfoSet(s, info.month_idx)
        feats = [*factor_state(panel_stat, past, n_factors),
                 bridge_quarterly_growth(mgdp_level, past),
                 float(y[past.gdp_through]) if past.gdp_through in y.index else np.nan]
        if us_panel is not None:
            feats.extend(factor_state(us_panel, past, 5))
        rows.append(feats)
        targets.append(hist[s])
    feats_now = [*factor_state(panel_stat, info, n_factors),
                 bridge_quarterly_growth(mgdp_level, info),
                 float(y[info.gdp_through])]
    if us_panel is not None:
        feats_now.extend(factor_state(us_panel, info, 5))
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
