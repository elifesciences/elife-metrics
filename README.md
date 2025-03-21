# elife-metrics

An effort by [eLife Sciences](http://elifesciences.org) to provide a data store
and API for accessing article-level metrics (views, downloads, citations).

This project uses the [Python programming language](https://www.python.org/),
the [Django web framework](https://www.djangoproject.com/) and a
[relational database](https://en.wikipedia.org/wiki/Relational_database_management_system).

[Github repo](https://github.com/elifesciences/elife-metrics/).

API documentation can be found here:

* [code](https://github.com/elifesciences/elife-metrics/blob/master/src/metrics/api_v2_urls.py)

For example, the [Homo Naledi](https://dx.doi.org/10.7554/eLife.09560) article:

* [/api/v2/article/9560/summary](/api/v2/article/9560/summary)

would yield a response similar to:

    {"total":1,"items":[{"id":9560,"views":227913,"downloads":16498,"crossref":103,"pubmed":21,"scopus":52}]}

------------

## Local development

### Prerequisites

Docker
Docker Compose

#### 3rd Party credentials for local development

The service has dependencies on the following 3rd party services:

[`crossref`](https://www.crossref.org)
[`scopus`](https://www.scopus.com/home.uri)
[`Google Analytics`](https://developers.google.com/analytics/devguides/collection/ga4)

Each of these require credentials to be set in the environment. You will need to set these up in your local environment
in order to ingest/generate metrics data locally.

In the `.docker/app.cfg` file, you will need to set the following variables with real values:

```
[scopus]
apikey: <scopus api key>

[crossref]
user: <crossref user>
pass: <crossref pass>
```
For Google Analytics, you will need to provide a `client_secrets.json` file in the `.docker` directory of the project.

Example `.docker/client-secrets.json` file:
```json
{
  "private_key_id": "<private_key_id>",
  "private_key": "<private_key>",
  "client_id": "<client_id>",
  "client_email": "<client_email>",
  "type": "service_account"
}
```

#### TODO: AWS Section
...

### (Optional) Prepare for seeding the local database
If you want to seed the local database with some data, one way is to populate the `.docker/pg_import_data.sql` file with the
 desired contents. In a later step you can execute the import command to load the data into the database.

### Build
```bash
make build
```

### Run
```bash
make run
```

### (Optional) Importing data into the local database
```bash
make import-data
```

### Stop
```bash
make stop
````

### Running linting
```bash
make lint
```

### Running tests
```bash
make test
```

### Run test watching for files changes

```bash
make dev-watch
```

Note: Some tests will fail because they require a database to be running. You can run over a subset passing PYTEST_WATCH_MODULES to make

```bash
make dev-watch PYTEST_WATCH_MODULES="src/article_metrics/tests/test_crossref_citations.py"
```

You can run a watch within docker compose with the database using:

```bash
make watch
```

Note: some docker setups may not react to file changes

### Working with local ingestion

#### Fetching Articles
To download a list of PMCIDs and create the relevant articles in the db run:

```bash
make fetch-articles
```

#### Fetching Metrics
To fetch metrics for the articles in the db:

```bash
make fetch-metrics
```

You can also pass in the number of days and months to look back for metrics data should you need to:

```bash
docker compose exec app bash -c "python src/manage.py ingest_metrics --days 999 --months 999"
```

(If not provided, the defaults at the time of writing are 5 days and 2 months)

------------

#### Fetching Citation Counts for an Article
For use as a debugging utility, to fetch citation counts for all versions of an article (currently Crossref only) run:

```bash
make fetch-citation-counts-for-article ARTICLE_ID="85111"
```
(note this does not persist the data in the database)

Example output:
```
Article with id 85111 exists
INFO - fetching crossref citations for 10.7554/eLife.85111
INFO - fetching crossref citations for 10.7554/eLife.85111.1
INFO - fetching crossref citations for 10.7554/eLife.85111.2
INFO - fetching crossref citations for 10.7554/eLife.85111.3

Citation data for 85111: [
 {'doi': '10.7554/eLife.85111', 'num': 16, 'source': 'crossref', 'source_id': 'https://doi.org/10.7554/eLife.85111'}, 
 {'doi': '10.7554/eLife.85111.1', 'num': 12, 'source': 'crossref', 'source_id': 'https://doi.org/10.7554/eLife.85111.1'}, 
 {'doi': '10.7554/eLife.85111.2', 'num': 3, 'source': 'crossref', 'source_id': 'https://doi.org/10.7554/eLife.85111.2'}, 
 {'doi': '10.7554/eLife.85111.3', 'num': 3, 'source': 'crossref', 'source_id': 'https://doi.org/10.7554/eLife.85111.3'}
]

Combined citation data for 85111: {
 'doi': '10.7554/eLife.85111', 
 'num': 34, 
 'source': 'crossref', 
 'source_id': 'https://doi.org/10.7554/eLife.85111'
}
```

### Legacy non-docker installation

[code](https://github.com/elifesciences/elife-metrics/blob/master/install.sh)

    git clone https://github.com/elifesciences/elife-metrics
    cd elife-metrics
    ./install.sh

### updating

[code](https://github.com/elifesciences/elife-metrics/blob/master/install.sh)

    git pull
    ./install.sh
    ./migrate.sh

### testing

[code](https://github.com/elifesciences/elife-metrics/blob/master/src/metrics/tests/)

    ./project_tests.sh

### running

[code](https://github.com/elifesciences/elife-metrics/blob/master/manage.sh)

    ./manage.sh runserver
    firefox http://127.0.0.1:8000/api/docs/


## Copyright & Licence

Copyright 2016-2024 eLife Sciences. Licensed under the [GPLv3](LICENCE.txt)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
