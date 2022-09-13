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

## installation

[code](https://github.com/elifesciences/elife-metrics/blob/master/install.sh) 

    git clone https://github.com/elifesciences/elife-metrics
    cd elife-metrics
    ./install.sh

## updating

[code](https://github.com/elifesciences/elife-metrics/blob/master/install.sh)  

    git pull
    ./install.sh

## testing 

[code](https://github.com/elifesciences/elife-metrics/blob/master/src/metrics/tests/)  

    ./project_tests.sh

## running

[code](https://github.com/elifesciences/elife-metrics/blob/master/manage.sh)

    ./manage.sh runserver
    firefox http://127.0.0.1:8000/api/docs/

## Copyright & Licence
 
Copyright 2016-2022 eLife Sciences. Licensed under the [GPLv3](LICENCE.txt)

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

