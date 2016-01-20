# elife-metrics

An effort by [eLife Sciences](http://elifesciences.org) to provide a data store 
and API for accessing the article level metrics.

[Github repo](https://github.com/elifesciences/elife-metrics/).

API documentation can be found here:

* [code](https://github.com/elifesciences/elife-metrics/blob/master/src/metrics/api.py)
* [Swagger](https://metrics.elifesciences.org/api/docs/) (or your [local version](/api/docs/))

For example, the [Homo Naledi](http://elifesciences.org/content/4/e09560) article:

* [http://metrics.elifesciences.org/api/v1/article/hw,ga/10.7554/eLife.09560/](http://metrics.elifesciences.org/api/v1/article/hw,ga/10.7554/eLife.09560/)

## installation

[code](https://github.com/elifesciences/elife-metrics/blob/master/install.sh) 

    git clone https://github.com/elifesciences/elife-metrics
    cd elife-metrics
    ./install.sh

## updating

[code](https://github.com/elifesciences/elife-metrics/blob/master/install.sh)  

    ./install.sh

## testing 

[code](https://github.com/elifesciences/elife-metrics/blob/master/src/metrics/tests/)  

    ./test.sh

## running

[code](https://github.com/elifesciences/elife-metrics/blob/master/manage.sh)

    ./manage.sh runserver
    firefox http://127.0.0.1:8000/api/docs/

## importing metrics (development)

[code](https://github.com/elifesciences/elife-metrics/blob/master/src/metrics/management/commands/import_metrics.py)

Load daily metrics for the last two days and monthly metrics for the last two months:

    ./import-metrics.sh

Load all the metrics you can:

    ./import-all-metrics.sh

## Copyright & Licence
 
Copyright 2016 eLife Sciences. Licensed under the [GPLv3](LICENCE.txt)

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

