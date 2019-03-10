#!/bin/bash
set -e # everything must succeed.
echo "[-] install.sh"

. download-api-raml.sh

. mkvenv.sh

source venv/bin/activate

if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi

# remove any old compiled python files
# pylint likes to lint them
find src/ -name '*.py[c|~]' -delete
find src/ -regex "\(.*__pycache__.*\|*.py[co]\)" -delete

pip install -r requirements.txt
python src/manage.py migrate --no-input

echo "[✓] install.sh"
