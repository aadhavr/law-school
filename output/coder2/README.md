# Coder 2 sheets (Test B, PREREG.md Amendments 2 and 2a)

Code each row on your own, without looking at coder 1's codes, the code in `code/testB_*.py`, or
`ANALYSIS_LOG.md` section F. **Finish sheet 1 before you open sheet 2.** Save the completed files,
with the same names and columns, in `output/coder2/returned/`.

## Sheet 1: `sheet1_filter.csv` (30 rows)
Fill `policy_flag` with `yes` or `no`, using the rule (also in each row):

> The statement proposes or evaluates a specific US federal measure that Congress, an agency, or the president could enact, change, or repeal, and the favored direction is clear. Exclude claims about the past or causes, forecasts, theory, other countries, and state or local measures.

## Sheet 2: `sheet2_adoption.csv` (10 rows)
Judge adoption as of 2026-11-07.

- `adopted_any_time`: `yes`, `no` or `unclear`. Adopted: a federal law, rule, regulation, or executive measure was in force at any time within 10 years after the statement date, in substantially the form the statement describes. Each code needs a source URL and a date. If it is unclear, code "unclear".
- `adopted_still_in_force`: `yes`, `no` or `unclear`: whether that measure is still in force on 2026-11-07.
- `source_url` and `source_date`: the source for your code, and its date (YYYY-MM-DD).
- `cause_code` (only if `adopted_any_time` is `no`): one of: knowledge gap; blocked by interests or veto players; no actor with the skill to act.
