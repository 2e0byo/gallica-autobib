#!/usr/bin/env bash

set -e
set -x

mypy gallica-autobib --disallow-untyped-defs
black gallica-autobib tests --check
isort --multi-line=3 --trailing-comma --force-grid-wrap=0 --combine-as --line-width 88 --recursive --check-only --thirdparty gallica-autobib gallica-autobib tests
