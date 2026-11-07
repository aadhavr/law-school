"""Step 4, linkage-corrected re-run (D15). The PREREG Step 4 outputs (step4_*) are not changed.

Why: Step 4 matched CLASS idno to the LES-panel ICPSR. Voteview gives some party switchers a
second ICPSR, and CLASS sometimes stores a person under an ICPSR that has no LES row. So three
CLASS people with LES rows under another ICPSR were dropped (Martínez 94879, Forbes 99542,
Goode 99767), and persons with two ICPSRs could enter twice (once per ICPSR α̂).

Corrected version:
- Every LES-panel ICPSR and CLASS idno is mapped to a bioguide ID through Voteview.
- The Step 3 model (PREREG X_it) is fit on the full chamber panel with one random effect per
  person (bioguide), so each person has one α̂_i. One CLASS record per person and chamber;
  their background fields must agree across idnos (checked).
- OLS of α̂_i (LES points) on law degree + the same background terms and the same ≥ 10 holders
  rule as Step 4. Bootstrap: resample persons of the full chamber panel, refit, B = 1000.
- law_deg = 1 if any CLASS row of the person has law_ind = 1 (D15; only Hall changes).
- Sensitivity: the same with Hall (H000067) left out.
- Units: LES points, and LES points / the fixed full-panel σ̂_α from Step 3 (House 0.600,
  Senate 0.427). The PREREG JD rule is applied in the fixed unit.

The original Step 4 bootstrap is replayed (its seed) to give its law effect in LES points and in
the fixed unit; the replay is checked against output/step4_coefs.csv.

Writes output/step4_linked_counts.csv, step4_linked_coefs.csv, step4_linked_compare.csv,
step4_linked_lawdeg_draws.csv, step4_linked_results.json.

Usage: python -I step4_linked.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
from load_data import load_all, ROOT
from step3_test_A import member_blocks, resample_rows, ci
import step4_skill_source as s4
from person_ids import bioguide_of_icpsr, to_person

OUT = ROOT / "output"
SEED = 20261107
B = 1000
BG = ["law_deg", "phd", "econ_phd", "phd_field_blank", "female", "black", "hispanic"]


def class_persons(bio):
    """One CLASS record per person and chamber.

    law_deg (D15): 1 if any CLASS row of the person has law_ind = 1 (max across idnos and
    chambers). Set after the Hall (H000067) conflict was seen, before any fit. The other
    background fields must agree across a person's idnos (checked)."""
    cls = s4.load_class()
    cls["bioguide"] = cls["idno"].map(bio)
    no_bio = cls[cls["bioguide"].isna()]
    cls = cls.dropna(subset=["bioguide"]).copy()
    person_law = cls.groupby("bioguide")["law_deg"].max()
    cls["law_deg_idno_rule"] = cls["law_deg"]
    cls["law_deg"] = cls["bioguide"].map(person_law)
    changed = cls[cls["law_deg"] != cls["law_deg_idno_rule"]]
    g = cls.groupby(["bioguide", "chamber"])
    differ = g[BG].nunique(dropna=False).gt(1).any(axis=1)
    if differ.any():
        raise SystemExit(f"STOP: background fields differ across idnos for {list(differ[differ].index)}")
    per = g.agg(**{k: (k, "first") for k in BG},
                idnos=("idno", lambda x: ";".join(str(i) for i in sorted(x))),
                n_idno=("idno", "nunique")).reset_index()
    return per, no_bio, changed[["bioguide", "idno", "chamber", "law_deg_idno_rule", "law_deg"]]


def replay_original(D, cls):
    """Replay Step 4 (same seed and chamber order); law_deg in LES points and both σ units."""
    rng = np.random.default_rng(s4.SEED)
    ref = pd.read_csv(OUT / "step4_coefs.csv")
    out = {}
    for body, code in s4.CHAMBERS.items():
        panel = D[body].sort_values(["id", "t"]).reset_index(drop=True)
        samp = cls[(cls["chamber"] == code) & cls["idno"].isin(panel["id"])]
        terms = [t for t in ["law_deg", "phd", "female", "black", "hispanic"]
                 if t == "law_deg" or samp[t].sum() >= s4.MIN_HOLDERS]
        bg = samp.set_index("idno")[terms]

        def one(p, orig):
            a, sig = s4.alpha_hat(p)
            drawn = pd.Series(orig, index=p["id"].to_numpy()).groupby(level=0).first().loc[a.index].to_numpy()
            keep = np.isin(drawn, bg.index)
            X = np.column_stack([np.ones(keep.sum())] + [bg.loc[drawn[keep], t].to_numpy(float) for t in terms])
            les = s4.ols(a.to_numpy()[keep], X)[1]
            return les, les / sig

        est = np.array(one(panel, panel["id"].to_numpy()))
        start, count = member_blocks(panel["id"].to_numpy())
        draws = np.empty((s4.B, 2))
        for b in range(s4.B):
            rows, new_id = resample_rows(start, count, rng)
            bp = panel.iloc[rows].copy()
            orig = bp["id"].to_numpy()
            bp["id"] = new_id
            draws[b] = one(bp, orig)
        r = ref[(ref["body"] == body) & (ref["term"] == "law_deg")].iloc[0]
        lo, hi = ci(draws[:, 1])
        assert abs(est[1] - r["estimate_sigma_alpha_units"]) < 1e-12 and abs(lo - r["ci_lo"]) < 1e-12 \
            and abs(hi - r["ci_hi"]) < 1e-12, (body, est, lo, hi)
        out[body] = (est, draws, len(samp))
    return out


