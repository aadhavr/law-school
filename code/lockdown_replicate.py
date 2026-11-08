"""Lockdown data (Wehner and Hallerberg, JOP): PREREG "Lockdown data".

Step 1: replicate Appendix Table A5 column (1) (= Table 1 column 1) exactly as JOP_lockdown.do specifies:
  stset stop, failure(stayathome == 1) id(country)
  stcox dddemocracy populist2 sciencesmedicine womanpm medicine_hm2 womanhm lnGDPpccur ghsi_2019
        confirmeddeaths2 ggdebt_2019 island federal ddpresidential left right legmaj diffparty_hmpm
        independent_hm rel_christian rel_muslim rel_unaffiliated rel_hindu rel_buddhist i.e_regionpol
        if date <= 20201231
  Stata defaults: Breslow ties, model-based (OIM) standard errors, no strata, no clustering.
  stset with id(): each daily record spans (previous stop, stop]; the first record starts at 0;
  a country exits at its first record with stayathome == 1 (default exit(failure)).
  i.e_regionpol: one dummy per region, lowest level (1) is the base.

Step 2: law-trained leader indicator = `law` ("Leader degree subject - Law") from
JOP_lockdown_leaders.dta, joined on cntrycode, added to column (1) and nothing else. If step 1 misses the
tolerance, step 2 still runs and is labeled "not an exact replication" (rule set 2026-11-07, before the fit).

Writes output/lockdown/. Usage: python -I lockdown_replicate.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.duration.hazard_regression import PHReg

ROOT = Path(__file__).resolve().parents[1]
LD = ROOT / "lockdowns"
OUT = ROOT / "output" / "lockdown"

COVS = ("dddemocracy populist2 sciencesmedicine womanpm medicine_hm2 womanhm lnGDPpccur ghsi_2019 "
        "confirmeddeaths2 ggdebt_2019 island federal ddpresidential left right legmaj diffparty_hmpm "
        "independent_hm rel_christian rel_muslim rel_unaffiliated rel_hindu rel_buddhist").split()

# Published Table A5 column (1); tolerances set by the user before the fit.
PUBLISHED = {"sciencesmedicine": (1.092, 0.532, 2.241), "medicine_hm2": (0.577, 0.383, 0.869)}
TOL_HR, TOL_CI = 0.01, 0.02


def survival_sample(d):
    """Counting-process rows as Stata's stset builds them, restricted by `if date <= 20201231`."""
    d = d.sort_values(["country", "stop"]).copy()
    d["start"] = d.groupby("country")["stop"].shift(1).fillna(0.0)
    d["fail"] = (d["stayathome"] == 1).astype(int)
    first = d.groupby("country")["fail"].cumsum()
    prior = first - d["fail"]
    d = d[prior == 0]                       # drop records after the first failure
    d = d[d["date"] <= 20201231]
    return d


REL = ["rel_christian", "rel_muslim", "rel_unaffiliated", "rel_hindu", "rel_buddhist"]
# The five religion dummies sum to 1 in every country, so together they are collinear with the
# baseline hazard; Stata's stcox omits one. Main run: the last-listed one in the .do file.
REL_DROP_MAIN, REL_DROP_CHECK = "rel_buddhist", "rel_christian"


def design(d, extra=(), rel_drop=REL_DROP_MAIN):
    X = d[[c for c in COVS if c != rel_drop] + list(extra)].astype(float)
    reg = pd.get_dummies(d["e_regionpol"].astype(int), prefix="region", dtype=float)
    reg = reg.drop(columns=f"region_{int(d['e_regionpol'].min())}")
    X = pd.concat([X, reg], axis=1)
    keep = X.notna().all(axis=1)            # stcox drops records with any missing covariate
    return X[keep], d[keep]


