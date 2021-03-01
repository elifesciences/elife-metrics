#!/bin/bash
# ensures the `./schema/api-raml` repository exists and matches the revision in `api.raml.sha1`
# assumes the contents of `./schema/api-raml/dist` are the latest compiled version

set -e # everything must pass

mkdir -p schema
(
    cd schema
    if [ ! -d api-raml ]; then
        git clone https://github.com/elifesciences/api-raml
    fi
)

if [ -f api-raml.sha1 ]; then
    sha="$(cat api-raml.sha1)"
    (
        cd schema/api-raml/
        git reset --hard
        git fetch
        git checkout "$sha"
    )
fi
