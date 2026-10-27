"""Step 3: Test A. Is individual legislative skill (α_i) large?

Model (PREREG.md): LES_it = X_it·β + α_i + ε_it, fit separately for House, Senate, States.
X_it = intercept, seniority, party (D ref; R; Other), majority, committee chair.
This is the PREREG.md list exactly (no chamber term, also for States).

Usage: python step3_test_A.py [output_dir]   (default: ../output)

Outputs:
  step3_validation.csv   fast REML vs statsmodels MixedLM on the full data (numerical check)
  step3_kappa.csv        κ, σ²_α, σ²_ε, Var(X_it·β̂), marginal R², member-bootstrap 95% CIs
  step3_beta.csv         fixed effects β̂ per body
  step3_oos_pairs.csv    out-of-sample (α̂_i from terms before t, residual LES at t) pairs
  step3_oos.csv          Pearson r and member-bootstrap 95% CI per body
  step3_results.json     every number above, plus the PREREG verdict per body
"""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
from load_data import load_all
import remlfit

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "output"
SEED = 20261024
B_KAPPA = 1000
B_R = 2000


def design(df):
    cols = {
        "Intercept": np.ones(len(df)),
        "seniority": df["seniority"].to_numpy(float),
        "party_R": (df["party"] == "R").to_numpy(float),
        "party_Other": (df["party"] == "Other").to_numpy(float),
        "majority": df["majority"].to_numpy(float),
        "chair": df["chair"].to_numpy(float),
    }
    names = list(cols)
    return np.column_stack([cols[k] for k in names]), names


def fit_df(df):
    X, names = design(df)
    X, names = remlfit.drop_constant_columns(X, names)
    return remlfit.fit(df["les"].to_numpy(float), X, df["id"].to_numpy()), names


def member_blocks(ids):
    """Rows must be sorted by id. Return start offset and count per member."""
    _, start, count = np.unique(ids, return_index=True, return_counts=True)
    return start, count


def resample_rows(start, count, rng):
    m = rng.integers(0, len(start), len(start))
    c = count[m]
    new_id = np.repeat(np.arange(len(m)), c)
    offs = np.arange(c.sum()) - np.repeat(np.cumsum(c) - c, c)
    rows = np.repeat(start[m], c) + offs
    return rows, new_id


def bootstrap_kappa(df, B, rng):
    df = df.sort_values(["id", "t"]).reset_index(drop=True)
    X_full, names = design(df)
    y_full = df["les"].to_numpy(float)
    start, count = member_blocks(df["id"].to_numpy())
    draws = []
    for _ in range(B):
        rows, new_id = resample_rows(start, count, rng)
        X, _ = remlfit.drop_constant_columns(X_full[rows], names)
        r = remlfit.fit(y_full[rows], X, new_id)
        draws.append((r["kappa"], r["sig2_alpha"], r["sig2_eps"], r["marginal_r2"]))
    return np.array(draws)


def oos_pairs(df, body):
    """For each t, fit on all rows with t' < t; α̂_i = BLUP; residual = LES_it − X_it·β̂."""
    rows = []
    ts = np.sort(df["t"].unique())
    for t in ts[1:]:
        train = df[df["t"] < t]
        X_tr, names = design(train)
        X_tr, kept = remlfit.drop_constant_columns(X_tr, names)
        r = remlfit.fit(train["les"].to_numpy(float), X_tr, train["id"].to_numpy())
        blup = pd.Series(r["blup"], index=r["ids"])
        nprior = pd.Series(r["n_terms"], index=r["ids"])
        test = df[(df["t"] == t) & df["id"].isin(blup.index)]
        if test.empty:
            continue
        X_te, names_te = design(test)
        X_te = X_te[:, [names_te.index(k) for k in kept]]
        resid = test["les"].to_numpy(float) - X_te @ r["beta"]
        rows.append(pd.DataFrame({
            "body": body, "t": t, "id": test["id"].to_numpy(),
            "alpha_hat_prior": blup.loc[test["id"]].to_numpy(),
            "n_prior_terms": nprior.loc[test["id"]].to_numpy(),
            "resid_t": resid,
        }))
    return pd.concat(rows, ignore_index=True)


def bootstrap_r(pairs, B, rng):
    pairs = pairs.sort_values("id").reset_index(drop=True)
    a = pairs["alpha_hat_prior"].to_numpy()
    e = pairs["resid_t"].to_numpy()
    start, count = member_blocks(pairs["id"].to_numpy())
    out = np.empty(B)
    for b in range(B):
        rows, _ = resample_rows(start, count, rng)
        out[b] = np.corrcoef(a[rows], e[rows])[0, 1]
    return out


def ci(x):
    lo, hi = np.percentile(x, [2.5, 97.5])
    return float(lo), float(hi)


