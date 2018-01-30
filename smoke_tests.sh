#!/usr/bin/env bash
. /opt/smoke.sh/smoke.sh

smoke_url $(hostname)/
smoke_url $(hostname)/api/v2/ping
    smoke_assert_body "pong"

smoke_report
