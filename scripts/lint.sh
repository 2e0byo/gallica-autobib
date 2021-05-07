#!/usr/bin/env bash

set -e
set -x

black gallica_autobib tests --check
isort --multi-line=3 --trailing-comma --force-grid-wrap=0 --combine-as --line-width 88 --recursive --check-only --thirdparty gallica_autobib gallica_autobib tests
mypy gallica_autobib --disallow-untyped-defs
