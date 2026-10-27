"""Step 4: Skill source. Does a law degree predict α̂_i? (Congresses 106–110, CLASS 1.9)

PREREG.md: regress α̂_i on background variables; bootstrap over members to account for
α̂_i being estimated; express effects in units of σ_α.
- JD favors law school: estimate ≥ 0.20σ_α AND 95% CI lower bound > 0.
- No evidence: CI includes 0, or estimate < 0.10σ_α. Otherwise: inconclusive.
- Economics PhD effect: estimated only if at least 30 members hold one.
House is primary; Senate is secondary.

α̂_i: BLUP from the Step 3 model (PREREG X_it) fit on the full LES 1.0 panel (Congresses
93–118) for each chamber. Sample: members in CLASS (Congresses 106–110), merged by ICPSR.
Regression: α̂_i/σ̂_α on law degree (law_ind), doctorate (phd_ind), [econ PhD], female, Black,
Hispanic (all from CLASS); a term other than law degree enters only if ≥ 10 members hold it. Bootstrap: resample members of the full chamber panel, refit the
mixed model, recompute α̂_i and σ̂_α, rerun the regression on resampled CLASS members.

Usage: python -I step4_skill_source.py [output_dir]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
from load_data import load_all, ROOT
import remlfit
from step3_test_A import design, member_blocks, resample_rows, ci

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "output"
CLASS = ROOT / "data/raw/09_carnes/CLASS.1.9.dta"
SEED = 20261026
B = 1000
MIN_ECON_PHD = 30
MIN_HOLDERS = 10
CHAMBERS = {"House": "H", "Senate": "S"}


def load_class():
    c = pd.read_stata(CLASS, convert_categoricals=False,
                      columns=["cong", "idno", "chamber", "law_ind", "phd_ind", "college_doctorate_major",
                               "female_ind", "black_ind", "hispanic_ind"])
    major = c["college_doctorate_major"].fillna("").astype(str).str.strip()
    c["econ_phd"] = ((c["phd_ind"] == 1) & major.str.contains("econom", case=False)).astype(float)
    c["phd_field_blank"] = ((c["phd_ind"] == 1) & major.eq("")).astype(float)
    # Background fields are constant within member-chamber (checked); keep one row each.
    m = c.groupby(["idno", "chamber"], as_index=False).agg(
        law_deg=("law_ind", "max"), phd=("phd_ind", "max"), econ_phd=("econ_phd", "max"),
        phd_field_blank=("phd_field_blank", "max"), female=("female_ind", "max"),
        black=("black_ind", "max"), hispanic=("hispanic_ind", "max"), n_class_congs=("cong", "nunique"))
    m["idno"] = m["idno"].astype(int)
    return m


def alpha_hat(panel):
    """Fit the PREREG model on a panel; return Series of BLUPs by id and σ̂_α."""
    X, names = design(panel)
    X, _ = remlfit.drop_constant_columns(X, names)
    r = remlfit.fit(panel["les"].to_numpy(float), X, panel["id"].to_numpy())
    return pd.Series(r["blup"], index=r["ids"]), float(np.sqrt(r["sig2_alpha"]))


def ols(y, X):
    return np.linalg.lstsq(X, y, rcond=None)[0]


def prereg_jd(est, lo, hi):
    if est >= 0.20 and lo > 0:
        return "JD favors law school as a skill source"
    if lo <= 0 <= hi or est < 0.10:
        return "no evidence for a JD skill premium"
    return "inconclusive"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    D = load_all()
    cls = load_class()
    per_member = cls.groupby("idno")[["law_deg", "phd", "econ_phd", "phd_field_blank"]].max()
    results = {"seed": SEED, "B": B, "chambers": {},
               "class_unique_members_both_chambers": {"members": len(per_member),
                                                      **{k: int(v) for k, v in per_member.sum().items()}}}
    print(results["class_unique_members_both_chambers"])
    count_rows, coef_rows = [], []

    for body, code in CHAMBERS.items():
        panel = D[body].sort_values(["id", "t"]).reset_index(drop=True)
        sub = cls[cls["chamber"] == code].copy()
        a_hat, sig_a = alpha_hat(panel)
        sub["matched"] = sub["idno"].isin(a_hat.index)
        samp = sub[sub["matched"]].copy()
        samp["alpha_hat"] = a_hat.loc[samp["idno"]].to_numpy()
        samp["y"] = samp["alpha_hat"] / sig_a

        n_econ = int(samp["econ_phd"].sum())
        counts = {"body": body, "class_members": len(sub), "matched_to_LES": len(samp),
                  "unmatched": int((~sub["matched"]).sum()),
                  "law_degree": int(samp["law_deg"].sum()), "doctorate_phd_ind": int(samp["phd"].sum()),
                  "econ_phd": n_econ, "doctorate_field_blank": int(samp["phd_field_blank"].sum()),
                  "female": int(samp["female"].sum()), "black": int(samp["black"].sum()),
                  "hispanic": int(samp["hispanic"].sum()), "sigma_alpha_full_panel": sig_a}
        cand = ["law_deg", "phd"] + (["econ_phd"] if n_econ >= MIN_ECON_PHD else []) + ["female", "black", "hispanic"]
        # Rule set before any coefficient was seen: a binary background term enters only if
        # at least MIN_HOLDERS members in this chamber's sample hold it (law_deg always enters).
        terms = [t for t in cand if t == "law_deg" or samp[t].sum() >= MIN_HOLDERS]
        counts["terms_dropped_lt_min_holders"] = ";".join(t for t in cand if t not in terms)
        counts["unmatched_icpsr"] = ";".join(str(i) for i in sub.loc[~sub["matched"], "idno"])

        Xs = np.column_stack([np.ones(len(samp))] + [samp[t].to_numpy(float) for t in terms])
        est = ols(samp["y"].to_numpy(), Xs)

        # Bootstrap over members of the full panel: refit mixed model, recompute α̂_i and σ̂_α.
        start, count = member_blocks(panel["id"].to_numpy())
        ids_sorted = panel["id"].to_numpy()[start]
        bg = samp.set_index("idno")[terms]
        draws = np.empty((B, len(terms) + 1))
        for b in range(B):
            rows, new_id = resample_rows(start, count, rng)
            bp = panel.iloc[rows].copy()
            orig = bp["id"].to_numpy()
            bp["id"] = new_id
            a_b, sig_b = alpha_hat(bp)
            first = np.r_[0, np.flatnonzero(np.diff(new_id)) + 1]
            drawn_orig = orig[first]
            keep = np.isin(drawn_orig, bg.index)
            yb = a_b.to_numpy()[keep] / sig_b
            Xb = np.column_stack([np.ones(keep.sum())] + [bg.loc[drawn_orig[keep], t].to_numpy(float) for t in terms])
            draws[b] = ols(yb, Xb)

        count_rows.append(counts)
        names = ["Intercept"] + terms
        for j, n in enumerate(names):
            lo, hi = ci(draws[:, j])
            coef_rows.append({"body": body, "term": n, "estimate_sigma_alpha_units": float(est[j]),
                              "ci_lo": lo, "ci_hi": hi, "n": len(samp)})
        jd = next(r for r in coef_rows if r["body"] == body and r["term"] == "law_deg")
        results["chambers"][body] = {
            "counts": counts, "terms": names, "econ_phd_estimated": n_econ >= MIN_ECON_PHD,
            "coefficients": [r for r in coef_rows if r["body"] == body],
            "prereg_jd_verdict": prereg_jd(jd["estimate_sigma_alpha_units"], jd["ci_lo"], jd["ci_hi"]),
        }
        print(body, counts, flush=True)

    pd.DataFrame(count_rows).to_csv(OUT / "step4_counts.csv", index=False)
    pd.DataFrame(coef_rows).to_csv(OUT / "step4_coefs.csv", index=False)
    with open(OUT / "step4_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("done")


if __name__ == "__main__":
    main()
