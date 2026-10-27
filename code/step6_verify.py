"""Step 6: check every number in post.qmd against output/.

A. Every {{< var >}} in post.qmd exists in _variables.yml; every {{< include >}} file exists.
B. Every number in the rendered post (post.html, prose and tables) is traced to a source:
   output/ (any CSV/JSON value that rounds to the shown number at the shown precision),
   PREREG.md (thresholds), a code constant, or the data itself (CLASS coverage and codes).
   A number with no source is a MISMATCH.
C. Key numbers are recomputed from the output/ files by separate code here, including the
   PREREG decision rules, and compared with the post's strings. Wilson CIs use statsmodels.
D. Hand-typed numbers in post.qmd (outside shortcodes) are listed with their source.

Writes output/step6_verify.md. Exit status 1 if anything fails.
Usage: python -I step6_verify.py
"""
import html
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
NUM = re.compile(r"(?<![A-Za-z_\d.])[−+-]?\d[\d,]*(?:\.\d+)?%?")


def parse(tok):
    t = tok.replace("−", "-").replace(",", "").rstrip("%")
    d = len(t.split(".")[1]) if "." in t else 0
    return float(t), d


def load_yaml_vars(path):
    v, sec = {}, None
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        if not line.startswith(" "):
            sec = line.rstrip(":")
        else:
            k, val = line.strip().split(": ", 1)
            v[f"{sec}.{k}"] = val.strip('"')
    return v


def pool_from_outputs():
    """(value, source) for every number in output/ CSV and JSON files (not tables/figures)."""
    pool = []
    for f in sorted(OUT.rglob("*")):
        if f.parent.name in ("tables", "figures") or f.name == "step3_oos_pairs.csv":
            continue
        rel = f.relative_to(ROOT).as_posix()
        if f.suffix == ".csv":
            df = pd.read_csv(f)
            for c in df.columns:
                for i, x in enumerate(df[c]):
                    if isinstance(x, (int, float, np.integer, np.floating)) and not pd.isna(x) and not isinstance(x, bool):
                        pool.append((float(x), f"{rel}:{c}[{i}]"))
                    elif isinstance(x, str):
                        for m in re.findall(r"\d+\.\d+|\d+", x):
                            pool.append((float(m), f"{rel}:{c}[{i}] (text)"))
        elif f.suffix == ".json":
            def walk(o, path):
                if isinstance(o, dict):
                    for k, x in o.items():
                        walk(x, f"{path}.{k}")
                elif isinstance(o, list):
                    for i, x in enumerate(o):
                        walk(x, f"{path}[{i}]")
                elif isinstance(o, (int, float)) and not isinstance(o, bool):
                    pool.append((float(o), f"{rel}{path}"))
            walk(json.loads(f.read_text()), "")
    k = pd.read_csv(OUT / "step3_kappa.csv").set_index("body")
    for b in k.index:  # PREREG threshold in LES points (D9): 0.20 × full-panel σ̂_α
        pool.append((0.20 * k.loc[b, "sigma_alpha"], f"derived: 0.20 × output/step3_kappa.csv:sigma_alpha[{b}]"))
    return pool


def prereg_numbers():
    txt = (ROOT / "PREREG.md").read_text()
    return {parse(t)[0] for t in NUM.findall(txt)}, txt


