"""Test A sensitivity (D16): one ID per person (bioguide) instead of one per ICPSR.

The PREREG Test A result (output/step3_*) is primary and is not changed. The LES panel gives a
party switcher a second ICPSR, so α_i splits one person into two units. Here the Step 3 code is
run unchanged (same X_it, B, seed and rules) on House and Senate panels whose id is the person
(bioguide, through Voteview). States use sles_id and are not affected. Test D keeps the Step 3
(ICPSR) outcome input.

Writes output/sensitivity/: step3_person_multi_icpsr.csv, step3_person_kappa.csv,
step3_person_oos.csv, step3_person_compare.csv, step3_person_results.json.

Usage: python -I step3_person_sensitivity.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
from load_data import load_all, ROOT
import step3_test_A as s3
from person_ids import bioguide_of_icpsr, to_person, multi_icpsr

OUT = ROOT / "output/sensitivity"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(s3.SEED)
    D = load_all()
    bio = bioguide_of_icpsr()
    prereg = json.loads((ROOT / "output/step3_results.json").read_text())["bodies"]
    multi, kap_rows, oos_rows, cmp, res = [], [], [], [], {"seed": s3.SEED, "B_kappa": s3.B_KAPPA, "B_r": s3.B_R}
    for body in ["House", "Senate"]:
        m = multi_icpsr(D[body], bio).assign(body=body)
        multi.append(m)
        df = to_person(D[body], bio)
        r, _ = s3.fit_df(df)
        assert not r["loglam_at_bound"]
        draws = s3.bootstrap_kappa(df, s3.B_KAPPA, rng)
        k_lo, k_hi = s3.ci(draws[:, 0])
        pairs = s3.oos_pairs(df, body)
        rb = s3.bootstrap_r(pairs, s3.B_R, rng)
        r_hat = float(np.corrcoef(pairs["alpha_hat_prior"], pairs["resid_t"])[0, 1])
        r_lo, r_hi = s3.ci(rb)
        kr = {"body": body, "n_rows": len(df), "n_persons": int(df["id"].nunique()),
              "sig2_alpha": r["sig2_alpha"], "sig2_eps": r["sig2_eps"], "sigma_alpha": float(np.sqrt(r["sig2_alpha"])),
              "kappa": r["kappa"], "kappa_lo": k_lo, "kappa_hi": k_hi}
        orow = {"body": body, "n_pairs": len(pairs), "n_persons": int(pairs["id"].nunique()),
                "r": r_hat, "r_lo": r_lo, "r_hi": r_hi}
        kap_rows.append(kr)
        oos_rows.append(orow)
        v = s3.verdict(r["kappa"], r_lo, r_hi)
        p = prereg[body]
        for version, n_units, k, klo, khi, rr, rlo, rhi, vv in [
                ("PREREG (one ID per ICPSR)", p["n_members"], p["kappa"], p["kappa_lo"], p["kappa_hi"],
                 p["oos_r"], p["oos_r_lo"], p["oos_r_hi"], p["prereg_verdict"]),
                ("sensitivity (one ID per person)", kr["n_persons"], kr["kappa"], k_lo, k_hi, r_hat, r_lo, r_hi, v)]:
            cmp.append({"body": body, "version": version, "n_rows": len(df), "n_units": n_units, "kappa": k,
                        "kappa_lo": klo, "kappa_hi": khi, "r": rr, "r_lo": rlo, "r_hi": rhi, "verdict": vv,
                        "kappa_ge_0_20": bool(k >= 0.20)})
        res[body] = {**kr, **{f"oos_{a}": b for a, b in orow.items() if a != "body"}, "verdict": v,
                     "prereg_verdict": p["prereg_verdict"], "verdict_changes": bool(v != p["prereg_verdict"]),
                     "kappa_side_of_0_20_changes": bool((kr["kappa"] >= 0.20) != (p["kappa"] >= 0.20)),
                     "persons_with_more_than_one_icpsr": len(m), "their_member_terms": int(m["member_terms"].sum()),
                     "their_icpsr_units": int(m["n_icpsr"].sum())}
        print(body, res[body], flush=True)
    pd.concat(multi).to_csv(OUT / "step3_person_multi_icpsr.csv", index=False)
    pd.DataFrame(kap_rows).to_csv(OUT / "step3_person_kappa.csv", index=False)
    pd.DataFrame(oos_rows).to_csv(OUT / "step3_person_oos.csv", index=False)
    pd.DataFrame(cmp).to_csv(OUT / "step3_person_compare.csv", index=False)
    (OUT / "step3_person_results.json").write_text(json.dumps(res, indent=2))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(cmp).to_string())


if __name__ == "__main__":
    main()
