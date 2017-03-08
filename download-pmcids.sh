#!/bin/bash
set -exv
wget ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/PMC-ids.csv.gz
gunzip -f PMC-ids.csv.gz
head PMC-ids.csv -n 1 > elife-doi-pmcids.csv
cat PMC-ids.csv | grep '10.7554/eLife.' >> elife-doi-pmcids.csv
./manage.sh load_pmids elife-doi-pmcids.csv
rm PMC-ids.csv elife-doi-pmcids.csv
