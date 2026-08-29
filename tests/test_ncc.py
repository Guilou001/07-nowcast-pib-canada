"""Le protocole sur données synthétiques : calendrier d'information, AR, bridge, fuite, juges."""

import numpy as np
import pandas as pd
import pytest

from ncc.data import stationarize
from ncc.engine import dm_pvalue
from ncc.models import InfoSet, ar_nowcast, bridge_quarterly_growth, feature_table


def test_infoset_calendar_matches_publication_lags():
    t = pd.Period("2020Q2", freq="Q")
    m1, m2, m3 = InfoSet(t, 1), InfoSet(t, 2), InfoSet(t, 3)
    assert str(m1.now_month) == "2020-04" and str(m1.panel_through) == "2020-02"
    assert str(m1.gdp_through) == "2019Q4" and m1.horizon == 2
    assert str(m2.gdp_through) == "2020Q1" and m2.horizon == 1
    assert str(m3.panel_through) == "2020-04"


def ar1_series(n: int = 120, phi: float = 0.8, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    y = np.zeros(n)
    for t in range(1, n):
        y[t] = phi * y[t - 1] + rng.normal(0, 0.5)
    return pd.Series(y, index=pd.period_range("1990Q1", periods=n, freq="Q"))


def test_ar_nowcast_beats_the_mean_on_ar_data():
    y = ar1_series()
    errs_ar, errs_mean = [], []
    for q in y.index[-20:]:
        info = InfoSet(q, 3)
        hist = y[y.index <= info.gdp_through]
        errs_ar.append(y[q] - ar_nowcast(y, info))
        errs_mean.append(y[q] - float(hist.mean()))
    assert np.sqrt(np.mean(np.square(errs_ar))) < np.sqrt(np.mean(np.square(errs_mean)))


def test_bridge_growth_recovers_a_steady_trend():
    rng = np.random.default_rng(1)
    idx = pd.period_range("2000-01", periods=250, freq="M")
    level = pd.Series(100.0 * np.cumprod(1.0 + 0.002 + rng.normal(0, 0.0002, 250)), index=idx)
    info = InfoSet(idx[-2].asfreq("Q"), 3)
    g = bridge_quarterly_growth(level, info)
    true_annualized = 100.0 * (1.002**12 - 1.0)     # 0,2 % par mois, composé sur douze mois
    assert g == pytest.approx(true_annualized, rel=0.15)


def synthetic_world(n_months: int = 240, seed: int = 2):
    rng = np.random.default_rng(seed)
    midx = pd.period_range("2000-01", periods=n_months, freq="M")
    panel = pd.DataFrame(rng.normal(0, 1, (n_months, 40)), index=midx,
                         columns=[f"s{i}" for i in range(40)])
    level = pd.Series(100.0 * np.cumprod(1.0 + rng.normal(0.002, 0.004, n_months)), index=midx)
    qidx = pd.period_range("2000Q1", periods=n_months // 3, freq="Q")
    y = pd.Series(rng.normal(2, 1, len(qidx)), index=qidx)
    return y, level, panel


def test_features_ignore_panel_months_after_the_cutoff():
    y, level, panel = synthetic_world()
    info = InfoSet(pd.Period("2018Q2", freq="Q"), 2)
    start = pd.Period("2005Q1", freq="Q")
    _, _, x_now = feature_table(y, panel, level, info, start)
    shocked = panel.copy()
    shocked.loc[shocked.index > info.panel_through] = 99.0     # le futur du panel bouge
    _, _, x_now_shocked = feature_table(y, shocked, level, info, start)
    # même ACP (mêmes données avant la coupure), donc mêmes scores, signes compris
    assert np.allclose(x_now, x_now_shocked, atol=1e-8)


def test_factor_cache_requires_the_same_object():
    from ncc.models import _FACTOR_CACHE, factor_history

    _, _, panel = synthetic_world()
    cutoff = pd.Period("2018-04", freq="M")
    a = factor_history(panel, cutoff)
    n_before = len(_FACTOR_CACHE)
    b = factor_history(panel.copy(), cutoff)       # copie : même contenu, autre objet
    assert np.allclose(a.to_numpy(), b.to_numpy())
    assert len(_FACTOR_CACHE) > n_before           # la copie a été recalculée, pas servie du cache


def test_discontinued_series_are_dropped_at_the_cutoff():
    from ncc.models import factor_history

    _, _, panel = synthetic_world()
    dead = panel.copy()
    dead["morte"] = dead.iloc[:, 0]
    cutoff = pd.Period("2018-04", freq="M")
    dead.loc[dead.index > pd.Period("2015-12", freq="M"), "morte"] = np.nan   # série arrêtée en 2015
    alive_scores = factor_history(panel, cutoff)
    dead_scores = factor_history(dead, cutoff)
    # la série morte est écartée : les scores coïncident avec le panel qui ne l'a jamais contenue
    assert np.allclose(alive_scores.to_numpy(), dead_scores.to_numpy())


def test_dm_pvalue_orders_a_clear_winner():
    rng = np.random.default_rng(3)
    e_ref = rng.normal(0, 1.0, 60)
    e_good = 0.3 * e_ref
    assert dm_pvalue(e_good, e_ref) < 0.01
    assert np.isnan(dm_pvalue(e_ref.copy(), e_ref.copy()))


def test_stationarize_rule_by_sign():
    idx = pd.period_range("2000-01", periods=5, freq="M")
    df = pd.DataFrame({"prod": [100.0, 110.0, 121.0, 133.1, 146.41],
                       "taux": [1.0, -0.5, 0.25, 0.0, 0.5]}, index=idx)
    out = stationarize(df)
    assert out["prod"].iloc[1] == pytest.approx(100.0 * np.log(1.1))
    assert out["taux"].iloc[1] == pytest.approx(-1.5)
