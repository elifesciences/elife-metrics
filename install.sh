#!/bin/bash
set -e # everything must succeed.
echo "[-] install.sh"

. download-api-raml.sh

# use the latest version of python3 we can find. 
# on Ubuntu14.04 the stable version is 3.3, the max we can install is 3.6

. mkvenv.sh

source venv/bin/activate
pip install -r requirements.lock

if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi

# remove any old compiled python files
# pylint likes to lint them
find src/ -name '*.py[c|~]' -delete
find src/ -regex "\(.*__pycache__.*\|*.py[co]\)" -delete

python src/manage.py migrate --no-input

echo "[✓] install.sh"
