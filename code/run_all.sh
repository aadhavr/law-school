#!/bin/zsh
# Step 6: re-run every analysis and generator from scratch, in order. Usage: zsh code/run_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
rm -rf output
mkdir -p output/exploratory
$PY -I code/write_data_sources.py
$PY -I code/write_table_columns.py
$PY -I code/step3_test_A.py > output/step3_log.txt 2>&1
$PY -I code/step4_skill_source.py > output/step4_log.txt 2>&1
$PY -I code/explore_law_mixed.py > output/exploratory/expl_law_log.txt 2>&1
$PY -I code/explore_rank_house.py > output/exploratory/expl_rank_log.txt 2>&1
$PY -I code/step5_figures.py
$PY -I code/step5_numbers.py
quarto render post.qmd
$PY -I code/step6_verify.py