def data_constants():
    """Numbers the post states that come from the data or code, not from output/."""
    sys.path.insert(0, str(ROOT / "code"))
    import step4_skill_source as s4
    import explore_law_mixed as ex
    c = pd.read_stata(s4.CLASS, convert_categoricals=False, columns=["cong"])
    with pd.io.stata.StataReader(s4.CLASS) as r:
        lab = r.value_labels()["occupation"]
    lawyer_codes = sorted(k for k, v in lab.items() if str(v).startswith("Lawyer"))
    src = (ROOT / "code" / "explore_law_mixed.py").read_text()
    consts = {
        int(c["cong"].min()): "CLASS first Congress (data)",
        int(c["cong"].max()): "CLASS last Congress (data)",
        lawyer_codes[0]: f"CLASS occupation value labels: Lawyer codes {lawyer_codes}",
        lawyer_codes[-1]: f"CLASS occupation value labels: Lawyer codes {lawyer_codes}",
        s4.MIN_HOLDERS: "code/step4_skill_source.py MIN_HOLDERS (deviation D3)",
        1.9: f"CLASS file name {s4.CLASS.name}",
    }
    if "norm.ppf(0.975) + norm.ppf(0.80)" in src:
        consts[0.05] = "code/explore_law_mixed.py: two-sided α = 0.05 (z_0.975)"
        consts[80.0] = "code/explore_law_mixed.py: 80% power (z_0.80)"
    return consts


DATE_TOKENS, XREF = set(), {}


def cross_refs(qmd):
    """'(deviation N below)' must point at the deviation list item about which σ_α."""
    out = {}
    m = re.search(r"\(deviation (\d+) below\)", qmd)
    if m:
        dev = qmd[qmd.index("# Deviations from the pre-registration"):qmd.index("# Exploratory analyses")]
        item = re.search(rf"^{m.group(1)}\. (.*)$", dev, flags=re.M)
        ok = item is not None and item.group(1).startswith("**Which σ_α.**")
        out[m.group(1)] = f"cross-reference to deviation list item {m.group(1)} ({'points to Which σ_α: OK' if ok else 'WRONG ITEM'})"
        if not ok:
            raise SystemExit("bad deviation cross-reference")
    return out


def section_b(text, V):
    pool = pool_from_outputs()
    pre, pre_txt = prereg_numbers()
    consts = data_constants()
    vals = np.array([p[0] for p in pool])
    rows, bad = [], []
    for tok in sorted(set(NUM.findall(text)), key=lambda t: (parse(t)[0], t)):
        x, d = parse(tok)
        srcs = []
        targets = [x / 100] if tok.endswith("%") else [x]
        for tval in targets:
            tol = 0.5 * 10 ** (-d) + 1e-12 if d else 1e-9
            hit = np.flatnonzero(np.abs(vals - tval) <= tol * (1 if not tok.endswith("%") else 1 / 100))
            if tok.endswith("%"):
                hit = np.flatnonzero(np.abs(vals * 100 - x) <= 0.5 * 10 ** (-d) + 1e-12)
            srcs += [pool[i][1] for i in hit[:3]]
            if len(hit) > 3:
                srcs.append(f"... {len(hit)} matches in output/")
        if x in pre:
            srcs.insert(0, "PREREG.md")
        for k, v in consts.items():
            if abs(x - k) < 1e-9:
                srcs.insert(0, v)
        if re.fullmatch(r"20\d\d", tok) or tok in DATE_TOKENS:
            srcs.insert(0, "post date (front matter; section D)")
        if tok in XREF:
            srcs.insert(0, XREF[tok])
        rows.append((tok, srcs))
        if not srcs:
            bad.append(tok)
    return rows, bad