def fit_linked(D, body, code, per, bio, rng, exclude=()):
    panel = to_person(D[body], bio)
    sub = per[(per["chamber"] == code) & ~per["bioguide"].isin(exclude)].copy()
    sub["matched"] = sub["bioguide"].isin(panel["bioguide"])
    samp = sub[sub["matched"]].copy()
    code_of = panel.drop_duplicates("bioguide").set_index("bioguide")["id"]
    samp["pid"] = samp["bioguide"].map(code_of).astype(int)
    a_hat, sig_person = s4.alpha_hat(panel)
    samp["alpha_hat_les"] = a_hat.loc[samp["pid"]].to_numpy()
    n_econ = int(samp["econ_phd"].sum())
    cand = ["law_deg", "phd"] + (["econ_phd"] if n_econ >= s4.MIN_ECON_PHD else []) + ["female", "black", "hispanic"]
    terms = [t for t in cand if t == "law_deg" or samp[t].sum() >= s4.MIN_HOLDERS]
    c = {"body": body, "class_persons_with_bioguide": len(sub), "matched_to_LES": len(samp),
         "unmatched": int((~sub["matched"]).sum()), "excluded": ";".join(exclude),
         "persons_with_more_than_one_class_idno": int((samp["n_idno"] > 1).sum()),
         "multi_idno_persons": ";".join(samp.loc[samp["n_idno"] > 1, "bioguide"]),
         "law_degree": int(samp["law_deg"].sum()), "doctorate_phd_ind": int(samp["phd"].sum()),
         "econ_phd": n_econ, "female": int(samp["female"].sum()), "black": int(samp["black"].sum()),
         "hispanic": int(samp["hispanic"].sum()), "sigma_alpha_person_model": sig_person,
         "terms_dropped_lt_min_holders": ";".join(t for t in cand if t not in terms)}
    Xs = np.column_stack([np.ones(len(samp))] + [samp[t].to_numpy(float) for t in terms])
    est = s4.ols(samp["alpha_hat_les"].to_numpy(), Xs)
    start, count = member_blocks(panel["id"].to_numpy())
    bg = samp.set_index("pid")[terms]
    draws = np.empty((B, len(terms) + 1))
    for b in range(B):
        rows, new_id = resample_rows(start, count, rng)
        bp = panel.iloc[rows].copy()
        o = bp["id"].to_numpy()
        bp["id"] = new_id
        a_b, _ = s4.alpha_hat(bp)
        first = np.r_[0, np.flatnonzero(np.diff(new_id)) + 1]
        drawn = o[first]
        keep = np.isin(drawn, bg.index)
        Xb = np.column_stack([np.ones(keep.sum())] + [bg.loc[drawn[keep], t].to_numpy(float) for t in terms])
        draws[b] = s4.ols(a_b.to_numpy()[keep], Xb)
    return est, draws, ["Intercept"] + terms, c


VARIANTS = {"linkage-corrected": (), "sensitivity: linkage-corrected, Hall left out": ("H000067",)}


