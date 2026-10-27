"""Fast REML for the random-intercept model y_it = X_it·β + α_i + ε_it.

α_i ~ N(0, σ²_α), ε_it ~ N(0, σ²_ε). With λ = σ²_α/σ²_ε, each member's covariance is
σ²_ε (I + λJ). Quasi-demeaning by θ_i = 1 - 1/sqrt(1 + n_i λ) turns GLS into OLS, so
the REML criterion profiles to a 1-D search over log λ. Results are checked against
statsmodels MixedLM in step3_test_A.py.
"""
import numpy as np
from scipy.optimize import minimize_scalar


def _group_index(ids):
    _, g = np.unique(ids, return_inverse=True)
    n = np.bincount(g)
    return g, n


def _transform(y, X, g, n, lam):
    theta = 1.0 - 1.0 / np.sqrt(1.0 + n * lam)
    th = theta[g]
    ybar = np.bincount(g, weights=y) / n
    Xbar = np.stack([np.bincount(g, weights=X[:, j]) / n for j in range(X.shape[1])], axis=1)
    return y - th * ybar[g], X - th[:, None] * Xbar[g]


def _neg2_reml(loglam, y, X, g, n):
    lam = np.exp(loglam)
    ys, Xs = _transform(y, X, g, n, lam)
    XtX = Xs.T @ Xs
    beta = np.linalg.solve(XtX, Xs.T @ ys)
    rss = np.sum((ys - Xs @ beta) ** 2)
    N, p = X.shape
    _, logdet = np.linalg.slogdet(XtX)
    return (N - p) * np.log(rss / (N - p)) + np.sum(np.log1p(n * lam)) + logdet


def drop_constant_columns(X, names):
    keep = [0] + [j for j in range(1, X.shape[1]) if np.ptp(X[:, j]) > 0]
    return X[:, keep], [names[j] for j in keep]


def fit(y, X, ids):
    """Return dict with beta, sig2_alpha, sig2_eps, kappa, and per-member BLUPs.

    X must include an intercept column first. Constant columns are dropped.
    """
    g, n = _group_index(ids)
    res = minimize_scalar(_neg2_reml, bounds=(-20, 5), args=(y, X, g, n),
                          method="bounded", options={"xatol": 1e-7})
    lam = np.exp(res.x)
    ys, Xs = _transform(y, X, g, n, lam)
    beta = np.linalg.solve(Xs.T @ Xs, Xs.T @ ys)
    N, p = X.shape
    sig2_eps = np.sum((ys - Xs @ beta) ** 2) / (N - p)
    sig2_alpha = lam * sig2_eps
    resid = y - X @ beta
    rbar = np.bincount(g, weights=resid) / n
    blup = (n * lam / (1.0 + n * lam)) * rbar
    xb = X @ beta
    return {
        "beta": beta,
        "sig2_alpha": sig2_alpha,
        "sig2_eps": sig2_eps,
        "kappa": sig2_alpha / (sig2_alpha + sig2_eps),
        "var_xb": np.var(xb),
        "marginal_r2": np.var(xb) / (np.var(xb) + sig2_alpha + sig2_eps),
        "ids": np.unique(ids),
        "blup": blup,
        "n_terms": n,
        "loglam_at_bound": res.x <= -19.9 or res.x >= 4.9,
    }
