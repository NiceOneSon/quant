# dbt convenience targets.
# CWD must be dbt/ so that the default QUANT_DATA_DIR=../data resolves to data/.
DBT_BIN := $(CURDIR)/dbt/.venv/bin/dbt
DBT_DIR := $(CURDIR)/dbt

.PHONY: dbt-deps dbt-seed dbt-run dbt-test dbt-build dbt-docs dbt-clean

dbt-deps:
	cd $(DBT_DIR) && $(DBT_BIN) deps --profiles-dir .

dbt-seed:
	cd $(DBT_DIR) && $(DBT_BIN) seed --profiles-dir .

dbt-run:
	cd $(DBT_DIR) && $(DBT_BIN) run --profiles-dir .

dbt-test:
	cd $(DBT_DIR) && $(DBT_BIN) test --profiles-dir .

dbt-build:
	cd $(DBT_DIR) && $(DBT_BIN) build --profiles-dir .
	uv run python scripts/gen_duckdb_views.py

dbt-docs:
	cd $(DBT_DIR) && $(DBT_BIN) docs generate --profiles-dir . && $(DBT_BIN) docs serve --profiles-dir .

dbt-clean:
	cd $(DBT_DIR) && $(DBT_BIN) clean --profiles-dir .
