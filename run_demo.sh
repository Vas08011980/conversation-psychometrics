#!/usr/bin/env bash
# Full demo on simulated data: simulate -> pipeline -> tests (about 1 minute)
set -e
python3 simulate/simulate.py --n 60 --days 14 --seed 2026 --out demo/data
python3 pipeline/pipeline.py --exports demo/data/exports --anchors anchors.yaml --out demo/out --encoder lsa
Rscript tests/tests.R demo/out demo/data
