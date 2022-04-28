#!/usr/bin/env bash

set -e
set -x

pytest -n auto --cov=gallica_autobib --cov=tests --cov-report=term-missing ${@} --cov-report xml --cov-report html --cov-config .coveragerc --cov-branch
bash ./scripts/lint.sh