def fit(d, extra=(), rel_drop=REL_DROP_MAIN, fit_kw=None):
    X, dd = design(d, extra, rel_drop)
    m = PHReg(dd["stop"].values, X.values, status=dd["fail"].values, entry=dd["start"].values,
              ties="breslow")
    r = m.fit(**(fit_kw or {}))  # default: statsmodels Newton-Raphson, tol 1e-8, maxiter 100
    z = stats.norm.ppf(0.975)
    tab = pd.DataFrame({"term": X.columns, "coef": r.params, "se": r.bse})
    tab["hr"] = np.exp(tab.coef)
    tab["ci_lo"] = np.exp(tab.coef - z * tab.se)
    tab["ci_hi"] = np.exp(tab.coef + z * tab.se)
    tab["p"] = 2 * stats.norm.sf(np.abs(tab.coef / tab.se))
    score = m.score(r.params)
    info = {"max_abs_score": float(np.max(np.abs(score))), "n_records": int(len(dd)), "n_countries": int(dd["country"].nunique()),
            "n_events": int(dd["fail"].sum()), "loglik": float(r.llf),
            "n_dropped_missing": int(len(d) - len(dd)),
            "countries_with_dropped": int(d.loc[~d.index.isin(dd.index), "country"].nunique()),
            "events_dropped_missing": int(d.loc[~d.index.isin(dd.index), "fail"].sum()),
            "rel_drop": rel_drop}
    return tab, info, dd


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    main_df = pd.read_stata(LD / "JOP_lockdown_main.dta", convert_categoricals=False)
    leaders = pd.read_stata(LD / "JOP_lockdown_leaders.dta", convert_categoricals=False)
    s = survival_sample(main_df)

    # ---- Step 1: replication ----
    assert (main_df.drop_duplicates("country")[REL].sum(axis=1) == 1).all()
    tab, info, _ = fit(s)
    tab.to_csv(OUT / "lockdown_A5_col1.csv", index=False)
    # Invariance check: dropping a different religion dummy gives the same likelihood and the
    # same non-religion estimates.
    tab2, info2, _ = fit(s, rel_drop=REL_DROP_CHECK)
    a = tab[~tab.term.isin(REL)].set_index("term").hr
    b = tab2[~tab2.term.isin(REL)].set_index("term").hr
    inv = pd.DataFrame({"hr_drop_" + REL_DROP_MAIN: a, "hr_drop_" + REL_DROP_CHECK: b})
    inv["abs_diff"] = (inv.iloc[:, 0] - inv.iloc[:, 1]).abs()
    inv["match_6sig"] = [f"{x:.6g}" == f"{y:.6g}" for x, y in zip(inv.iloc[:, 0], inv.iloc[:, 1])]
    inv.to_csv(OUT / "lockdown_rel_invariance.csv")
    ll_match = f"{info['loglik']:.6f}" == f"{info2['loglik']:.6f}"
    print(inv.to_string())
    print("loglik", info["loglik"], info2["loglik"], "match to 6 decimals:", ll_match)
    # Convergence check (one pass, model unchanged): tighter Newton tolerance and more iterations.
    TIGHT = {"method": "newton", "tol": 1e-12, "maxiter": 1000}
    tabt, infot, _ = fit(s, fit_kw=TIGHT)
    conv = []
    for lab, t_, i_ in [("default (newton, tol 1e-8, maxiter 100)", tab, info),
                        ("tight (newton, tol 1e-12, maxiter 1000)", tabt, infot)]:
        tt_ = t_.set_index("term")
        conv.append({"settings": lab, "loglik": i_["loglik"], "max_abs_score": i_["max_abs_score"],
                     **{f"{k}_{c}": tt_.loc[k, c] for k in PUBLISHED for c in ("hr", "ci_lo", "ci_hi")}})
    conv = pd.DataFrame(conv)
    conv.to_csv(OUT / "lockdown_convergence.csv", index=False)
    hr_shift = float((tab.set_index("term").hr - tabt.set_index("term").hr).abs().max())
    print(conv.to_string(index=False)); print("max |HR shift| over all terms:", hr_shift)
    cmp = []
    for term, (hr, lo, hi) in PUBLISHED.items():
        row = tab.set_index("term").loc[term]
        dif = {"hr": row.hr - hr, "ci_lo": row.ci_lo - lo, "ci_hi": row.ci_hi - hi}
        ok = abs(dif["hr"]) <= TOL_HR and abs(dif["ci_lo"]) <= TOL_CI and abs(dif["ci_hi"]) <= TOL_CI
        cmp.append({"term": term, "pub_hr": hr, "pub_lo": lo, "pub_hi": hi,
                    "rep_hr": row.hr, "rep_lo": row.ci_lo, "rep_hi": row.ci_hi,
                    "d_hr": dif["hr"], "d_lo": dif["ci_lo"], "d_hi": dif["ci_hi"], "pass": ok})
    cmp = pd.DataFrame(cmp)
    cmp.to_csv(OUT / "lockdown_A5_compare.csv", index=False)
    passed = bool(cmp["pass"].all())
    res = {"replication": info, "replication_pass": passed,
           "invariance": {"rel_drop_check": REL_DROP_CHECK, "loglik_check": info2["loglik"],
                          "loglik_match_6dp": ll_match, "hr_all_match_6sig": bool(inv.match_6sig.all()),
                          "hr_max_abs_diff": float(inv.abs_diff.max())}, "tol_hr": TOL_HR, "tol_ci": TOL_CI,
           "convergence": {"tight_settings": TIGHT, "loglik_default": info["loglik"], "loglik_tight": infot["loglik"],
                           "max_abs_score_default": info["max_abs_score"], "max_abs_score_tight": infot["max_abs_score"],
                           "max_abs_hr_shift": hr_shift},
           "main_rows": int(len(main_df)), "main_cols": int(main_df.shape[1]),
           "leaders_rows": int(len(leaders)), "leaders_cols": int(leaders.shape[1])}
    print(tab.to_string(index=False))
    print(info)
    print(cmp.to_string(index=False))
    # ---- Step 2: law-trained leader (PREREG). Fallback rule (set 2026-11-07 before this fit):
    # if the replication misses the tolerance, run it anyway, labeled "not an exact replication".
    res["law_label"] = "replication" if passed else "not an exact replication"
    # Join key: cntrycode (one leaders row per country; leader and minister names checked equal).
    lk = leaders[["cntrycode", "namepm", "namehm", "law"]].rename(
        columns={"namepm": "namepm_l", "namehm": "namehm_l"})
    s2 = s.merge(lk, on="cntrycode", how="left", validate="many_to_one")
    assert (s2.namepm == s2.namepm_l).all() and (s2.namehm == s2.namehm_l).all()
    s2.index = s.index
    ltab, linfo, ldd = fit(s2, extra=("law",))
    ltab.to_csv(OUT / "lockdown_law.csv", index=False)
    lrow = ltab.set_index("term").loc["law"]
    cl = s2.drop_duplicates("country")
    used = ldd.drop_duplicates("country")
    res["law"] = {**linfo, "hr": float(lrow.hr), "ci_lo": float(lrow.ci_lo), "ci_hi": float(lrow.ci_hi),
                  "p": float(lrow.p),
                  "n_law_leaders": int((used.law == 1).sum()),
                  "n_law_missing_countries": int(cl.law.isna().sum()),
                  "n_law_missing_leaders_file": int(leaders.law.isna().sum()),
                  "law_missing_countries": sorted(cl.loc[cl.law.isna(), "country"]),
                  "n_events_law_leaders": int(ldd.loc[ldd.law == 1, "fail"].sum()),
                  "sciencesmedicine_law_overlap": int(((used.law == 1) & (used.sciencesmedicine == 1)).sum())}
    print(ltab.to_string(index=False))
    print(json.dumps(res["law"], indent=2))
    (OUT / "lockdown_results.json").write_text(json.dumps(res, indent=2) + "\n")


if __name__ == "__main__":
    main()
