"""EXPLORATORY (not in PREREG.md). Law background inside the mixed model, power, Wilson CI.

Requested 2026-10-26. The PREREG results (step3_*, step4_*) are primary and are not changed.

1. LES_it = X_it·β + γ·LAW_i + α_i + ε_it, X_it = PREREG list. Sample: CLASS 1.9 members
   (Congresses 106–110) matched to LES 1.0 by ICPSR, with all their LES 1.0 terms (Congresses
   93–118) in that chamber. House and Senate are fit separately, as in PREREG, because LES is
   scaled within chamber. LAW_i is person-level (identical across a member's CLASS rows; checked).
2. Same with LAWYER_i (any CLASS occupation code 1–4: lawyer, private/corporate/other/unspecified),
   then both in one model.
   Units: γ / σ̂_α, where σ̂_α is from the PREREG model (no background term) on the same sample.
   95% CI: percentile, bootstrap over members (all models refit in every draw).
4. Bootstrap standard error (SD of the bootstrap draws) of each law effect, here and for the
   PREREG Step 4 law_deg effects (their bootstrap is replayed with the Step 4 seed; the replay
   is checked against output/step4_coefs.csv). Smallest effect with 80% power, two-sided α = 0.05:
   MDE = (z_0.975 + z_0.80) × SE.
D9 (ANALYSIS_LOG.md). Every law effect is reported three ways (expl_law_units.csv):
   LES points; units of the full-panel σ̂_α (the Step 3 estimate; for Step 4 this is the PREREG
   result, σ̂_α re-estimated per draw; for E1/E2 it is fixed, because only CLASS members are
   resampled); units of the sample σ̂_α (PREREG model on the analysis sample's own terms).
   The PREREG threshold (0.20σ_α) and the power at it use the full-panel σ̂_α.
5. Wilson 95% CI for the share of members with an economics PhD.

Usage: python -I explore_law_mixed.py [output_dir]   (default: ../output/exploratory)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
from load_data import load_all, ROOT
import remlfit
from step3_test_A import design, member_blocks, resample_rows, ci
import step4_skill_source as s4

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "output" / "exploratory"
SEED = 20261027
B = 1000
Z = norm.ppf(0.975) + norm.ppf(0.80)
OCC = [f"occupation{k}_category" for k in range(1, 11)]
MODELS = {"degree": ["law_deg"], "occupation": ["lawyer_occ"], "both": ["law_deg", "lawyer_occ"]}


def load_people():
    c = pd.read_stata(s4.CLASS, convert_categoricals=False,
                      columns=["idno", "law_ind", "phd_ind", "college_doctorate_major"] + OCC)
    c["lawyer_occ"] = c[OCC].isin([1, 2, 3, 4]).any(axis=1).astype(float)
    major = c["college_doctorate_major"].fillna("").astype(str)
    c["econ_phd"] = ((c["phd_ind"] == 1) & major.str.contains("econom", case=False)).astype(float)
    g = c.groupby("idno")
    assert (g["law_ind"].nunique() == 1).all() and (g["lawyer_occ"].nunique() == 1).all()
    p = g.agg(law_deg=("law_ind", "max"), lawyer_occ=("lawyer_occ", "max"), econ_phd=("econ_phd", "max"))
    p.index = p.index.astype(int)
    return p


def fit_all(panel, people):
    """Return [σ̂_α(PREREG), then for each model: γ's, γ/σ̂_α's] as one flat vector."""
    y = panel["les"].to_numpy(float)
    X0, names = design(panel)
    X0, names = remlfit.drop_constant_columns(X0, names)
    ids = panel["id"].to_numpy()
    sig_a = np.sqrt(remlfit.fit(y, X0, ids)["sig2_alpha"])
    out = [sig_a]
    for terms in MODELS.values():
        Z_ = people.loc[panel["orig"].to_numpy(), terms].to_numpy(float)
        r = remlfit.fit(y, np.column_stack([X0, Z_]), ids)
        g = r["beta"][-len(terms):]
        out += list(g) + list(g / sig_a)
    return np.array(out)


def labels():
    lab = ["sigma_alpha_prereg"]
    for m, terms in MODELS.items():
        lab += [f"{m}:{t}:gamma_les" for t in terms] + [f"{m}:{t}:gamma_sigma_alpha" for t in terms]
    return lab


def replay_step4():
    """Replay the Step 4 bootstrap (same seed, same chamber order) for law_deg.

    Returns, per chamber: point estimates and draws of the law_deg coefficient in LES points
    (OLS on unscaled α̂_i), in PREREG units (α̂_i / σ̂_α of the full panel, re-estimated per draw),
    and in sample units (LES points / σ̂_α of the PREREG model fit on the CLASS members' own terms).
    """
    rng = np.random.default_rng(s4.SEED)
    D = load_all()
    cls = s4.load_class()
    out = {}
    for body, code in s4.CHAMBERS.items():
        panel = D[body].sort_values(["id", "t"]).reset_index(drop=True)
        samp = cls[(cls["chamber"] == code) & cls["idno"].isin(panel["id"])]
        terms = [t for t in ["law_deg", "phd", "female", "black", "hispanic"]
                 if t == "law_deg" or samp[t].sum() >= s4.MIN_HOLDERS]  # = step4_results.json terms
        bg = samp.set_index("idno")[terms]

        def one(p):
            a, sig = s4.alpha_hat(p)
            drawn_ids = p.groupby("id")["orig"].first().loc[a.index].to_numpy()
            keep = np.isin(drawn_ids, bg.index)
            X = np.column_stack([np.ones(keep.sum())] + [bg.loc[drawn_ids[keep], t].to_numpy(float) for t in terms])
            les = s4.ols(a.to_numpy()[keep], X)[1]
            sub = p[p["orig"].isin(bg.index)]
            sig_s = sigma_alpha_prereg(sub)
            return les, les / sig, les / sig_s, sig_s

        p0 = panel.assign(orig=panel["id"])
        est = one(p0)
        start, count = member_blocks(panel["id"].to_numpy())
        draws = np.empty((s4.B, 4))
        for b in range(s4.B):
            rows, new_id = resample_rows(start, count, rng)
            bp = panel.iloc[rows].copy()
            bp["orig"] = bp["id"].to_numpy()
            bp["id"] = new_id
            draws[b] = one(bp)
        out[body] = (np.array(est), draws)
    return out


def sigma_alpha_prereg(panel):
    X, names = design(panel)
    X, _ = remlfit.drop_constant_columns(X, names)
    return float(np.sqrt(remlfit.fit(panel["les"].to_numpy(float), X, panel["id"].to_numpy())["sig2_alpha"]))


def wilson(k, n, z=norm.ppf(0.975)):
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return float(c - h), float(c + h)


def power_at(effect, se):
    return float(norm.cdf(effect / se - norm.ppf(0.975)) + norm.cdf(-effect / se - norm.ppf(0.975)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    D = load_all()
    people = load_people()
    res = {"label": "EXPLORATORY", "seed": SEED, "B": B, "z_sum_80pct_power": float(Z),
           "class_people": len(people)}
    matched = people.index[people.index.isin(D["House"]["id"]) | people.index.isin(D["Senate"]["id"])]
    res["matched_people"] = len(matched)
    res["unmatched_icpsr"] = [int(i) for i in people.index.difference(matched)]
    rows = []
    all_est, all_draws = {}, {}

    for body in ["House", "Senate"]:
        panel = D[body][D[body]["id"].isin(people.index)].sort_values(["id", "t"]).reset_index(drop=True)
        panel["orig"] = panel["id"]
        pp = people.loc[panel["id"].unique()]
        info = {"n_rows": len(panel), "n_members": len(pp), "law_deg": int(pp["law_deg"].sum()),
                "lawyer_occ": int(pp["lawyer_occ"].sum()),
                "both": int(((pp["law_deg"] == 1) & (pp["lawyer_occ"] == 1)).sum()),
                "degree_not_occ": int(((pp["law_deg"] == 1) & (pp["lawyer_occ"] == 0)).sum()),
                "occ_not_degree": int(((pp["law_deg"] == 0) & (pp["lawyer_occ"] == 1)).sum())}
        est = fit_all(panel, people)
        start, count = member_blocks(panel["id"].to_numpy())
        draws = np.empty((B, len(est)))
        for b in range(B):
            r_idx, new_id = resample_rows(start, count, rng)
            bp = panel.iloc[r_idx].copy()
            bp["id"] = new_id
            draws[b] = fit_all(bp, people)
        for j, lab in enumerate(labels()):
            lo, hi = ci(draws[:, j])
            rows.append({"body": body, "quantity": lab, "estimate": float(est[j]), "ci_lo": lo, "ci_hi": hi,
                         "boot_se": float(draws[:, j].std(ddof=1))})
        res[body] = info
        all_est[body], all_draws[body] = est, draws
        print(body, info, flush=True)

    # ---- D9: every law effect in LES points, full-panel σ_α units, sample σ̂_α units ----
    kap = pd.read_csv(ROOT / "output" / "step3_kappa.csv").set_index("body")
    ref = pd.read_csv(ROOT / "output" / "step4_coefs.csv")
    unit_rows = []

    def add(body, analysis, term, unit, est, d, thr):
        lo, hi = ci(d)
        unit_rows.append({"body": body, "analysis": analysis, "term": term, "unit": unit, "estimate": float(est),
                          "ci_lo": lo, "ci_hi": hi, "boot_se": float(np.std(d, ddof=1)),
                          "mde_80pct_power": float(Z * np.std(d, ddof=1)),
                          "power_at_prereg_threshold": power_at(thr, float(np.std(d, ddof=1))) if thr else np.nan,
                          "threshold_in_this_unit": thr if thr else np.nan})

    for body, (est, d4) in replay_step4().items():
        r = ref[(ref["body"] == body) & (ref["term"] == "law_deg")].iloc[0]
        lo, hi = ci(d4[:, 1])
        assert abs(est[1] - r["estimate_sigma_alpha_units"]) < 1e-12 and abs(lo - r["ci_lo"]) < 1e-12 \
            and abs(hi - r["ci_hi"]) < 1e-12, (body, est, lo, hi, r)
        a = "PREREG step4 (OLS on BLUP)"
        add(body, a, "law_deg", "LES points", est[0], d4[:, 0], None)
        add(body, a, "law_deg", "full-panel sigma_alpha (PREREG; re-estimated per draw)", est[1], d4[:, 1], 0.20)
        add(body, a, "law_deg", f"sample sigma_alpha ({est[3]:.6f})", est[2], d4[:, 2], None)
    res["step4_replay_ci_matches_output"] = True

    for body in ["House", "Senate"]:
        sig_full = float(kap.loc[body, "sigma_alpha"])
        dr = all_draws[body]
        lab = labels()
        for m, terms in MODELS.items():
            for t in terms:
                j_les = lab.index(f"{m}:{t}:gamma_les")
                j_s = lab.index(f"{m}:{t}:gamma_sigma_alpha")
                a = f"E1/E2 mixed model: {m}"
                add(body, a, t, "LES points", all_est[body][j_les], dr[:, j_les], None)
                add(body, a, t, f"full-panel sigma_alpha (fixed at {sig_full:.6f})", all_est[body][j_les] / sig_full,
                    dr[:, j_les] / sig_full, 0.20)
                add(body, a, t, f"sample sigma_alpha ({all_est[body][0]:.6f})", all_est[body][j_s], dr[:, j_s], None)
    units = pd.DataFrame(unit_rows)
    full = units[units["unit"].str.startswith("full-panel")]
    res["prereg_rule_on_full_panel_units"] = [
        {"body": r["body"], "analysis": r["analysis"], "term": r["term"],
         "verdict": s4.prereg_jd(r["estimate"], r["ci_lo"], r["ci_hi"])} for _, r in full.iterrows()]
    units.to_csv(OUT / "expl_law_units.csv", index=False)
    print(units.to_string())

    k = int(people.loc[matched, "econ_phd"].sum())
    k_all = int(people["econ_phd"].sum())
    res["econ_phd_wilson"] = [
        {"k": k_all, "n": len(people), "denominator": "all CLASS people",
         "share": k_all / len(people), "ci": wilson(k_all, len(people))},
        {"k": k, "n": len(matched), "denominator": "CLASS people matched to LES 1.0",
         "share": k / len(matched), "ci": wilson(k, len(matched))}]

    pd.DataFrame(rows).to_csv(OUT / "expl_law_mixed.csv", index=False)
    with open(OUT / "expl_law_results.json", "w") as f:
        json.dump(res, f, indent=2)
    print(pd.DataFrame(rows).to_string())
    print(json.dumps(res["econ_phd_wilson"], indent=1))


if __name__ == "__main__":
    main()