def main():
    D = load_all()
    bio = bioguide_of_icpsr()
    kap = pd.read_csv(OUT / "step3_kappa.csv").set_index("body")
    per, no_bio, changed = class_persons(bio)
    print("rows whose law_deg differs from the max-within-idno rule:")
    print(changed.to_string())
    res = {"seed": SEED, "B": B, "class_idnos_without_bioguide": sorted(int(i) for i in no_bio["idno"].unique()),
           "law_deg_changed_by_person_rule": changed.to_dict("records"), "chambers": {}}
    counts, coefs, compare, draw_cols = [], [], [], {}
    orig = replay_original(D, s4.load_class())

    for body, code in s4.CHAMBERS.items():
        sig_fixed = float(kap.loc[body, "sigma_alpha"])
        e_o, d_o, n_o = orig[body]
        lo_ol, hi_ol = ci(d_o[:, 0])
        lo_os, hi_os = ci(d_o[:, 1])
        rows_cmp = [
            {"version": "original (PREREG Step 4)", "unit": "LES points", "estimate": e_o[0], "ci_lo": lo_ol,
             "ci_hi": hi_ol, "boot_se": d_o[:, 0].std(ddof=1), "n": n_o},
            {"version": "original (PREREG Step 4)", "unit": "full-panel sigma_alpha, re-estimated per draw (PREREG)",
             "estimate": e_o[1], "ci_lo": lo_os, "ci_hi": hi_os, "boot_se": d_o[:, 1].std(ddof=1), "n": n_o},
            {"version": "original (PREREG Step 4)", "unit": f"fixed full-panel sigma_alpha ({sig_fixed:.3f})",
             "estimate": e_o[0] / sig_fixed, "ci_lo": lo_ol / sig_fixed, "ci_hi": hi_ol / sig_fixed,
             "boot_se": d_o[:, 0].std(ddof=1) / sig_fixed, "n": n_o}]
        draw_cols[f"{body}_original_les"] = d_o[:, 0]
        draw_cols[f"{body}_original_sigma_per_draw"] = d_o[:, 1]
        res["chambers"][body] = {}
        for vname, excl in VARIANTS.items():
            rng = np.random.default_rng(SEED)  # same seed for both variants
            est, draws, names, c = fit_linked(D, body, code, per, bio, rng, excl)
            c = {"version": vname, **c, "sigma_alpha_fixed_step3": sig_fixed}
            counts.append(c)
            for j, n in enumerate(names):
                lo, hi = ci(draws[:, j])
                coefs.append({"version": vname, "body": body, "term": n, "estimate_les": float(est[j]),
                              "ci_lo_les": lo, "ci_hi_les": hi, "estimate_sigma_fixed": float(est[j]) / sig_fixed,
                              "ci_lo_sigma_fixed": lo / sig_fixed, "ci_hi_sigma_fixed": hi / sig_fixed,
                              "boot_se_les": float(draws[:, j].std(ddof=1)), "n": c["matched_to_LES"]})
            j = names.index("law_deg")
            lo_l, hi_l = ci(draws[:, j])
            rows_cmp += [
                {"version": vname, "unit": "LES points", "estimate": est[j], "ci_lo": lo_l, "ci_hi": hi_l,
                 "boot_se": draws[:, j].std(ddof=1), "n": c["matched_to_LES"]},
                {"version": vname, "unit": f"fixed full-panel sigma_alpha ({sig_fixed:.3f})",
                 "estimate": est[j] / sig_fixed, "ci_lo": lo_l / sig_fixed, "ci_hi": hi_l / sig_fixed,
                 "boot_se": draws[:, j].std(ddof=1) / sig_fixed, "n": c["matched_to_LES"]}]
            draw_cols[f"{body}_{'linked' if not excl else 'linked_no_hall'}_les"] = draws[:, j]
            res["chambers"][body][vname] = {"counts": c, "terms": names}
            print(body, vname, c, flush=True)
        for r in rows_cmp:
            r = {"body": body, "term": "law_deg", **{k: (float(v) if isinstance(v, (float, np.floating)) else v)
                                                      for k, v in r.items()}}
            r["verdict"] = s4.prereg_jd(r["estimate"], r["ci_lo"], r["ci_hi"]) if r["unit"] != "LES points" else ""
            compare.append(r)

    cmp = pd.DataFrame(compare)
    for body in s4.CHAMBERS:
        v = cmp[(cmp["body"] == body) & (cmp["unit"] != "LES points")]
        v_orig = v[v["unit"].str.contains("re-estimated")]["verdict"].iloc[0]
        res["chambers"][body]["verdict_original"] = v_orig
        for vname in VARIANTS:
            v_new = v[v["version"] == vname]["verdict"].iloc[0]
            res["chambers"][body][f"verdict {vname}"] = v_new
            res["chambers"][body][f"verdict changes ({vname})"] = v_orig != v_new
    pd.DataFrame(counts).to_csv(OUT / "step4_linked_counts.csv", index=False)
    pd.DataFrame(coefs).to_csv(OUT / "step4_linked_coefs.csv", index=False)
    cmp.to_csv(OUT / "step4_linked_compare.csv", index=False)
    pd.DataFrame(draw_cols).to_csv(OUT / "step4_linked_lawdeg_draws.csv", index=False)
    with open(OUT / "step4_linked_results.json", "w") as f:
        json.dump(res, f, indent=2)
    pd.set_option("display.width", 250)
    print(cmp.to_string())
    print(json.dumps({b: {k: v for k, v in r.items() if k.startswith("verdict")} for b, r in res["chambers"].items()},
                     indent=1))


if __name__ == "__main__":
    main()
