"""EXPLORATORY (not in PREREG.md). House Test A on an inverse-normal rank transform of LES.

Requested 2026-10-26. The PREREG result (LES 1.0 in levels, step3_*) is primary and unchanged.
Within each Congress, LES is replaced by Φ⁻¹((rank − 3/8)/(n + 1/4)) (Blom; ties get the mean
rank). Then the Step 3 code is run unchanged: same X_it, κ with a member-bootstrap 95% CI
(B = 1000), out-of-sample Pearson r with a member-bootstrap 95% CI (B = 2000).

Usage: python -I explore_rank_house.py [output_dir]   (default: ../output/exploratory)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
from load_data import load_all, ROOT
import step3_test_A as s3

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "output" / "exploratory"
SEED = 20261028


def int_within(df):
    df = df.copy()
    df["les_raw"] = df["les"]
    df["les"] = df.groupby("t")["les_raw"].transform(
        lambda s: norm.ppf((rankdata(s) - 0.375) / (len(s) + 0.25)))
    return df


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    df = int_within(load_all()["House"])
    r, names = s3.fit_df(df)
    assert not r["loglam_at_bound"]
    draws = s3.bootstrap_kappa(df, s3.B_KAPPA, rng)
    pairs = s3.oos_pairs(df, "House")
    rb = s3.bootstrap_r(pairs, s3.B_R, rng)
    tot = r["var_xb"] + r["sig2_alpha"] + r["sig2_eps"]
    res = {"label": "EXPLORATORY", "seed": SEED, "body": "House", "outcome": "inverse-normal rank of LES 1.0 within Congress",
           "n_rows": len(df), "n_members": int(df["id"].nunique()),
           "sig2_alpha": r["sig2_alpha"], "sig2_eps": r["sig2_eps"],
           "kappa": r["kappa"], "kappa_ci": s3.ci(draws[:, 0]),
           "marginal_r2": r["marginal_r2"], "marginal_r2_ci": s3.ci(draws[:, 3]), "share_x": r["var_xb"] / tot,
           "oos_r": float(np.corrcoef(pairs["alpha_hat_prior"], pairs["resid_t"])[0, 1]), "oos_r_ci": s3.ci(rb),
           "oos_n_pairs": len(pairs), "oos_n_members": int(pairs["id"].nunique()),
           "prereg_rule_applied_for_comparison": s3.verdict(r["kappa"], *s3.ci(rb))}
    with open(OUT / "expl_rank_house.json", "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
