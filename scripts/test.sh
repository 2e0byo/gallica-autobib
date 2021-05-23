#!/usr/bin/env bash

set -e
set -x

pytest --cov=gallica_autobib --cov=tests --cov-report=term-missing ${@} --cov-report xml --cov-config .coveragerc --cov-branch
bash ./scripts/lint.sh
