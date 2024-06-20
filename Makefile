DOCKER_COMPOSE = docker compose

build:
	$(DOCKER_COMPOSE) build

run:
	$(DOCKER_COMPOSE) up --wait

stop:
	$(DOCKER_COMPOSE) down

lint:
	$(DOCKER_COMPOSE) exec app bash -c "./.lint.sh"

test:
	$(DOCKER_COMPOSE) exec app bash -c "./.test.sh"

import-data:
	$(DOCKER_COMPOSE) exec postgres psql -U postgres -d postgres -f /data/pg_import_data.sql

fetch-articles:
	$(DOCKER_COMPOSE) exec app bash -c "./download-pmcids.sh"

fetch-metrics:
	$(DOCKER_COMPOSE) exec app bash -c "python src/manage.py import_metrics"

fetch-citation-counts-for-article:
	$(DOCKER_COMPOSE) exec app bash -c "python src/manage.py fetch_citation_counts_for_article $(ARTICLE_ID)"
