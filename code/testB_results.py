"""Test B results: κ_C and π (PREREG Test B; Amendments 2, 2a, 2b, 2c; log D17, D19, D21–D23).

Inputs
  data/derived/igm/test_b_policy_filter.csv     coder 1 policy filter (pool numbers)
  output/coder1_private/coder1_adoption.csv     coder 1 adoption codes (revealed 2026-11-07)
  output/coder2/returned/sheet1_filter.csv      coder 2 policy filter (30 rows)
  output/coder2/returned/sheet2_adoption.csv    coder 2 adoption codes (10 policies)
  output/coder2_key/row_key.csv                 row_id -> pool_no

κ_C (Cohen's kappa, unweighted):
  (1) policy filter, 30 rows, categories yes/no;
  (2) adoption any time, 10 rows, categories yes/no/unclear;
  (3) cause code, rows where both coders coded adoption any time = no.
  PREREG: if κ_C < 0.6 the cause coding is reported as unreliable.

Counting (D19 / Amendment 2a): primary set = coder 1 policy = yes, and coder 2 yes where coder 2 coded it.
Sensitivity set = either coder yes. Fewer than 20 in the primary set: descriptive only. Wilson 95% CI
for the sensitivity set only if it has 20 or more policies (exploratory).

Adoption rules (Amendment 2c), for adopted any time and still in force:
  main: coder 1, unclear = adopted; S1: coder 1, unclear = not adopted;
  S2: both coders adopted (unclear = adopted for each); S3: either coder adopted (unclear = adopted);
  S2/S3 use coder 1's code where coder 2 did not code the policy.
Policy type (Amendment 2b): preserve-type = pool 53 and pool 85; all others change-type.

Writes output/testB/. Usage: python -I testB_results.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportion_confint

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "testB"
PRESERVE = {53, 85}
CAUSES = ["knowledge gap", "blocked by interests or veto players", "no actor with the skill to act"]
MIN_POLICIES = 20


def cohen_kappa(a, b, cats):
    a, b = list(a), list(b)
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    k = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    return {"n": n, "pct_agree": po, "p_expected": pe, "kappa": k}


def adopted(code, unclear_as):
    return code == "yes" or (code == "unclear" and unclear_as)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    key = pd.read_csv(ROOT / "output/coder2_key/row_key.csv")
    f1 = pd.read_csv(ROOT / "data/derived/igm/test_b_policy_filter.csv")
    c1 = pd.read_csv(ROOT / "output/coder1_private/coder1_adoption.csv", dtype={"pool_no": int})
    s1 = pd.read_csv(ROOT / "output/coder2/returned/sheet1_filter.csv", dtype=str).merge(key, on="row_id")
    s2 = pd.read_csv(ROOT / "output/coder2/returned/sheet2_adoption.csv", dtype=str).merge(key, on="row_id")
    assert len(s1) == 30 and len(s2) == 10

    # ---- κ_C ----
    filt = s1[["row_id", "pool_no", "policy_flag"]].rename(columns={"policy_flag": "c2"}).merge(
        f1[["pool_no", "policy_flag"]].rename(columns={"policy_flag": "c1"}), on="pool_no")
    k_filter = cohen_kappa(filt.c1, filt.c2, ["yes", "no"])
    ad = s2[["row_id", "pool_no", "adopted_any_time", "adopted_still_in_force", "source_url", "source_date",
             "cause_code"]].add_suffix("_c2").rename(columns={"row_id_c2": "row_id", "pool_no_c2": "pool_no"}).merge(
        c1[["pool_no", "adopted_any_time", "adopted_still_in_force", "source_url", "source_date", "cause_code",
            "note"]].add_suffix("_c1").rename(columns={"pool_no_c1": "pool_no"}), on="pool_no")
    assert len(ad) == 10
    k_adopt = cohen_kappa(ad.adopted_any_time_c1, ad.adopted_any_time_c2, ["yes", "no", "unclear"])
    both_no = ad[(ad.adopted_any_time_c1 == "no") & (ad.adopted_any_time_c2 == "no")]
    k_cause = cohen_kappa(both_no.cause_code_c1, both_no.cause_code_c2, CAUSES)
    kap = pd.DataFrame([{"measure": "policy filter", "categories": "yes/no", **k_filter},
                        {"measure": "adoption any time", "categories": "yes/no/unclear", **k_adopt},
                        {"measure": "cause code (both coders: not adopted)", "categories": "3 PREREG causes", **k_cause}])
    kap.to_csv(OUT / "testB_kappa.csv", index=False)
    # PREREG: κ_C < 0.6 -> cause coding unreliable. An undefined κ (all rows in one category for both
    # coders, p_expected = 1) is reported as undefined; PREREG gives no rule for it.
    kc = k_cause["kappa"]
    cause_status = ("undefined: PREREG rule cannot be applied" if np.isnan(kc)
                    else "unreliable (κ_C < 0.6)" if kc < 0.6 else "κ_C ≥ 0.6")
    print(kap.to_string(index=False))

    # Side-by-side reveal (filter and adoption).
    filt.merge(f1[["pool_no", "statement"]], on="pool_no").sort_values("pool_no").to_csv(
        OUT / "testB_filter_side_by_side.csv", index=False)
    ad.sort_values("pool_no").to_csv(OUT / "testB_adoption_side_by_side.csv", index=False)
    # Revealed after coder 2's sheets were returned (2026-11-07): coder 1's full adoption codes, all 24 rows.
    c1.sort_values("pool_no").to_csv(OUT / "testB_coder1_adoption_revealed.csv", index=False)
    s1.sort_values("pool_no").to_csv(OUT / "testB_coder2_filter_returned.csv", index=False)
    s2.sort_values("pool_no").to_csv(OUT / "testB_coder2_adoption_returned.csv", index=False)

    # ---- Counting (D19) ----
    c2yes = set(filt.loc[filt.c2 == "yes", "pool_no"])
    c2no = set(filt.loc[filt.c2 == "no", "pool_no"])
    kept = f1[f1.kept_as_policy == "yes"]
    primary = sorted(p for p in kept.pool_no if p not in c2no)
    sens = sorted(set(kept.pool_no) | c2yes)
    missing = [p for p in sens if p not in set(c1.pool_no)]
    assert not missing, f"no coder-1 adoption code for {missing}"

    c2map = s2.set_index("pool_no")
    rows = []
    for setname, pools in [("primary", primary), ("sensitivity (either coder)", sens)]:
        for outcome in ["adopted_any_time", "adopted_still_in_force"]:
            for scope in ["all", "change-type"]:
                ps = [p for p in pools if scope == "all" or p not in PRESERVE]
                for rule in ["main", "S1", "S2", "S3"]:
                    k = 0
                    for p in ps:
                        a1 = c1.set_index("pool_no").loc[p, outcome]
                        a2 = c2map.loc[p, outcome] if p in c2map.index else None
                        if rule == "main":
                            y = adopted(a1, True)
                        elif rule == "S1":
                            y = adopted(a1, False)
                        elif a2 is None:
                            y = adopted(a1, True)
                        elif rule == "S2":
                            y = adopted(a1, True) and adopted(a2, True)
                        else:
                            y = adopted(a1, True) or adopted(a2, True)
                        k += y
                    n = len(ps)
                    r = {"set": setname, "outcome": outcome, "scope": scope, "rule": rule, "n_policies": n,
                         "n_adopted": k, "pi": k / n, "wilson_lo": np.nan, "wilson_hi": np.nan,
                         "status": "descriptive only" if n < MIN_POLICIES else "test"}
                    if setname.startswith("sensitivity") and n >= MIN_POLICIES:
                        r["wilson_lo"], r["wilson_hi"] = proportion_confint(k, n, method="wilson")
                        r["status"] = "exploratory (Wilson CI)"
                    rows.append(r)
    pi = pd.DataFrame(rows)
    pi.to_csv(OUT / "testB_pi.csv", index=False)
    print(pi.to_string(index=False))

    # Cause codes (coder 1) for primary-set policies not adopted any time (main rule).
    c1p = c1.set_index("pool_no").loc[primary]
    cause = c1p.loc[c1p.adopted_any_time == "no", "cause_code"].value_counts().reindex(CAUSES, fill_value=0)
    res = {"kappa": kap.set_index("measure").to_dict(orient="index"), "cause_status": cause_status,
           "primary_pools": primary, "sensitivity_pools": sens, "n_primary": len(primary), "n_sensitivity": len(sens),
           "coder2_added_pools": sorted(c2yes - set(kept.pool_no)),
           "n_change_primary": len([p for p in primary if p not in PRESERVE]),
           "coder1_cause_counts_primary_not_adopted": {k: int(v) for k, v in cause.items()},
           "wilson_reported": bool(len(sens) >= MIN_POLICIES)}
    (OUT / "testB_results.json").write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
