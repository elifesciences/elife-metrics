#!/bin/bash
set -e # everything must succeed.
echo "[-] install.sh"

. download-api-raml.sh

# use the latest version of python3 we can find. 
# on Ubuntu14.04 the stable version is 3.3, the max we can install is 3.6

# ll: /usr/bin/python3.6
#maxpy=$(which /usr/bin/python3* | grep -E '[0-9]$' | sort -r | head -n 1)
maxpy=/usr/bin/python3.5

# ll: python3.6
# http://stackoverflow.com/questions/2664740/extract-file-basename-without-path-and-extension-in-bash
py=${maxpy##*/} # magic

# check for exact version of python
if [ ! -e "venv/bin/$py" ]; then
    echo "could not find venv/bin/$py, recreating venv"
    rm -rf venv
    virtualenv --python="$maxpy" venv
fi
source venv/bin/activate
if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi
pip install -r requirements.txt
python src/manage.py migrate --no-input

echo "[✓] install.sh"
