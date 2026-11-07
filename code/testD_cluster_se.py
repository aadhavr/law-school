"""Test D, post-result note (2026-11-07): cluster-robust standard error of γ̂ for (b) and (d).

Not part of the Test D rule; changes no verdict. For (d) the realized bootstrap SE is below the
planned GLS σ̂_γ̂, and for (b) it is 1.32 times the plan. A model-based GLS SE assumes the same
σ²_α and σ²_ε for every member. A cluster-robust SE (clusters = members) does not. If the gap is
from variance that is unequal across members, the cluster-robust SE should track the bootstrap SE.

Method: the Test D model for that predictor (testD_models.fit, s_z on the fit's own rows), REML λ̂.
At λ̂ the model is quasi-demeaned (remlfit._transform), which makes GLS into OLS. Then
    V_CR = (X*'X*)⁻¹ [Σ_i X*_i' e*_i e*_i' X*_i] (X*'X*)⁻¹,
with CR1 scaling G/(G−1)·(N−1)/(N−p) (reported) and CR0 (no scaling) next to it.
The model-based SE on the same fit, σ̂²_ε (X*'X*)⁻¹, is also reported.

Rule written before this was computed, for the post's wording only: the check "supports" the
unequal-variance reason for a predictor if the CR1 SE moves from the model-based SE toward the
bootstrap SE, in the same direction, by at least half of the gap between them. Otherwise the
reason is labeled a guess.

Writes output/testD/testD_cluster_se.csv. Usage: python -I testD_cluster_se.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
from load_data import load_house, clean, ROOT
from step3_test_A import design
import remlfit

OUT = ROOT / "output/testD"
SAMPLES = [("b", "b_pagerank"), ("d", "d_state_leg_years")]
D_FLAG = 0.0235  # user instruction: report if the (d) cluster-robust SE is above this


def cluster_se(df, z):
    X, names = design(df)
    X = np.column_stack([X, df[z].to_numpy(float) / df[z].to_numpy(float).std(ddof=1)])
    X, kept = remlfit.drop_constant_columns(X, names + [z])
    assert kept[-1] == z
    y, ids = df["les"].to_numpy(float), df["id"].to_numpy()
    r = remlfit.fit(y, X, ids)
    assert not r["loglam_at_bound"]
    g, n = remlfit._group_index(ids)
    lam = r["sig2_alpha"] / r["sig2_eps"]
    ys, Xs = remlfit._transform(y, X, g, n, lam)
    bread = np.linalg.inv(Xs.T @ Xs)
    beta = bread @ Xs.T @ ys
    assert np.allclose(beta, r["beta"])
    e = ys - Xs @ beta
    G, (N, p) = len(n), X.shape
    S = np.zeros((G, p))
    np.add.at(S, g, Xs * e[:, None])
    v0 = bread @ (S.T @ S) @ bread
    c1 = G / (G - 1) * (N - 1) / (N - p)
    return {"gamma_les": float(beta[-1]), "n_members": G, "n_member_terms": N,
            "se_model_based": float(np.sqrt(r["sig2_eps"] * bread[-1, -1])),
            "se_cluster_cr0": float(np.sqrt(v0[-1, -1])), "se_cluster_cr1": float(np.sqrt(c1 * v0[-1, -1]))}


def main():
    panel = clean(load_house()).merge(pd.read_csv(OUT / "testD_predictors.csv"), on=["id", "t"], validate="one_to_one")
    pc = pd.read_csv(OUT / "testD_planning_check.csv").set_index("sample")
    rs = pd.read_csv(OUT / "testD_results.csv").set_index("sample")
    rows = []
    for smp, z in SAMPLES:
        df = panel[panel[z].notna()].sort_values(["id", "t"]).reset_index(drop=True)
        c = cluster_se(df, z)
        assert np.isclose(c["gamma_les"], rs.loc[smp, "gamma_les"])
        boot, mb, cr = float(rs.loc[smp, "boot_se"]), c["se_model_based"], c["se_cluster_cr1"]
        moved = (cr - mb) / (boot - mb)  # share of the model-based → bootstrap gap closed
        rows.append({"sample": smp, "predictor": z, **c,
                     "se_planned_gls_full_panel": float(pc.loc[smp, "se_planned_gls_full_panel"]),
                     "se_gls_own_rows": float(pc.loc[smp, "se_gls_own_rows"]),
                     "se_bootstrap_realized": boot, "share_of_gap_closed_by_cr1": moved,
                     "supports_unequal_variance": bool(moved >= 0.5)})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "testD_cluster_se.csv", index=False)
    pd.set_option("display.width", 250)
    print(out.round(5).T.to_string())
    d = out.set_index("sample").loc["d", "se_cluster_cr1"]
    if d > D_FLAG:
        print(f"FLAG: (d) cluster-robust SE {d:.4f} is above {D_FLAG}")


if __name__ == "__main__":
    main()
