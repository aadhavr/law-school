"""Test D, post-result note (2026-11-07): planned σ̂_γ̂ versus the realized bootstrap SE.

Not part of the Test D rule. Planned σ̂_γ̂ (testD_power.csv) used the full-panel Step 3 House
variance components. Here, for each predictor, the PREREG model without z is refit on that
predictor's own rows to get σ̂²_α and σ̂²_ε there, and the GLS σ̂_γ̂ is recomputed with those
components. Compared with the realized bootstrap standard error (testD_results.csv, boot_se).

Writes output/testD/testD_planning_check.csv.
Usage: python -I testD_planning_check.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
from load_data import load_house, clean, ROOT
from step3_test_A import design
import remlfit
import testD_design as td

OUT = ROOT / "output/testD"


def main():
    panel = clean(load_house()).merge(pd.read_csv(OUT / "testD_predictors.csv"), on=["id", "t"], validate="one_to_one")
    pw = pd.read_csv(OUT / "testD_power.csv").set_index("sample")
    rs = pd.read_csv(OUT / "testD_results.csv").set_index("sample")
    rows = []
    for smp, z in [("a_full", "a_dist_median"), ("a_t109_118", "a_dist_median"), ("b", "b_pagerank"),
                   ("c", "c_cross_share"), ("d", "d_state_leg_years")]:
        m = panel[z].notna() & (panel["t"].between(109, 118) if smp == "a_t109_118" else True)
        df = panel[m].sort_values(["id", "t"]).reset_index(drop=True)
        X, names = design(df)
        X, _ = remlfit.drop_constant_columns(X, names)
        r = remlfit.fit(df["les"].to_numpy(float), X, df["id"].to_numpy())
        se_own, _, _, _ = td.gls_se(df, z, r["sig2_alpha"], r["sig2_eps"])
        planned, boot = float(pw.loc[smp, "se_gamma_gls"]), float(rs.loc[smp, "boot_se"])
        rows.append({"sample": smp, "predictor": z, "n_member_terms": len(df),
                     "sig2_alpha_full_panel": td_s2()[0],
                     "sig2_eps_full_panel": td_s2()[1],
                     "sig2_alpha_own_rows": float(r["sig2_alpha"]), "sig2_eps_own_rows": float(r["sig2_eps"]),
                     "se_planned_gls_full_panel": planned, "se_gls_own_rows": se_own, "se_bootstrap_realized": boot,
                     "ratio_realized_to_planned": boot / planned, "ratio_realized_to_own_rows_gls": boot / se_own})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "testD_planning_check.csv", index=False)
    pd.set_option("display.width", 250)
    print(out.round(5).to_string())


def td_s2():
    k = pd.read_csv(ROOT / "output/step3_kappa.csv").set_index("body").loc["House"]
    return float(k["sig2_alpha"]), float(k["sig2_eps"])


if __name__ == "__main__":
    main()
