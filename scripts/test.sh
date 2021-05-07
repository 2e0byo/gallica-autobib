#!/usr/bin/env bash

set -e
set -x

pytest --cov=gallica_autobib --cov=tests --cov-report=term-missing ${@}
bash ./scripts/lint.sh
