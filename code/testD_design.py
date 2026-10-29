"""Test D, step 2: build predictors (a)–(d) and the design-based power report.

PREREG.md Amendments 1, 1a and 1b. No model using the LES outcome is fit and no γ is
estimated: the LES column is dropped right after the House panel is loaded. Only the rows
of the Step 3 House panel and their X_it are used.

Predictors (member-term (i, t); lagged ones use Congress t−1):
  (a) |nominate_dim1_i − median nominate_dim1 of House members in t−1|  (Voteview)
  (b) PageRank (damping 0.85) in the t−1 cosponsorship network: one edge per non-withdrawn
      cosponsorship, cosponsor → sponsor, weight = count; hr and hjres (BILLSTATUS)
  (c) share of the member's bills (hr, hjres) in t−1 with ≥ 1 non-withdrawn cosponsor whose
      Voteview party_code in t−1 differs from the sponsor's; missing if no bills
  (d) years in the state legislature before the first House term (CLASS 1.9 spells), for
      House members of Congresses 106–110, all their House panel terms
(a)–(c) need House service in t−1. (b), (c) cover t = 109–118.

Power (Amendments 1a, 1b): σ̂_γ̂ = sqrt of the γ entry of σ̂²_ε (X̃′X̃)⁻¹ after quasi-demeaning,
which equals the GLS (X′V⁻¹X)⁻¹ with V = σ̂²_ε I + σ̂²_α J by member; Step 3 House σ̂²_α, σ̂²_ε.

Writes to output/testD/: testD_predictors.csv, testD_d_members.csv, testD_power.csv,
testD_power.json, testD_design_log.txt.

Usage: python -I testD_design.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
from load_data import load_house, clean, ROOT
from step3_test_A import design
import remlfit

OUT = ROOT / "output/testD"
VOTEVIEW = ROOT / "data/raw/02_voteview/HSall_members.csv"
CLASS = ROOT / "data/raw/09_carnes/CLASS.1.9.dta"
DERIVED = ROOT / "data/derived"
BILL_CONGRESSES = range(108, 118)
DAMPING = 0.85
GAMMAS = [0.060, 0.120]
THRESHOLD = 0.060
Z995 = norm.ppf(0.995)
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


def pagerank(nodes, src, dst, w, d=DAMPING, tol=1e-13):
    """Weighted directed PageRank; dangling mass spread uniformly (networkx convention)."""
    idx = {n: k for k, n in enumerate(nodes)}
    N = len(nodes)
    s = np.array([idx[x] for x in src])
    t = np.array([idx[x] for x in dst])
    w = np.asarray(w, float)
    out = np.bincount(s, weights=w, minlength=N)
    dangling = out == 0
    p = np.full(N, 1.0 / N)
    for _ in range(10000):
        flow = np.bincount(t, weights=p[s] * w / out[s], minlength=N)
        new = d * (flow + p[dangling].sum() / N) + (1 - d) / N
        if np.abs(new - p).sum() < tol:
            p = new
            break
        p = new
    else:
        raise RuntimeError("PageRank did not converge")
    # Check the fixed point.
    flow = np.bincount(t, weights=p[s] * w / out[s], minlength=N)
    assert np.allclose(p, d * (flow + p[dangling].sum() / N) + (1 - d) / N, atol=1e-12)
    assert abs(p.sum() - 1) < 1e-10
    return pd.Series(p, index=nodes)


def voteview_house():
    vv = pd.read_csv(VOTEVIEW, usecols=["congress", "chamber", "icpsr", "bioguide_id", "party_code",
                                        "nominate_dim1", "nominate_number_of_votes"])
    return vv[vv["chamber"] == "House"].copy()


def network_predictors(vv, panel_ids_by_t):
    """(b) PageRank and (c) cross-party share, keyed by (bioguide, congress)."""
    sp = pd.read_csv(DERIVED / "billstatus_sponsors.csv")
    co = pd.read_csv(DERIVED / "billstatus_cosponsors.csv")
    co = co[co["withdrawn"] == 0]
    out, stats = [], []
    for c in BILL_CONGRESSES:
        h = vv[vv["congress"] == c].copy()
        # One party per person and Congress. Party switchers have two rows: use the row whose
        # ICPSR is in the LES panel in c, else the row with more votes.
        h["in_panel"] = h["icpsr"].isin(panel_ids_by_t.get(c, set()))
        h = h.sort_values(["in_panel", "nominate_number_of_votes"], ascending=False)
        party = h.drop_duplicates("bioguide_id").set_index("bioguide_id")["party_code"]
        nodes = list(party.index)
        s_c = sp[sp["congress"] == c]
        c_c = co[co["congress"] == c].merge(s_c, on=["congress", "type", "number"])
        m = c_c["cosponsor"].isin(party.index) & c_c["sponsor"].isin(party.index) & (c_c["cosponsor"] != c_c["sponsor"])
        e = c_c[m].groupby(["cosponsor", "sponsor"]).size().reset_index(name="w")
        pr = pagerank(nodes, e["cosponsor"], e["sponsor"], e["w"])
        # (c): a cosponsor outside the Voteview House roster of c has no party_code and does not count.
        c_c = c_c.assign(sp_party=c_c["sponsor"].map(party), co_party=c_c["cosponsor"].map(party))
        c_c["cross"] = c_c["co_party"].notna() & c_c["sp_party"].notna() & (c_c["co_party"] != c_c["sp_party"])
        bill_cross = c_c.groupby(["type", "number"])["cross"].any()
        b = s_c[s_c["sponsor"].isin(party.index)].set_index(["type", "number"])
        b = b.assign(cross=bill_cross.reindex(b.index, fill_value=False).to_numpy())
        share = b.groupby("sponsor")["cross"].agg(["mean", "size"])
        df = pd.DataFrame({"bioguide": nodes, "congress": c, "pagerank": pr.reindex(nodes).to_numpy()})
        df["cross_share"] = df["bioguide"].map(share["mean"])
        df["n_bills_sponsored"] = df["bioguide"].map(share["size"]).fillna(0).astype(int)
        out.append(df)
        stats.append({"congress": c, "nodes": len(nodes), "edges": len(e), "edge_weight": int(e["w"].sum()),
                      "cosponsorships_dropped_unmatched": int((~m).sum()),
                      "cosponsorships_cosponsor_no_party": int(c_c["co_party"].isna().sum()),
                      "members_no_bills": int((df["n_bills_sponsored"] == 0).sum())})
    for s in stats:
        log("network", s)
    return pd.concat(out, ignore_index=True), pd.DataFrame(stats)


def class_years(vv):
    c = pd.read_stata(CLASS, convert_categoricals=False,
                      columns=["cong", "idno", "chamber", "pol_stateleg1_s", "pol_stateleg1_e",
                               "pol_stateleg2_s", "pol_stateleg2_e"])
    c = c[c["chamber"] == "H"].copy()
    c["idno"] = c["idno"].astype(int)
    spells = ["pol_stateleg1_s", "pol_stateleg1_e", "pol_stateleg2_s", "pol_stateleg2_e"]
    # Spells are constant within member (checked here).
    assert (c.groupby("idno")[spells].nunique(dropna=False) <= 1).all().all()
    m = c.groupby("idno", as_index=False)[spells].first()
    first = vv.groupby("icpsr")["congress"].min()
    m["first_house_congress"] = m["idno"].map(first)
    m["Y"] = 1789 + 2 * (m["first_house_congress"] - 1)
    yrs = np.zeros(len(m))
    for k in (1, 2):
        s, e = m[f"pol_stateleg{k}_s"], m[f"pol_stateleg{k}_e"]
        v = (np.minimum(e, m["Y"]) - s).clip(lower=0)
        yrs += v.fillna(0).to_numpy()  # missing spell = 0 years
    m["d_years"] = np.where(m["Y"].notna(), yrs, np.nan)  # no first House Congress: missing, not 0
    m["any_spell"] = m["pol_stateleg1_s"].notna() | m["pol_stateleg2_s"].notna()
    m["spell_cut_by_Y"] = ((m["pol_stateleg1_e"] > m["Y"]) | (m["pol_stateleg2_e"] > m["Y"]))
    return m


def gls_se(df, zcol, s2a, s2e):
    X, names = design(df)
    z = df[zcol].to_numpy(float)
    s_z = z.std(ddof=1)
    X = np.column_stack([X, z / s_z])
    X, names = remlfit.drop_constant_columns(X, names + [zcol])
    assert names[-1] == zcol
    g, n = remlfit._group_index(df["id"].to_numpy())
    lam = s2a / s2e
    theta = 1.0 - 1.0 / np.sqrt(1.0 + n * lam)
    Xbar = np.stack([np.bincount(g, weights=X[:, j]) / n for j in range(X.shape[1])], axis=1)
    Xs = X - theta[g][:, None] * Xbar[g]
    cov = s2e * np.linalg.inv(Xs.T @ Xs)
    return float(np.sqrt(cov[-1, -1])), float(s_z), X, g


def gls_se_direct(X, g, s2a, s2e):
    """Check: sum over members of X_i′ V_i⁻¹ X_i, with V_i inverted explicitly."""
    A = np.zeros((X.shape[1], X.shape[1]))
    for k in np.unique(g):
        Xi = X[g == k]
        ni = len(Xi)
        Vi = s2e * np.eye(ni) + s2a * np.ones((ni, ni))
        A += Xi.T @ np.linalg.solve(Vi, Xi)
    return float(np.sqrt(np.linalg.inv(A)[-1, -1]))


def power(gamma, se):
    return float(norm.cdf(gamma / se - Z995) + norm.cdf(-gamma / se - Z995))


def p_supported(gamma, se):
    a = max(THRESHOLD, Z995 * se)
    return float(1 - norm.cdf((a - gamma) / se) + norm.cdf((-a - gamma) / se)), float(a)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    panel = clean(load_house()).drop(columns=["les"])  # the outcome is never used here
    kap = pd.read_csv(ROOT / "output/step3_kappa.csv").set_index("body").loc["House"]
    s2a, s2e = float(kap["sig2_alpha"]), float(kap["sig2_eps"])
    log(f"Step 3 House: sig2_alpha={s2a!r} sig2_eps={s2e!r}")
    log(f"House panel rows={len(panel)} members={panel['id'].nunique()} t={panel['t'].min()}-{panel['t'].max()}")

    vv = voteview_house()
    assert not vv.duplicated(["icpsr", "congress"]).any()
    bio_of = vv.drop_duplicates("icpsr").set_index("icpsr")["bioguide_id"]
    assert (vv.groupby("icpsr")["bioguide_id"].nunique() <= 1).all()
    panel["bioguide"] = panel["id"].map(bio_of)
    log("panel rows without a Voteview bioguide ID:", int(panel["bioguide"].isna().sum()))

    # Lag by person (bioguide), because party switchers get a new ICPSR in the LES panel.
    prev = panel[["bioguide", "t", "id"]].dropna(subset=["bioguide"]).rename(columns={"id": "id_prev"})
    prev["t"] = prev["t"] + 1
    assert not prev.duplicated(["bioguide", "t"]).any()
    panel = panel.merge(prev, on=["bioguide", "t"], how="left")
    panel["served_tm1"] = panel["id_prev"].notna()
    n_switch = int((panel["served_tm1"] & (panel["id_prev"] != panel["id"])).sum())
    log("rows with House service in t-1:", int(panel["served_tm1"].sum()),
        f"(of which {n_switch} have a different ICPSR in t-1)")

    # (a)
    med = vv.groupby("congress")["nominate_dim1"].median()
    vv["dist_median"] = (vv["nominate_dim1"] - vv["congress"].map(med)).abs()
    a = vv.set_index(["icpsr", "congress"])["dist_median"]
    key = pd.MultiIndex.from_arrays([panel["id_prev"].fillna(-1).astype(int), panel["t"] - 1])
    panel["a_dist_median"] = np.where(panel["served_tm1"], a.reindex(key).to_numpy(), np.nan)

    # (b), (c)
    panel_ids_by_t = {t: set(g["id"]) for t, g in panel.groupby("t")}
    net, net_stats = network_predictors(vv, panel_ids_by_t)
    net_stats.to_csv(OUT / "testD_network_stats.csv", index=False)
    netk = net.set_index(["bioguide", "congress"])
    key = pd.MultiIndex.from_arrays([panel["bioguide"], panel["t"] - 1])
    ok = panel["served_tm1"] & panel["t"].between(109, 118)
    for col, src in [("b_pagerank", "pagerank"), ("c_cross_share", "cross_share")]:
        panel[col] = np.where(ok, netk[src].reindex(key).to_numpy(), np.nan)
    log("rows t=109-118 with service in t-1:", int(ok.sum()), "; with (b):", int(panel["b_pagerank"].notna().sum()),
        "; with (c):", int(panel["c_cross_share"].notna().sum()))

    # (d)
    dm = class_years(vv)
    dm.to_csv(OUT / "testD_d_members.csv", index=False)
    log(f"(d) CLASS House members 106-110: {len(dm)}; without a Voteview first House Congress: "
        f"{int(dm['first_house_congress'].isna().sum())}; with any spell: {int(dm['any_spell'].sum())}; "
        f"years > 0: {int((dm['d_years'] > 0).sum())}; spells cut at Y: {int(dm['spell_cut_by_Y'].sum())}")
    panel["d_state_leg_years"] = panel["id"].map(dm.set_index("idno")["d_years"])
    log("(d) CLASS members with no row in the House panel:", int((~dm["idno"].isin(panel["id"])).sum()))

    cols = ["id", "t", "bioguide", "served_tm1", "a_dist_median", "b_pagerank", "c_cross_share", "d_state_leg_years"]
    panel[cols].sort_values(["id", "t"]).to_csv(OUT / "testD_predictors.csv", index=False)

    # Fit samples (sorted by id, as remlfit expects).
    samples = {
        "a_full": ("a_dist_median", panel["a_dist_median"].notna()),
        "a_t109_118": ("a_dist_median", panel["a_dist_median"].notna() & panel["t"].between(109, 118)),
        "b": ("b_pagerank", panel["b_pagerank"].notna()),
        "c": ("c_cross_share", panel["c_cross_share"].notna()),
        "d": ("d_state_leg_years", panel["d_state_leg_years"].notna()),
    }
    abc = panel[["a_dist_median", "b_pagerank", "c_cross_share"]].notna().all(axis=1)
    rows = []
    for name, (zcol, mask) in samples.items():
        df = panel[mask].sort_values(["id", "t"]).reset_index(drop=True)
        se, s_z, X, g = gls_se(df, zcol, s2a, s2e)
        se_check = gls_se_direct(X, g, s2a, s2e)
        assert abs(se - se_check) < 1e-9 * se, (se, se_check)
        r = {"sample": name, "predictor": zcol, "n_member_terms": len(df), "n_members": df["id"].nunique(),
             "t_min": int(df["t"].min()), "t_max": int(df["t"].max()), "s_z": s_z, "se_gamma_gls": se,
             "se_gamma_gls_direct_check": se_check, "role": "comparison only" if name == "a_t109_118" else "verdict"}
        for gm in GAMMAS:
            ps, a_cut = p_supported(gm, se)
            tag = f"{gm:.3f}".replace("0.", "")
            r[f"power_ci_excludes_0_g{tag}"] = power(gm, se)
            r[f"p_supported_g{tag}"] = ps
        r["a_cutoff"] = a_cut
        rows.append(r)
        log(name, {k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()})
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "testD_power.csv", index=False)
    info = {"sig2_alpha": s2a, "sig2_eps": s2e, "z_995": float(Z995), "threshold_les": THRESHOLD, "gammas": GAMMAS,
            "abc_rows": int(abc.sum()), "abc_members": int(panel.loc[abc, "id"].nunique()),
            "note": "Planning figures: GLS with Step 3 House variance components fixed. The test uses the "
                    "B = 2000 member bootstrap. No LES outcome used; no γ estimated.",
            "results": rows}
    (OUT / "testD_power.json").write_text(json.dumps(info, indent=2))
    log(f"rows with (a), (b), (c) all available (total-share sample): {info['abc_rows']} "
        f"member-terms, {info['abc_members']} members")
    (OUT / "testD_design_log.txt").write_text("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
