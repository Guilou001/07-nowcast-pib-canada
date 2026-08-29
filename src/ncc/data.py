"""Données : le PIB par l'API de Statistique Canada, le panel mensuel LCDMA déposé à la main.

Trois sources, trois statuts :

1. **PIB trimestriel réel** (cible) : table 36-10-0104, vecteur v62305752, PIB aux prix du marché en
   dollars enchaînés de 2017, désaisonnalisé au taux annuel. Téléchargé par l'API Web de Statistique
   Canada (licence ouverte), transformé en croissance trimestrielle annualisée en pourcent.
2. **PIB mensuel réel par industrie** : table 36-10-0434, vecteur v65201210, toutes industries.
   Même API ; c'est la matière première du modèle bridge.
3. **LCDMA** (Fortin-Gagnon, Leroux, Stevanovic et Surprenant, 2022), le grand panel mensuel canadien,
   411 séries depuis 1981 : licence non commerciale, donc JAMAIS commité ; le fichier CAN_MD se dépose
   à la main dans data/raw/ (instructions dans le README). Les millésimes publics (Borealis,
   DOI 10.5683/SP3/59JYPU) s'arrêtent en 2021-08 ; le snapshot utilisé ici court jusqu'en 2024-04,
   date déclarée dans le nom du fichier.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

WDS = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods"
V_PIB_TRIMESTRIEL = 62305752      # 36-10-0104 : PIB prix du marché, enchaîné 2017, dessaisonnalisé TAA
V_PIB_MENSUEL = 65201210          # 36-10-0434 : PIB toutes industries, enchaîné 2017

RAW = Path("data/raw")
LCDMA_SNAPSHOT = RAW / "CAN_MD_snapshot_2024-04.csv"
FREDMD_SNAPSHOT = RAW / "FRED_MD_snapshot_2024-05.csv"


def fetch_statcan(vector_id: int, n: int = 800) -> pd.Series:
    """Une série de l'API Web de Statistique Canada, indexée par période de référence."""
    import requests

    resp = requests.post(WDS, json=[{"vectorId": vector_id, "latestN": n}], timeout=60)
    resp.raise_for_status()
    points = resp.json()[0]["object"]["vectorDataPoint"]
    s = pd.Series({pd.Timestamp(p["refPer"]): p["value"] for p in points}).sort_index()
    return s.astype(float)


def fetch(dest: Path = RAW) -> None:
    """Écrit les deux séries de PIB en parquet ; la LCDMA, elle, se dépose à la main."""
    dest.mkdir(parents=True, exist_ok=True)
    fetch_statcan(V_PIB_TRIMESTRIEL).rename("pib_t").to_frame().to_parquet(dest / "pib_trimestriel.parquet")
    fetch_statcan(V_PIB_MENSUEL).rename("pib_m").to_frame().to_parquet(dest / "pib_mensuel.parquet")


def quarterly_gdp_growth(path: Path = RAW / "pib_trimestriel.parquet") -> pd.Series:
    """Croissance trimestrielle annualisée du PIB réel, en pourcent (la cible du nowcast)."""
    level = pd.read_parquet(path)["pib_t"]
    growth = 100.0 * ((level / level.shift(1)) ** 4 - 1.0)
    growth.index = pd.PeriodIndex(growth.index, freq="Q")
    return growth.dropna()


def monthly_gdp_growth(path: Path = RAW / "pib_mensuel.parquet") -> pd.Series:
    """Croissance mensuelle du PIB par industrie, en pourcent."""
    level = pd.read_parquet(path)["pib_m"]
    growth = 100.0 * level.pct_change()
    growth.index = pd.PeriodIndex(growth.index, freq="M")
    return growth.dropna()


def load_lcdma(path: Path = LCDMA_SNAPSHOT) -> pd.DataFrame:
    """Le panel LCDMA en niveaux, index mensuel ; erreur claire si le dépôt manuel manque."""
    if not path.exists():
        raise FileNotFoundError(f"{path} absent : déposer le fichier CAN_MD (LCDMA) à la main, "
                                "voir la section Données du README (licence non commerciale)")
    df = pd.read_csv(path)
    df.index = pd.PeriodIndex(pd.to_datetime(df.pop("Date")), freq="M")
    return df.astype(float)


def stationarize(panel: pd.DataFrame) -> pd.DataFrame:
    """Rend chaque série stationnaire par une règle simple et déclarée : différence de log en
    pourcent pour les séries strictement positives (production, prix, crédit), différence simple
    pour les autres (taux, soldes d'opinion). Approximation assumée : la LCDMA publie des codes de
    transformation plus fins, non embarqués dans le snapshot."""
    out = {}
    for col in panel.columns:
        s = panel[col]
        if (s.dropna() > 0).all():
            out[col] = 100.0 * np.log(s).diff()
        else:
            out[col] = s.diff()
    return pd.DataFrame(out, index=panel.index)


def load_fredmd_panel(path: Path = FREDMD_SNAPSHOT) -> pd.DataFrame:
    """Le panel FRED-MD américain (McCracken et Ng, 2016), stationnarisé par la même règle simple."""
    if not path.exists():
        raise FileNotFoundError(f"{path} absent : déposer le fichier FRED-MD à la main (voir README)")
    df = pd.read_csv(path, sep=";")
    first = df.columns[0]
    df = df[~df[first].astype(str).str.lower().str.startswith("transform")]
    df.index = pd.PeriodIndex(pd.to_datetime(df.pop(first)), freq="M")
    return stationarize(df.astype(float))