def validate(D):
    import statsmodels.api as sm
    rows = []
    for body, df in D.items():
        X, names = design(df)
        X, names = remlfit.drop_constant_columns(X, names)
        y = df["les"].to_numpy(float)
        mine = remlfit.fit(y, X, df["id"].to_numpy())
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sm_r = sm.MixedLM(y, X, groups=df["id"].to_numpy()).fit(reml=True)
        sm_blup = np.array([np.asarray(sm_r.random_effects[i])[0] for i in mine["ids"]])
        rows.append({
            "body": body,
            "sig2_alpha_fast": mine["sig2_alpha"], "sig2_alpha_statsmodels": float(np.asarray(sm_r.cov_re)[0, 0]),
            "sig2_eps_fast": mine["sig2_eps"], "sig2_eps_statsmodels": float(sm_r.scale),
            "max_abs_beta_diff": float(np.max(np.abs(mine["beta"] - np.asarray(sm_r.fe_params)))),
            "max_abs_blup_diff": float(np.max(np.abs(mine["blup"] - sm_blup))),
            "statsmodels_converged": bool(sm_r.converged),
        })
    return pd.DataFrame(rows)


def verdict(k, lo, hi):
    """PREREG.md decision rule for Claim A."""
    if k < 0.10:
        return "not supported"
    if k >= 0.20 and (lo > 0 or hi < 0):
        return "supported as a measurable trait"
    return "weak"


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    D = load_all()
    results = {"seed": SEED, "B_kappa": B_KAPPA, "B_r": B_R, "bodies": {}}

    val = validate(D)
    val.to_csv(OUT / "step3_validation.csv", index=False)
    print(val.to_string())

    kappa_rows, beta_rows, oos_rows, all_pairs = [], [], [], []
    for body, df in D.items():
        r, names = fit_df(df)
        assert not r["loglam_at_bound"], body
        draws = bootstrap_kappa(df, B_KAPPA, rng)
        tot = r["var_xb"] + r["sig2_alpha"] + r["sig2_eps"]
        row = {
            "body": body, "n_rows": len(df), "n_members": int(df["id"].nunique()),
            "t_min": int(df["t"].min()), "t_max": int(df["t"].max()),
            "mean_terms_per_member": float(df.groupby("id").size().mean()),
            "var_les_sample": float(df["les"].var(ddof=1)),
            "sig2_alpha": r["sig2_alpha"], "sig2_eps": r["sig2_eps"], "var_xb": r["var_xb"],
            "kappa": r["kappa"], "kappa_lo": ci(draws[:, 0])[0], "kappa_hi": ci(draws[:, 0])[1],
            "sig2_alpha_lo": ci(draws[:, 1])[0], "sig2_alpha_hi": ci(draws[:, 1])[1],
            "sig2_eps_lo": ci(draws[:, 2])[0], "sig2_eps_hi": ci(draws[:, 2])[1],
            "marginal_r2": r["marginal_r2"], "marginal_r2_lo": ci(draws[:, 3])[0], "marginal_r2_hi": ci(draws[:, 3])[1],
            "share_x": r["var_xb"] / tot, "share_alpha": r["sig2_alpha"] / tot, "share_eps": r["sig2_eps"] / tot,
            "sigma_alpha": float(np.sqrt(r["sig2_alpha"])),
        }
        kappa_rows.append(row)
        beta_rows += [{"body": body, "term": n, "beta": float(b)} for n, b in zip(names, r["beta"])]

        pairs = oos_pairs(df, body)
        all_pairs.append(pairs)
        rb = bootstrap_r(pairs, B_R, rng)
        r_hat = float(np.corrcoef(pairs["alpha_hat_prior"], pairs["resid_t"])[0, 1])
        oos_rows.append({"body": body, "n_pairs": len(pairs), "n_members": int(pairs["id"].nunique()),
                         "r": r_hat, "r_lo": ci(rb)[0], "r_hi": ci(rb)[1]})
        print(body, "done", f"{time.time() - t0:.0f}s", flush=True)

    kap = pd.DataFrame(kappa_rows)
    oos = pd.DataFrame(oos_rows)
    kap.to_csv(OUT / "step3_kappa.csv", index=False)
    pd.DataFrame(beta_rows).to_csv(OUT / "step3_beta.csv", index=False)
    oos.to_csv(OUT / "step3_oos.csv", index=False)
    pd.concat(all_pairs).to_csv(OUT / "step3_oos_pairs.csv", index=False)

    for k_row, o_row in zip(kappa_rows, oos_rows):
        results["bodies"][k_row["body"]] = {**k_row, **{f"oos_{k}": v for k, v in o_row.items() if k != "body"},
                                            "prereg_verdict": verdict(k_row["kappa"], o_row["r_lo"], o_row["r_hi"])}
    results["validation"] = val.to_dict(orient="records")
    with open(OUT / "step3_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
