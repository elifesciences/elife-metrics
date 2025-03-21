VENV = venv
PIP = $(VENV)/bin/pip
PYTHON = $(VENV)/bin/python

DOCKER_COMPOSE = docker compose

PYTEST_WATCH_MODULES = src

SOURCE =
ARTICLE_ID =

copy-docker-app-cfg-if-not-exists:
	@if [ ! -f .docker/app.cfg ]; then \
		cp .docker/app.cfg.template .docker/app.cfg; \
	fi

create-dummy-docker-client-secrets-if-not-exists:
	@if [ ! -f .docker/client-secrets.json ]; then \
		touch .docker/client-secrets.json; \
	fi

download-or-update-api-raml:
	./download-api-raml.sh


dev-watch: create-dummy-docker-client-secrets-if-not-exists
	GOOGLE_APPLICATION_CREDENTIALS=.docker/client-secrets.json \
		DJANGO_SETTINGS_MODULE=core.settings \
		$(PYTHON) -m pytest_watcher \
		--now \
		--runner=$(VENV)/bin/python \
		. \
		-m pytest -vv $(PYTEST_WATCH_MODULES)

build:
	$(DOCKER_COMPOSE) build

run: \
	copy-docker-app-cfg-if-not-exists \
	create-dummy-docker-client-secrets-if-not-exists
	$(DOCKER_COMPOSE) up --wait

stop:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

lint:
	$(DOCKER_COMPOSE) exec app bash -c "./.lint.sh"

test:
	$(DOCKER_COMPOSE) exec app bash -c "./.test.sh"

watch:
	$(DOCKER_COMPOSE) exec app bash -c \
		'DJANGO_SETTINGS_MODULE=core.settings \
		python -m pytest_watcher \
		--now \
		--runner=venv/bin/python \
		. \
		-m pytest -vv $(PYTEST_WATCH_MODULES)'

import-data:
	$(DOCKER_COMPOSE) exec postgres psql -U postgres -d postgres -f /data/pg_import_data.sql

fetch-articles:
	$(DOCKER_COMPOSE) exec app bash -c "./download-pmcids.sh"

fetch-metrics:
	$(DOCKER_COMPOSE) exec app bash -c \
		"python src/manage.py import_metrics --source=$(SOURCE)"

fetch-citation-counts-for-article:
	$(DOCKER_COMPOSE) exec app bash -c "python src/manage.py fetch_citation_counts_for_article $(ARTICLE_ID)"
