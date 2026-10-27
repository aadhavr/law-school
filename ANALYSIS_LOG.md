# ANALYSIS_LOG.md: deviations, decisions and exploratory analyses relative to PREREG.md

PREREG results (Step 3 Test A; Step 4 JD rule) are primary. Nothing labeled EXPLORATORY below changes them.

## A. Every deviation from PREREG.md

| # | What PREREG.md says | What was done | When it was decided |
|---|---|---|---|
| D1 | X_it = seniority, party, majority status, committee chair | First Step 3 run added a chamber term to the States model and fit three unlisted variants. That run was discarded (`archive/discarded_run1/`, see its NOTE.md). The current run uses the PREREG list exactly. | Before any result was reported |
| D2 | JD rule: regress α̂_i on "background variables" (not listed) | I chose the controls: doctorate (`phd_ind`), female, Black, Hispanic (CLASS). | Before seeing coefficients |
| D3 | (no rule) | A background term other than law degree enters only if ≥ 10 members in that chamber's sample hold it. This drops doctorate, Black and Hispanic from the Senate model. | **After seeing the counts**, before seeing coefficients |
| D4 | JD sample not stated | Step 4 can use only CLASS 1.9, which covers Congresses 106–110. α̂_i comes from the full LES 1.0 panel (93–118). | Forced by data |
| D5 | "JD" | `law_ind` (law degree) is the JD variable. It covers any law degree recorded in CLASS, not only the JD. | Before regression; see Step 4 notes |
| D6 | Economics PhD | Defined as `phd_ind` = 1 and the doctorate field contains "econom". `phd_ind` also counts Ed.D. and Ed.S.; 13 doctorates have a blank field. | Before counting |
| D7 | Claim A rule uses κ | Applied to the point estimate of κ, as PREREG says. The House κ 95% CI lower bound is 0.19987, below 0.20. | Rule as written |
| D9 | Effects "in units of σ_α", without saying which σ_α | Every law effect is now reported three ways (`output/exploratory/expl_law_units.csv`, post tables): (1) LES points; (2) units of the full-panel σ̂_α from Step 3 (House 0.600, Senate 0.427); (3) units of the σ̂_α of the PREREG model fit on the analysis sample's own terms. **The PREREG threshold (0.20σ_α) and the power at it use (2).** For Step 4, (2) is the PREREG result itself (σ̂_α re-estimated in each bootstrap draw). For E1/E2, (2) divides by the fixed full-panel estimate, because E1/E2 resample only CLASS members; its CI ignores uncertainty in σ̂_α. The earlier E1 numbers in sample units (e.g. House +0.194) are unchanged but are no longer the headline unit. | 2026-10-27, after the results were seen |
| D10 | (not in the original PREREG) | **New test, not a change to any test.** Test D (what α_i contains) was added as PREREG.md "Amendment 1: Test D" on 2026-10-27. It was written after the Test A and skill-source results were seen and before any Test D data was downloaded or loaded. Tests A, B, C and the combining rule are unchanged, and Test D does not enter the combining rule. Its own rule (99% CI of γ excludes 0 and \|γ\| ≥ 0.060 LES points) is fixed in the amendment. Committed to git before any data download (see section E). | 2026-10-27, after A and skill-source results; before Test D data |
| D11 | Amendment 1 named GovTrack as the source for (b) and (c); (d) had no source; the total share included all predictors | PREREG.md "Amendment 1a" (2026-10-27): (b) and (c) come from govinfo BILLSTATUS 108–117 (hr, hjres), so they cover t = 109–118. The reason is data availability only, because GovTrack blocks automated access. (a) is judged on its full sample and also run on t = 109–118 for comparison. (d) comes from the CLASS 1.9 state-legislature spells, counting years before the first House term; first terms are kept, and the sample is members of Congresses 106–110. The total share uses (a)+(b)+(c) only, and (d) is reported alone. A design-based power analysis (no outcome used) is written to output/ before any γ is estimated. | 2026-10-27, after the source check; before any bill data was downloaded or any Test D model was fit |
| D8 | Tests B, C and the lockdown replication | Not run yet. ABA and IGM data need manual download (`MANUAL_DOWNLOADS.md`). The combining rule cannot be evaluated until they are done. | — |

### Implementation choices PREREG.md does not specify (not deviations, listed for completeness)
- Party coded D (reference), R, Other. Rows with a missing ICPSR or covariate dropped (House: 127 delegate rows; States: 1,658 rows, including SLES `comm_chair` = ".", which the codebook does not define).
- States: t = term start year. Each body fit separately.
- REML fit; α̂_i = BLUP. Bootstrap: percentile 95% CIs, resampling members, B = 1000 for κ and Step 4, B = 2000 for r. Seeds are in each script.
- Out-of-sample: for each t, the model is fit on all rows with t′ < t; α̂_i is the BLUP from that fit; residual LES at t uses that fit's β̂.
- Step 4 units: σ̂_α from the PREREG model on the full chamber panel (House 0.600, Senate 0.427).
- 5 of 788 CLASS people have no LES 1.0 record (ICPSR 94879, 99542, 99767, 928489, 928490).

