SRC := src
TMP := tmp
PYTEST := `which py.test`
MYPY_REPORT := $(CURDIR)/$(TMP)/mypy
TESTS_REPORT := $(CURDIR)/$(TMP)/tests
HTMLCOV := $(TESTS_REPORT)/htmlcov

clean:
	find . -type f -name "*py[co]" -delete
	find . -type d -name "__pycache__" -delete

# REQUIREMENTS
install-pip:
	pip install pip==20.3
	pip install poetry==1.1.4

sync-requirements: install-pip
	poetry install --remove-untracked

update-requirements: install-pip
	poetry update

requirements: update-requirements sync-requirements

check-mypy:
	rm -rf .mypy_cache
	rm -rf $(MYPY_REPORT)
	MYPYPATH="$(SRC)" \
		mypy --config-file=setup.cfg \
	--html-report=$(MYPY_REPORT)/mypy_html_report \
		.

check-openapi-docs: update-openapi-docs
	git diff --quiet HEAD $(REF) -- docs/api || { echo 'update docs plz' ; exit 1; }

check-db-docs: update-db-docs
	git diff --quiet HEAD $(REF) -- docs/db.md || { echo 'update docs plz' ; exit 1; }


# CODE: FORMAT
isort:
	./code_checks/make_isort.sh -f $(SRC)

black:
	./code_checks/make_black.sh -f $(SRC)

autoflake:
	./code_checks/make_autoflake.sh -f $(SRC)

format: autoflake black isort


# CODE: coverage & tests
tests:
	cd $(SRC) && \
		mkdir -p $(TESTS_REPORT) && \
		export COVERAGE_FILE=$(TESTS_REPORT)/coverage.cov && \
			$(PYTEST) . \
			--cov . --cov-report term-missing --cov-config=../setup.cfg --cov-report=

coverage-combine:
	coverage combine $(TESTS_REPORT)/*.cov

coverage-report: coverage-combine
	coverage report

coverage-html-report: coverage-combine
	coverage html -d $(HTMLCOV)

# RUN
run-server:
	cd $(SRC) && python main.py run_server

openapi-docs:
	cd $(SRC) && python main.py openapi_docs > ../docs/openapi.yaml


check: requirements clean format check-mypy tests openapi-docs