def section_c(V):
    """Separate recomputation of key numbers from output/ files, plus the PREREG rules."""
    from statsmodels.stats.proportion import proportion_confint
    k = pd.read_csv(OUT / "step3_kappa.csv").set_index("body")
    o = pd.read_csv(OUT / "step3_oos.csv").set_index("body")
    co = pd.read_csv(OUT / "step4_coefs.csv").set_index(["body", "term"])
    cnt = pd.read_csv(OUT / "step4_counts.csv").set_index("body")
    u = pd.read_csv(OUT / "exploratory" / "expl_law_units.csv")
    rk = json.loads((OUT / "exploratory" / "expl_rank_house.json").read_text())
    lr = json.loads((OUT / "exploratory" / "expl_law_results.json").read_text())
    f3 = lambda x: f"{x:.3f}"
    s3 = lambda x: f"{x:+.3f}".replace("-", "−")
    checks = []

    def chk(var, expected):
        got = V.get(var)
        checks.append((var, got, expected, got == expected))

    def rule_a(kappa, lo, hi):
        if kappa < 0.10:
            return "not supported"
        if kappa >= 0.20 and not (lo <= 0 <= hi):
            return "supported as a measurable trait"
        return "weak"

    def rule_jd(e, lo, hi):
        if e >= 0.20 and lo > 0:
            return "JD favors law school as a skill source"
        if (lo <= 0 <= hi) or e < 0.10:
            return "no evidence for a JD skill premium"
        return "inconclusive"

    for b in ["House", "Senate", "States"]:
        p = b.lower()
        for var, col in [("kappa", "kappa"), ("kappa_lo", "kappa_lo"), ("kappa_hi", "kappa_hi"), ("r2", "marginal_r2"),
                         ("sig2_alpha", "sig2_alpha"), ("sig2_eps", "sig2_eps"), ("sigma_alpha", "sigma_alpha")]:
            chk(f"{p}.{var}", f3(k.loc[b, col]))
        for var, col in [("r", "r"), ("r_lo", "r_lo"), ("r_hi", "r_hi")]:
            chk(f"{p}.{var}", f3(o.loc[b, col]))
        chk(f"{p}.rows", f"{int(k.loc[b, 'n_rows']):,}")
        chk(f"{p}.members", f"{int(k.loc[b, 'n_members']):,}")
        chk(f"{p}.verdict", rule_a(k.loc[b, "kappa"], o.loc[b, "r_lo"], o.loc[b, "r_hi"]))
    chk("house.kappa_lo5", f"{k.loc['House', 'kappa_lo']:.5f}")
    for b, p in [("House", "s4house"), ("Senate", "s4senate")]:
        r = co.loc[(b, "law_deg")]
        chk(f"{p}.jd", f3(r["estimate_sigma_alpha_units"]))
        chk(f"{p}.jd_lo", s3(r["ci_lo"]))
        chk(f"{p}.jd_hi", s3(r["ci_hi"]))
        chk(f"{p}.verdict", rule_jd(r["estimate_sigma_alpha_units"], r["ci_lo"], r["ci_hi"]))
        chk(f"{p}.econ", str(int(cnt.loc[b, "econ_phd"])))
        chk(f"{p}.law", str(int(cnt.loc[b, "law_degree"])))
    jd_h = rule_jd(co.loc[("House", "law_deg"), "estimate_sigma_alpha_units"], co.loc[("House", "law_deg"), "ci_lo"],
                   co.loc[("House", "law_deg"), "ci_hi"])
    combined_fail = not (k.loc["House", "kappa"] >= 0.20 and jd_h.startswith("JD favors"))
    chk("combined.verdict", "the data gives no recommendation for law school" if combined_fail else "not yet determined (Test C pending)")
    for b, c in [("House", "h"), ("Senate", "s")]:
        sig = k.loc[b, "sigma_alpha"]
        chk(f"expl.{b.lower()}_thr_les", f3(0.20 * sig))
        for tag, an, term in [("s4", "PREREG step4 (OLS on BLUP)", "law_deg"), ("e1", "E1/E2 mixed model: degree", "law_deg"),
                              ("e2", "E1/E2 mixed model: occupation", "lawyer_occ")]:
            r = u[(u["body"] == b) & (u["analysis"] == an) & (u["term"] == term)]
            les = r[r["unit"] == "LES points"].iloc[0]
            full = r[r["unit"].str.startswith("full-panel")].iloc[0]
            chk(f"expl.{tag}{c}_les", s3(les["estimate"]))
            chk(f"expl.{tag}{c}_full", s3(full["estimate"]))
            if tag == "e1":  # full-panel units = LES points / full-panel σ̂_α
                chk(f"expl.{tag}{c}_full", s3(les["estimate"] / sig))
            se = float(full["boot_se"])
            from scipy.stats import norm
            pw = norm.cdf(0.20 / se - norm.ppf(0.975)) + norm.cdf(-0.20 / se - norm.ppf(0.975))
            chk(f"expl.{tag}{c}_pow", f"{pw:.2f}")
            chk(f"expl.{tag}{c}_mde_full", f3((norm.ppf(0.975) + norm.ppf(0.8)) * se))
    chk("expl.rank_kappa", f3(rk["kappa"]))
    chk("expl.rank_r", f3(rk["oos_r"]))
    for (kk, nn), suf in [((3, len(lr["unmatched_icpsr"]) + lr["matched_people"]), "all"), ((3, lr["matched_people"]), "m")]:
        lo, hi = proportion_confint(kk, nn, alpha=0.05, method="wilson")
        chk(f"expl.econ_lo_{suf}", f"{100 * lo:.2f}%")
        chk(f"expl.econ_hi_{suf}", f"{100 * hi:.2f}%")
    chk("expl.matched", f"{lr['matched_people']:,}")
    return checks


