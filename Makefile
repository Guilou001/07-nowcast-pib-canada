# Prérequis : uv (https://docs.astral.sh/uv/)
UV ?= uv

setup:
	$(UV) sync --locked --all-extras

test:             ## 6 tests synthétiques : calendrier, AR, bridge, fuite, Diebold-Mariano (sans réseau)
	$(UV) run pytest

lint:
	$(UV) run ruff check src tests

backtest:         ## 936 nowcasts 2011-2023 (35 s ; exige `ncc fetch` + dépôts manuels LCDMA/FRED-MD)
	$(UV) run ncc backtest
