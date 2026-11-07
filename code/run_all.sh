#!/bin/zsh
# Step 6: re-run every analysis and generator from scratch, in order. Usage: zsh code/run_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
# Keep the coder sheets, the returned sheets and coder 1's private codes; rebuild everything else.
find output -mindepth 1 -maxdepth 1 ! -name coder2 ! -name coder2_key ! -name coder1_private -exec rm -rf {} +
mkdir -p output/exploratory
$PY -I code/write_data_sources.py
$PY -I code/write_table_columns.py
$PY -I code/step3_test_A.py > output/step3_log.txt 2>&1
$PY -I code/step4_skill_source.py > output/step4_log.txt 2>&1
mkdir -p output/testD
$PY -I code/testD_billstatus.py > output/testD/billstatus_log.txt 2>&1
$PY -I code/testD_design.py > /dev/null
$PY -I code/testD_models.py > output/testD/testD_models_log.txt 2>&1
$PY -I code/testD_planning_check.py > output/testD/testD_planning_check_log.txt 2>&1
$PY -I code/testD_cluster_se.py > output/testD/testD_cluster_se_log.txt 2>&1
mkdir -p output/sensitivity
$PY -I code/step3_person_sensitivity.py > output/sensitivity/step3_person_log.txt 2>&1
$PY -I code/step4_linked.py > output/step4_linked_log.txt 2>&1
$PY -I code/explore_law_mixed.py > output/exploratory/expl_law_log.txt 2>&1
$PY -I code/explore_rank_house.py > output/exploratory/expl_rank_log.txt 2>&1
$PY -I code/igm_build.py > /dev/null
$PY -I code/testB_pool.py
$PY -I code/testB_policy_filter.py > /dev/null
$PY -I code/testB_coder2_sheets.py
$PY -I code/step5_figures.py
$PY -I code/step5_numbers.py
quarto render post.qmd
$PY -I code/step6_verify.py