### Checks (not analyses)
- `step3_validation.csv`: the fast REML estimator agrees with statsmodels MixedLM.
- Step 3 and Step 4 were each run twice from scratch; all output files byte-identical.

## B. Step 4 notes
- **`law_ind` = law degree, not lawyer occupation.** The Carnes Ch. 1 appendix, p. 4, describes "indicators for whether each member held a law degree, MBA, medical degree, master's degree, or PhD". `law_ind` = 1 for exactly the 1,153 rows with a law school recorded. It differs from occupation codes 1–4 (lawyer): 96 rows have the degree but no lawyer occupation; 34 have the occupation but no degree.

## C. EXPLORATORY analyses (not in PREREG.md; requested 2026-10-26)
Outputs in `output/exploratory/`. Code: `code/explore_law_mixed.py` (E1, E2, E4, E5), `code/explore_rank_house.py` (E3).

- **E1. Law degree inside the mixed model.** LES_it = X_it·β + γ·LAW_i + α_i + ε_it. Sample: CLASS people matched to LES 1.0 (783 of 788) with all their LES 1.0 terms, House and Senate fit separately (LES is scaled within chamber): House 699 members / 5,808 rows; Senate 166 / 1,522. Units: γ / σ̂_α, where σ̂_α is from the PREREG model on this same sample (House 0.462, Senate 0.396). These are not the full-panel σ̂_α used in Step 4, so E1 and Step 4 numbers are in different units.
- **E2. Lawyer occupation** (any CLASS occupation code 1–4), alone and together with the degree. Degree and occupation overlap heavily (House: 257 both, 22 degree only, 10 occupation only).
- **E3. House Test A on an inverse-normal rank transform** of LES within each Congress (Blom). Same X_it, B and code as Step 3.
- **E4. Bootstrap standard error** (SD of bootstrap draws) and the smallest effect with 80% power (two-sided, α = 0.05: 2.80 × the bootstrap standard error) for each law effect, in all three D9 units. Power at the PREREG threshold is computed once per effect, at 0.20 × full-panel σ̂_α (House 0.120 LES points, Senate 0.085). The PREREG Step 4 bootstrap (House and Senate) was replayed with its own seed; the replayed estimates and CIs equal `output/step4_coefs.csv`. Caveat: the Step 4 estimand is attenuated by BLUP shrinkage.
- **Joint model (E2, both terms).** Degree and occupation are almost the same people (House: 257 both, 22 degree only, 10 occupation only), so their separate coefficients are not interpretable. The post does not report them as findings; they stay in `expl_law_mixed.csv` and `expl_law_units.csv` only.
- **E5. Wilson 95% CI** for the share with an economics PhD, for 3/788 (all CLASS people) and 3/783 (matched).
- **Archived, never reported:** the three variants in `archive/discarded_run1/step3_sensitivity.csv`.

## D. Step 6 verification (2026-10-27)
- `code/run_all.sh` deleted `output/` and re-ran every script in order, then rendered `post.qmd` and ran `code/step6_verify.py`.
- Compared with a copy taken just before the re-run, every output file is byte-identical, as are `_variables.yml`, `post.html`, `DATA_SOURCES.md` and `TABLE_COLUMNS.md`. The only difference is the run-time lines in `step3_log.txt`. New files: `step5_data_counts.json` (raw-data counts the post cites, now saved to output/), `step6_verify.md`, `exploratory/expl_law_log.txt`.
- `output/step6_verify.md`: 70 distinct variables, 9 tables and 5 figures all resolve. All 209 distinct numbers in the rendered post trace to output/, PREREG.md, a code constant or CLASS itself. 88 key values, including every PREREG verdict, were recomputed by separate code and all matched.
- Before the fix, 7 numbers had no source in output/. Three were counts computed from raw data but not saved (127, 1,153, 34): now saved. Two were derived thresholds in LES points (0.120, 0.085): now derived explicitly in the verifier. One was the post date, and one was a "deviation 6" cross-reference, now checked against the list.

## E. Amendment 1: Test D (D10)
- Commit "state before Test D" holds every code, output, note and post file as they were before Test D.
- A second commit holds PREREG.md (with Amendment 1) and this log, made before any Test D data was downloaded.
- The amendment pins down choices the request left open:
  - the network measure (PageRank, damping 0.85; cosponsor → sponsor edges; hr and hjres; withdrawn cosponsorships excluded);
  - the party definition (Voteview party_code in t−1);
  - lagged predictors require House service in t−1;
  - the 99% CI uses a member bootstrap with B = 2000;
  - s_z is computed on each fit's own rows;
  - what happens if GovTrack data is only partly available.
- Amendment 1a (D11) was committed and pushed before the BILLSTATUS files were downloaded.
