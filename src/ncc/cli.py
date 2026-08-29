"""Ligne de commande : télécharger, backtester, produire le nowcast du trimestre en cours."""

from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(help="Nowcast du PIB trimestriel canadien : AR, bridge, facteurs LCDMA, "
                       "elastic net, forêt, en pseudo temps réel.")


@app.callback()
def main() -> None:
    """Sous-commandes nommées."""


@app.command()
def fetch() -> None:
    """Télécharge les deux séries de PIB (API Statistique Canada) ; la LCDMA se dépose à la main."""
    from ncc import data

    data.fetch()
    y = data.quarterly_gdp_growth()
    m = data.monthly_gdp_growth()
    typer.echo(f"PIB trimestriel : {y.index[0]} -> {y.index[-1]} ; PIB mensuel : {m.index[0]} -> {m.index[-1]}")


@app.command()
def backtest(start: str = "2011Q1", end: str = "2023Q4", out: Path = Path("results")) -> None:
    """L'évaluation pseudo temps réel complète : 3 nowcasts par trimestre, 6 modèles, tables et figures."""
    import time

    import pandas as pd

    from ncc import data, engine, figures

    t0 = time.time()
    y = data.quarterly_gdp_growth()
    mgdp = pd.read_parquet(data.RAW / "pib_mensuel.parquet")["pib_m"]
    mgdp.index = pd.PeriodIndex(mgdp.index, freq="M")
    panel = data.stationarize(data.load_lcdma())
    us = data.load_fredmd_panel()
    results = engine.run_backtest(y, mgdp, panel, us,
                                  pd.Period(start, freq="Q"), pd.Period(end, freq="Q"),
                                  log=typer.echo)
    tables = out / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    results.to_csv(tables / "nowcasts.csv", index=False)
    engine.summary(results).to_csv(tables / "rmsfe.csv", index=False)
    engine.summary(results, exclude_covid=True).to_csv(tables / "rmsfe_hors_covid.csv", index=False)
    figs = out / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    figures.fig_nowcast_vs_realise(results, figs / "nowcast_vs_realise.png")
    figures.fig_rmsfe(engine.summary(results, exclude_covid=True), figs / "rmsfe_par_mois.png")
    figures.fig_us_block(engine.summary(results), engine.summary(results, exclude_covid=True),
                         figs / "bloc_americain.png")
    typer.echo(f"{len(results)} nowcasts, tables -> {tables}, figures -> {figs}, "
               f"durée {time.time() - t0:.0f} s")


@app.command()
def report() -> None:
    """Le nowcast du trimestre en cours par le bridge, sur données Statistique Canada fraîches."""
    import pandas as pd

    from ncc import data
    from ncc.models import InfoSet, ar_nowcast, bridge_nowcast

    y = data.quarterly_gdp_growth()
    mgdp = pd.read_parquet(data.RAW / "pib_mensuel.parquet")["pib_m"]
    mgdp.index = pd.PeriodIndex(mgdp.index, freq="M")
    last_month = mgdp.index[-1]
    quarter = (last_month + 2).asfreq("Q")
    month_idx = ((last_month + 2) - quarter.asfreq("M", how="start")).n + 1
    info = InfoSet(quarter, month_idx)
    typer.echo(f"Trimestre visé : {quarter}, information du mois {month_idx} "
               f"(panel arrêté à {info.panel_through}, dernier PIB publié {info.gdp_through})")
    typer.echo(f"  AR      : {ar_nowcast(y, info):+.1f} % (taux annualisé)")
    typer.echo(f"  Bridge  : {bridge_nowcast(y, mgdp, info):+.1f} % (taux annualisé)")
    typer.echo(f"  Réalisé {info.gdp_through} : {float(y[info.gdp_through]):+.1f} %")


if __name__ == "__main__":
    app()