def main():
    V = load_yaml_vars(ROOT / "_variables.yml")
    qmd = (ROOT / "post.qmd").read_text()
    report, fail = ["# Step 6 verification", ""], False

    used = re.findall(r"\{\{< var ([\w.]+) >\}\}", qmd)
    missing = sorted({u for u in used if u not in V})
    incs = re.findall(r"\{\{< include ([^ ]+) >\}\}", qmd)
    miss_inc = [i for i in incs if not (ROOT / i).exists()]
    figs = re.findall(r"\]\((output/figures/[^)]+)\)", qmd)
    miss_fig = [f for f in figs if not (ROOT / f).exists()]
    report += ["## A. Shortcodes", f"- var shortcodes used: {len(used)} ({len(set(used))} distinct); missing from _variables.yml: {missing or 'none'}",
               f"- includes: {len(incs)}; missing: {miss_inc or 'none'}", f"- figures: {len(figs)}; missing: {miss_fig or 'none'}", ""]
    fail |= bool(missing or miss_inc or miss_fig)

    h = (ROOT / "post.html").read_text()
    h = h[h.find("<main"):]
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", h))
    if "?var:" in text:
        fail = True
        report.append("**Unresolved shortcode in post.html.**")
    global XREF
    XREF = cross_refs(qmd)
    d = pd.Timestamp(re.search(r"^date: (.+)$", qmd, flags=re.M).group(1).strip())
    DATE_TOKENS.update({f"{d.day},", str(d.day), str(d.year)})
    rows, bad = section_b(text, V)
    report += ["## B. Every number in the rendered post", f"- distinct numbers: {len(rows)}; with no source (MISMATCH): {bad or 'none'}", "",
               "| Number | Sources (first matches) |", "|---|---|"]
    report += [f"| {t} | {'; '.join(s) if s else '**NO SOURCE**'} |" for t, s in rows]
    report.append("")
    fail |= bool(bad)

    checks = section_c(V)
    nbad = [c for c in checks if not c[3]]
    report += ["## C. Key numbers recomputed separately from output/", f"- checks: {len(checks)}; failed: {len(nbad)}", "",
               "| Variable | In post | Recomputed | OK |", "|---|---|---|---|"]
    report += [f"| {v} | {g} | {e} | {'yes' if ok else '**NO**'} |" for v, g, e, ok in checks]
    report.append("")
    fail |= bool(nbad)

    body = re.sub(r"\{\{<.*?>\}\}", "", qmd)
    fm_date = re.search(r"^date: (.+)$", qmd, flags=re.M).group(1).strip()
    lit = sorted(set(NUM.findall(body.split("---", 2)[2])), key=lambda t: parse(t)[0])
    report += ["## D. Numbers typed by hand in post.qmd (outside shortcodes and front matter)", "",
               ", ".join(lit), "", f"- Front-matter date: {fm_date}. It is typed by hand, not computed; it is the post's date, not a result.", ""]
    (OUT / "step6_verify.md").write_text("\n".join(report))
    print("\n".join(report[:12]))
    print("B mismatches:", bad or "none", "| C failed:", [c[0] for c in nbad] or "none")
    print("hand-typed:", lit)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
