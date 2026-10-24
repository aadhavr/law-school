# Pre-registration: "should i go to law school"
Written: 2026-10-24, before any model was run on the LES data.

## Data and version
- LES 1.0 for House and Senate (Congresses 93 to 118). SLES for states.
- Primary sample: House. Senate and states are secondary and reported separately.
- I will not switch the LES version after seeing results.

## Test A: Is individual skill a distinct trait?
Model: LES_it = X_it·β + α_i + ε_it. X_it holds seniority, party, majority status, committee chair.
κ = σ²_α / (σ²_α + σ²_ε). I also report the share of Var(LES_it) explained by X_it.
Out-of-sample check: estimate α̂_i from terms before t. Predict the residual LES at t.
Report Pearson r with a 95% CI from a bootstrap over members.

Decision rule (House, primary):
- Claim A supported as a measurable trait: κ ≥ 0.20, AND the 95% CI of r excludes 0.
- Claim A weak: 0.10 ≤ κ < 0.20, or the CI of r includes 0.
- Claim A not supported: κ < 0.10.
Note: a large κ shows that skill differs between people. It does not show that skilled people are scarce.

## Skill source: Does a JD predict skill?
Regress α̂_i on background variables. Bootstrap over members to account for the fact that α̂_i is estimated.
Express each effect in units of σ_α.
- JD favors law school as a skill source: estimated effect ≥ 0.20σ_α, AND the 95% CI lower bound > 0.
- No evidence for a JD skill premium: the CI includes 0, or the estimate is < 0.10σ_α.
- Effects between these are reported as inconclusive.
Limit: this is descriptive. People who choose law school differ from people who do not.
Economics PhD effect: reported only if at least 30 members hold one. Otherwise it is not estimated.

## Test B: Are consensus answers unused?
- Consensus rule: IGM weighted agreement ≥ 80% (agree or strongly agree).
- Adopted: a national US measure in force within 10 years of the panel statement, and still in force.
- π̂ = share adopted. I report a Wilson 95% CI.
- Fewer than 20 policies: results are descriptive only, with no verdict.
- With 20 or more: "most consensus answers go unused" is supported if the CI upper bound < 0.5.
- Cause of non-adoption is coded as: knowledge gap, blocked by interests or veto players, or no actor with the skill to act.
- A second coder codes a random sample of at least 10 policies. I report Cohen's kappa (κ_C, not the κ above).
- If κ_C < 0.6, I report the cause coding as unreliable.

## Test C: Which path leads to a policy role?
r = [P(JD | role) / P(econ PhD | role)] × [N_PhD / N_JD], using the same cohort years for both pools.
- Favors JD: r ≥ 2.
- Favors PhD: r ≤ 0.5.
- Between 0.5 and 2: inconclusive.
Limit: descriptive ratio, not a causal effect.

## Lockdown data (Wehner and Hallerberg)
- First replicate Table A5 column (1) of their appendix. Report any difference from their numbers.
- If a law-trained leader indicator can be built, I report its HR and 95% CI and the number of such leaders. No threshold. The sample will be small.

## How the results combine
The data supports "go to law school" only if ALL of these hold: κ ≥ 0.20, the JD effect rule is met, and r ≥ 2.
If any fails, the data gives no recommendation for law school. The decision then rests on cost, time, and reversibility, which this project does not measure.

## Commitments
- All analyses are listed above. Anything else is labeled exploratory in the post.
- I will not change a threshold after seeing a result.