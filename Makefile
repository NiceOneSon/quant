# dbt convenience targets.
# direnv(.envrc)가 활성화된 환경에서는 `dbt` 명령어가 PATH에 있고
# QUANT_DATA_DIR 절대경로가 설정되어 있어 어디서든 `dbt build` 가능.
# direnv 없이도 동작하도록 Makefile 내에서 QUANT_ROOT / cd 폴백을 유지한다.

QUANT_ROOT  ?= $(CURDIR)
DBT_BIN     ?= $(QUANT_ROOT)/dbt/.venv/bin/dbt

.PHONY: dbt-deps dbt-seed dbt-run dbt-test dbt-build dbt-docs dbt-clean

dbt-deps:
	cd $(QUANT_ROOT)/dbt && $(DBT_BIN) deps

dbt-seed:
	cd $(QUANT_ROOT)/dbt && $(DBT_BIN) seed

dbt-run:
	cd $(QUANT_ROOT)/dbt && $(DBT_BIN) run

dbt-test:
	cd $(QUANT_ROOT)/dbt && $(DBT_BIN) test

dbt-build:
	cd $(QUANT_ROOT)/dbt && $(DBT_BIN) build
	uv run python scripts/gen_duckdb_views.py
	rm -rf $(QUANT_ROOT)/viz/evidence/.evidence/template/static/data/quant/
	rm -rf $(QUANT_ROOT)/viz/evidence/.evidence/meta/query-cache/
	rm -rf $(QUANT_ROOT)/viz/evidence/.evidence/template/.evidence-queries/

dbt-docs:
	cd $(QUANT_ROOT)/dbt && $(DBT_BIN) docs generate && $(DBT_BIN) docs serve

dbt-clean:
	cd $(QUANT_ROOT)/dbt && $(DBT_BIN) clean
