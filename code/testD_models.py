"""Test D models (PREREG.md Amendments 1, 1a, 1b; design fixes D13, D14).

For each predictor z ∈ {(a), (b), (c), (d)}, on that predictor's rows of the Step 3 House panel
(LES 1.0, PREREG X_it, one random effect per LES-panel ICPSR as in Step 3):
    LES_it = X_it·β + γ·z_i,t−1/s_z + α_i + ε_it      (REML, code/remlfit.py)
s_z = sample SD (ddof = 1) of z over the fit's own rows, recomputed in every bootstrap draw.
99% CI: percentile, bootstrap over members (ICPSR), B = 2000, the model refit in every draw.
Rule: supported if the 99% CI excludes 0 and |γ̂| ≥ 0.060 LES points; otherwise "no evidence".
Descriptive: share of σ̂²_α explained = 1 − σ̂²_α(with z)/σ̂²_α(without z), both fit on the same
rows; and the total share for (a), (b), (c) together on the rows where all three are available.
(a) on t = 109–118 is for comparison only; the (a) verdict uses the full (a) sample.

Inputs: output/testD/testD_predictors.csv (testD_design.py), the House panel (load_data.py).
Writes output/testD/testD_results.csv, testD_total_share.csv, testD_results.json,
testD_gamma_draws.csv.

Usage: python -I testD_models.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
from load_data import load_house, clean, ROOT
from step3_test_A import design, member_blocks, resample_rows
import remlfit

OUT = ROOT / "output/testD"
SEED = 20261107
B = 2000
THRESHOLD = 0.060
SIGMA_ALPHA_FULL = 0.600  # Amendment 1: γ / 0.600 (full-panel σ̂_α from Step 3)
SAMPLES = [("a_full", "a_dist_median", "verdict"), ("a_t109_118", "a_dist_median", "comparison only"),
           ("b", "b_pagerank", "verdict"), ("c", "c_cross_share", "verdict"), ("d", "d_state_leg_years", "verdict")]
ABC = ["a_dist_median", "b_pagerank", "c_cross_share"]


def fit(df, zcols):
    """REML fit with X_it plus each z/s_z (s_z on df's own rows). Returns (γ̂ vector, σ̂²_α)."""
    X, names = design(df)
    zs = [df[z].to_numpy(float) / df[z].to_numpy(float).std(ddof=1) for z in zcols]
    X = np.column_stack([X] + zs)
    X, kept = remlfit.drop_constant_columns(X, names + list(zcols))
    assert kept[-len(zcols):] == list(zcols), kept
    r = remlfit.fit(df["les"].to_numpy(float), X, df["id"].to_numpy())
    assert not r["loglam_at_bound"]
    return r["beta"][-len(zcols):], float(r["sig2_alpha"])


def fit_base(df):
    X, names = design(df)
    X, _ = remlfit.drop_constant_columns(X, names)
    r = remlfit.fit(df["les"].to_numpy(float), X, df["id"].to_numpy())
    assert not r["loglam_at_bound"]
    return float(r["sig2_alpha"])


def verdict(g, lo, hi):
    return "supported" if (lo > 0 or hi < 0) and abs(g) >= THRESHOLD else "no evidence"


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    panel = clean(load_house())
    pred = pd.read_csv(OUT / "testD_predictors.csv")
    assert len(pred) == len(panel)
    panel = panel.merge(pred, on=["id", "t"], how="left", validate="one_to_one")
    rows, draws_out = [], {}
    for name, z, role in SAMPLES:
        if name == "a_t109_118":
            mask = panel[z].notna() & panel["t"].between(109, 118)
        else:
            mask = panel[z].notna()
        df = panel[mask].sort_values(["id", "t"]).reset_index(drop=True)
        g_hat, s2a_with = fit(df, [z])
        s2a_without = fit_base(df)
        start, count = member_blocks(df["id"].to_numpy())
        draws = np.empty(B)
        for b in range(B):
            r_idx, new_id = resample_rows(start, count, rng)
            bp = df.iloc[r_idx].copy()
            bp["id"] = new_id
            draws[b] = fit(bp, [z])[0][0]
        lo, hi = (float(x) for x in np.percentile(draws, [0.5, 99.5]))
        g = float(g_hat[0])
        rows.append({"sample": name, "predictor": z, "role": role, "n_members": int(df["id"].nunique()),
                     "n_member_terms": len(df), "t_min": int(df["t"].min()), "t_max": int(df["t"].max()),
                     "s_z": float(df[z].std(ddof=1)), "gamma_les": g, "ci99_lo": lo, "ci99_hi": hi,
                     "gamma_over_0600": g / SIGMA_ALPHA_FULL, "ci_excludes_0": bool(lo > 0 or hi < 0),
                     "abs_gamma_ge_0060": bool(abs(g) >= THRESHOLD), "verdict": verdict(g, lo, hi),
                     "sig2_alpha_without": s2a_without, "sig2_alpha_with": s2a_with,
                     "share_sig2_alpha_explained": 1 - s2a_with / s2a_without,
                     "boot_se": float(draws.std(ddof=1))})
        draws_out[name] = draws
        print(name, {k: v for k, v in rows[-1].items()}, f"{time.time() - t0:.0f}s", flush=True)

    # Total share for (a), (b), (c) together, on the rows where all three are available.
    df = panel[panel[ABC].notna().all(axis=1)].sort_values(["id", "t"]).reset_index(drop=True)
    g_all, s2a_all = fit(df, ABC)
    s2a_base = fit_base(df)
    total = {"predictors": "+".join(ABC), "n_members": int(df["id"].nunique()), "n_member_terms": len(df),
             "sig2_alpha_without": s2a_base, "sig2_alpha_with": s2a_all,
             "total_share_sig2_alpha_explained": 1 - s2a_all / s2a_base,
             **{f"gamma_les_{z}": float(v) for z, v in zip(ABC, g_all)}}
    print("total", total, flush=True)

    res = pd.DataFrame(rows)
    res.to_csv(OUT / "testD_results.csv", index=False)
    pd.DataFrame([total]).to_csv(OUT / "testD_total_share.csv", index=False)
    pd.DataFrame(draws_out).to_csv(OUT / "testD_gamma_draws.csv", index=False)
    (OUT / "testD_results.json").write_text(json.dumps(
        {"seed": SEED, "B": B, "threshold_les": THRESHOLD, "sigma_alpha_full": SIGMA_ALPHA_FULL, "ci": "99% percentile",
         "results": rows, "total_share_abc": total}, indent=2))
    pd.set_option("display.width", 250)
    print(res.to_string())
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
