"""Step 5: figures for post.qmd. Reads only files in output/. Font: IBM Plex Sans.

Figures 1–4 show PREREG results. Figure 5 is EXPLORATORY and says so in its title.

Usage: python -I step5_figures.py   (writes output/figures/*.png)
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
FIG = OUT / "figures"

font_manager.findfont("IBM Plex Sans", fallback_to_default=False)  # fail loudly if missing
plt.rcParams.update({
    "font.family": "IBM Plex Sans", "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "semibold",
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 100, "savefig.dpi": 200,
    "savefig.bbox": "tight",
})
INK, MUTED, ACCENT, ACCENT2, GREY = "#1f2328", "#6e7781", "#0f62fe", "#da1e28", "#c6c6c6"
BODIES = ["House", "Senate", "States"]


def save(fig, name):
    fig.savefig(FIG / f"{name}.png")
    plt.close(fig)


def fig_variance(kap):
    fig, ax = plt.subplots(figsize=(6.5, 2.4))
    cols = [("share_x", "Role and party (X_it·β)", GREY), ("share_alpha", "Member (α_i)", ACCENT),
            ("share_eps", "Term-to-term noise (ε_it)", "#e0e0e0")]
    for k, b in enumerate(BODIES[::-1]):
        row = kap.loc[b]
        left = 0.0
        for c, lab, col in cols:
            ax.barh(k, row[c], left=left, color=col, edgecolor="white", label=lab if k == 0 else None)
            ax.text(left + row[c] / 2, k, f"{row[c]:.2f}", ha="center", va="center", fontsize=9,
                    color="white" if col == ACCENT else INK)
            left += row[c]
    ax.set_yticks(range(3), BODIES[::-1])
    ax.set_xlim(0, 1)
    ax.set_xlabel("Share of the model's variance in LES")
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.32), frameon=False, fontsize=9)
    ax.set_title("Where the variance in lawmaking effectiveness sits (PREREG)", loc="left")
    save(fig, "fig1_variance_shares")


def fig_kappa(kap, oos):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.6), sharey=True)
    ax = axes[0]
    for y0, lab in [(0.10, "0.10"), (0.20, "0.20")]:
        ax.axvline(y0, color=MUTED, lw=0.8, ls="--")
        ax.text(y0 + 0.005, -0.45, lab, color=MUTED, fontsize=8, ha="left")
    for k, b in enumerate(BODIES[::-1]):
        r = kap.loc[b]
        col = ACCENT if b == "House" else INK
        ax.plot([r["kappa_lo"], r["kappa_hi"]], [k, k], color=col, lw=2)
        ax.plot(r["kappa"], k, "o", color=col)
    ax.set_yticks(range(3), BODIES[::-1])
    ax.set_ylim(-0.6, 2.4)
    ax.set_xlim(0, 0.45)
    ax.set_xlabel("κ = σ²_α / (σ²_α + σ²_ε)")
    ax.set_title("κ, 95% CI", loc="left")
    ax = axes[1]
    ax.axvline(0, color=MUTED, lw=0.8)
    for k, b in enumerate(BODIES[::-1]):
        r = oos.loc[b]
        col = ACCENT if b == "House" else INK
        ax.plot([r["r_lo"], r["r_hi"]], [k, k], color=col, lw=2)
        ax.plot(r["r"], k, "o", color=col)
    ax.set_xlim(-0.05, 0.65)
    ax.set_xlabel("Out-of-sample Pearson r")
    ax.set_title("Out-of-sample r, 95% CI", loc="left")
    fig.suptitle("Test A: is skill a stable trait? (PREREG; House is primary)", x=0.01, ha="left",
                 fontweight="semibold", y=1.06)
    save(fig, "fig2_kappa_r")


def fig_oos(pairs, oos):
    p = pairs[pairs["body"] == "House"].copy()
    p["bin"] = pd.qcut(p["alpha_hat_prior"], 20, labels=False, duplicates="drop")
    g = p.groupby("bin")[["alpha_hat_prior", "resid_t"]].mean()
    fig, ax = plt.subplots(figsize=(5, 3.6))
    ax.axhline(0, color=GREY, lw=0.8)
    ax.axvline(0, color=GREY, lw=0.8)
    ax.plot(g["alpha_hat_prior"], g["resid_t"], "o", color=ACCENT)
    r = oos.loc["House"]
    ax.text(0.03, 0.95, f"r = {r['r']:.3f} (95% CI {r['r_lo']:.3f} to {r['r_hi']:.3f})\n"
            f"{int(r['n_pairs']):,} member-terms, {int(r['n_members']):,} members",
            transform=ax.transAxes, va="top", fontsize=9, color=INK)
    ax.set_xlabel("α̂_i estimated only from earlier Congresses")
    ax.set_ylabel("LES residual in the next Congress")
    ax.set_title("House: past skill predicts future effectiveness (PREREG)\nEach dot: mean of one twentieth of member-terms",
                 loc="left")
    save(fig, "fig3_oos_house")


def fig_step4(co):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.2), gridspec_kw={"width_ratios": [3, 2]}, layout="constrained")
    names = {"law_deg": "Law degree", "phd": "Doctorate", "female": "Female", "black": "Black", "hispanic": "Hispanic"}
    for ax, body in zip(axes, ["House", "Senate"]):
        c = co[(co["body"] == body) & (co["term"] != "Intercept")].reset_index(drop=True)[::-1]
        ax.axvline(0, color=MUTED, lw=0.8)
        for x in (0.10, 0.20):
            ax.axvline(x, color=MUTED, lw=0.8, ls="--")
        for k, (_, r) in enumerate(c.iterrows()):
            col = ACCENT if r["term"] == "law_deg" else INK
            ax.plot([r["ci_lo"], r["ci_hi"]], [k, k], color=col, lw=2)
            ax.plot(r["estimate_sigma_alpha_units"], k, "o", color=col)
        ax.set_yticks(range(len(c)), [names[t] for t in c["term"]])
        ax.set_title(f"{body} (n = {int(c['n'].iloc[0])})", loc="left")
        ax.set_xlabel("Effect on α̂_i, in σ_α units")
        ax.set_xlim(-0.35, 0.75)
        ax.set_xticks([-0.2, 0, 0.2, 0.4, 0.6])
    fig.suptitle("Skill source: background and α̂_i, Congresses 106–110 (PREREG)\nDashed lines: 0.10σ_α and 0.20σ_α",
                 x=0.01, ha="left", fontweight="semibold")
    save(fig, "fig4_skill_source")


def fig_explore(units):
    """House law effects in full-panel σ_α units (D9). The joint-model terms are not shown."""
    specs = [("PREREG step4 (OLS on BLUP)", "law_deg", "PREREG: law degree (OLS on α̂_i)", True),
             ("E1/E2 mixed model: degree", "law_deg", "E1: law degree, mixed model", False),
             ("E1/E2 mixed model: occupation", "lawyer_occ", "E2: lawyer occupation, mixed model", False)]
    h = units[(units["body"] == "House") & units["unit"].str.startswith("full-panel")]
    fig, ax = plt.subplots(figsize=(6.5, 2.2))
    ax.axvline(0, color=MUTED, lw=0.8)
    for x in (0.10, 0.20):
        ax.axvline(x, color=MUTED, lw=0.8, ls="--")
    for k, (an, term, lab, pre) in enumerate(specs[::-1]):
        r = h[(h["analysis"] == an) & (h["term"] == term)].iloc[0]
        col = ACCENT if pre else MUTED
        ax.plot([r["ci_lo"], r["ci_hi"]], [k, k], color=col, lw=2)
        ax.plot(r["estimate"], k, "o", color=col)
    ax.set_yticks(range(len(specs)), [s[2] for s in specs[::-1]])
    ax.set_xlabel("Effect in units of the full-panel σ_α (House)")
    ax.set_title("House law effects, 95% CI. EXPLORATORY except the top row", loc="left")
    save(fig, "fig5_exploratory_law")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    kap = pd.read_csv(OUT / "step3_kappa.csv").set_index("body")
    oos = pd.read_csv(OUT / "step3_oos.csv").set_index("body")
    pairs = pd.read_csv(OUT / "step3_oos_pairs.csv")
    co = pd.read_csv(OUT / "step4_coefs.csv")
    units = pd.read_csv(OUT / "exploratory" / "expl_law_units.csv")
    fig_variance(kap)
    fig_kappa(kap, oos)
    fig_oos(pairs, oos)
    fig_step4(co)
    fig_explore(units)
    print(sorted(p.name for p in FIG.glob("*.png")))


if __name__ == "__main__":
    main()
