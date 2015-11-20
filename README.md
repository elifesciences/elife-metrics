# elife-metrics
 
A data store and API for accessing the article level metrics that power the 
graphs on the elifesciences.org article metrics page.

## installation

    ./install.sh

## usage (development)

Load the stats contained in the `elife-ga-metrics` repository.
    
    ./manage.sh import_metrics
    
Run the development server

    ./manage.sh runserver
    
Visit the Swagger documentation
    
    firefox http://127.0.0.1/api/docs/

## Copyright & Licence
 
Copyright 2015 eLife Sciences. Licensed under the [GPLv3](LICENCE.txt)

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

