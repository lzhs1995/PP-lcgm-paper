"""Round2F exact conditional-Gaussian log-likelihood check (no optimisation).

For the PP-LGCM E0/E0B/E1/E1B structures, z0 is an observed exogenous covariate, so the
latent-by-observed product SXZ = SX*z0 turns into a person-specific coefficient
B[SY,SX](z) = bss + dc*z. Given z0 and the controls, the model is linear-Gaussian and the
observed-data log-likelihood has a closed form. This script evaluates it at the parameter
values Mplus saved (matrix_values.csv) and compares it with the printed H0 log-likelihood.

It does not estimate anything, prints no SE or P value and writes no person-level values.
Supported: continuous indicators, observed exogenous covariates, XWITH products of one latent
factor with one observed covariate. Anything else stops with an error.
"""
import argparse, csv, hashlib, json, math, os, re, sys
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def read_inp(path):
    txt = open(path, encoding='utf-8', errors='replace').read()
    up = txt.upper()
    m = re.search(r'NAMES\s*=\s*(.*?);', txt, re.S | re.I)
    names = [s.upper() for s in m.group(1).split()]
    m = re.search(r'USEVARIABLES\s*=\s*(.*?);', txt, re.S | re.I)
    use = []
    for tok in m.group(1).split():
        tok = tok.upper()
        r = re.fullmatch(r'([A-Z_]+)(\d+)-([A-Z_]+)(\d+)', tok)
        if r and r.group(1) == r.group(3):
            use += [f'{r.group(1)}{i}' for i in range(int(r.group(2)), int(r.group(4)) + 1)]
        else:
            use.append(tok)
    m = re.search(r'MISSING\s*=\s*(\S+?)\s*;', txt, re.I)
    missing = m.group(1) if m else '.'
    prods = {}
    for a, b, c in re.findall(r'(\w+)\s*\|\s*(\w+)\s+XWITH\s+(\w+)\s*;', txt, re.I):
        prods[a.upper()] = (b.upper(), c.upper())
    if 'TYPE' in up and re.search(r'TYPE\s*=[^;]*MIXTURE', up):
        raise SystemExit('UNSUPPORTED: mixture')
    if re.search(r'CATEGORICAL|COUNT|CENSORED|NOMINAL|WEIGHT', up.split('ANALYSIS:')[0]):
        raise SystemExit('UNSUPPORTED: non-continuous outcomes or weights')
    if re.search(r'^\s*DEFINE\s*:', up, re.M):
        raise SystemExit('UNSUPPORTED: DEFINE (derived variables are not rebuilt here)')
    return names, use, missing, prods


def read_mats(path):
    mats = {}
    with open(path, newline='', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            mats.setdefault(r['matrix'].upper(), []).append((r['row'].upper(), r['column'].upper(), float(r['value'])))
    return mats


def printed_ll(out_path):
    if not os.path.exists(out_path):
        return None, None
    txt = open(out_path, encoding='utf-8', errors='replace').read()
    m = re.search(r'H0 Value\s+(-?[\d.]+)', txt)
    n = re.search(r'Number of observations\s+(\d+)', txt)
    return (float(m.group(1)) if m else None), (int(n.group(1)) if n else None)


def build(mats, prods):
    eta = [c for (_, c, _) in mats['ALPHA']]
    ys = [c for (_, c, _) in mats['NU']]
    E = {n: i for i, n in enumerate(eta)}
    Y = {n: i for i, n in enumerate(ys)}
    B = np.zeros((len(eta), len(eta))); P = np.zeros_like(B)
    L = np.zeros((len(ys), len(eta))); T = np.zeros((len(ys), len(ys)))
    a = np.array([v for (_, _, v) in mats['ALPHA']]); nu = np.array([v for (_, _, v) in mats['NU']])
    for r, c, v in mats['BETA']: B[E[r], E[c]] = v
    for r, c, v in mats['PSI']: P[E[r], E[c]] = P[E[c], E[r]] = v
    for r, c, v in mats['LAMBDA']: L[Y[r], E[c]] = v
    for r, c, v in mats['THETA']: T[Y[r], Y[c]] = T[Y[c], Y[r]] = v
    for k in ('GAMMA', 'TAU', 'KAPPA'):
        if k in mats and any(v != 0 for (_, _, v) in mats[k]):
            raise SystemExit(f'UNSUPPORTED: nonzero {k}')
    # observed exogenous: eta with an identity loading from a same-named indicator, no regression row,
    # and not loading anything else -> conditioned on, like Mplus does for covariates
    exo = []
    for n in eta:
        if n in prods: continue
        if n in Y and L[Y[n], E[n]] == 1 and not B[E[n]].any() and np.count_nonzero(L[:, E[n]]) == 1:
            exo.append(n)
    for p, (f, z) in prods.items():
        if p not in E: raise SystemExit(f'product {p} not in TECH1 eta')
        if z not in exo or f in exo:
            raise SystemExit('UNSUPPORTED: product must be latent x observed covariate')
        if B[E[p]].any() or L[:, E[p]].any(): raise SystemExit('UNSUPPORTED: product with loadings/regressors')
    en = [n for n in eta if n not in exo and n not in prods]
    dep = [n for n in ys if n not in exo]
    return dict(eta=eta, E=E, ys=ys, Y=Y, B=B, P=P, L=L, T=T, a=a, nu=nu, exo=exo, en=en, dep=dep)


def loglik(M, prods, data, names, missing_code, allow_indefinite=False):
    E, Y = M['E'], M['Y']
    ie = [E[n] for n in M['en']]; ix = [E[n] for n in M['exo']]
    iy_dep = [Y[n] for n in M['dep']]
    col = {n: names.index(n) for n in set(M['exo']) | set(M['dep'])}
    Ben = M['B'][np.ix_(ie, ie)]; Bex = M['B'][np.ix_(ie, ix)]
    Pen = M['P'][np.ix_(ie, ie)]
    Len = M['L'][np.ix_(iy_dep, ie)]; Lex = M['L'][np.ix_(iy_dep, ix)]
    Tdd = M['T'][np.ix_(iy_dep, iy_dep)]; nud = M['nu'][iy_dep]; aen = M['a'][ie]
    if np.any(M['P'][np.ix_(ie,ix)] != 0):
        raise SystemExit('UNSUPPORTED: endogenous-exogenous residual covariance')
    # product terms: for row r with coefficient on product p=f*z, add coef*z to B[r,f]
    padd = []
    for p, (f, z) in prods.items():
        colp = M['B'][np.ix_(ie, [E[p]])][:, 0]
        for k, v in enumerate(colp):
            if v != 0: padd.append((k, M['en'].index(f), v, M['exo'].index(z)))
    eig = np.linalg.eigvalsh(Pen)
    if eig.min() < -1e-10 and not allow_indefinite:
        raise SystemExit(f'INADMISSIBLE: latent residual covariance has negative eigenvalue {eig.min():.3g}; use --diagnostic-allow-indefinite-latent for a diagnostic-only value')
    X = data[:, [col[n] for n in M['exo']]]; Yd = data[:, [col[n] for n in M['dep']]]
    ll = 0.0; n_used = 0; n_drop = 0; patt = set(); min_eig_obs = math.inf
    I = np.eye(len(ie))
    for i in range(data.shape[0]):
        x = X[i]
        if np.isnan(x).any(): n_drop += 1; continue
        obs = ~np.isnan(Yd[i])
        if not obs.any(): n_drop += 1; continue
        Bz = Ben.copy()
        for (r, f, v, zi) in padd: Bz[r, f] += v * x[zi]
        A = np.linalg.solve(I - Bz, I)
        mu_eta = A @ (aen + Bex @ x)
        S_eta = A @ Pen @ A.T
        mu = nud + Len @ mu_eta + Lex @ x
        S = Len @ S_eta @ Len.T + Tdd
        So = S[np.ix_(obs, obs)]; r_ = Yd[i, obs] - mu[obs]
        c = np.linalg.cholesky(So)
        min_eig_obs = min(min_eig_obs, float(np.linalg.eigvalsh(So).min()))
        sol = np.linalg.solve(c, r_)
        ll += -0.5 * (obs.sum() * math.log(2 * math.pi) + 2 * np.log(np.diag(c)).sum() + sol @ sol)
        n_used += 1; patt.add(tuple(obs))
    return ll, n_used, n_drop, len(patt), float(eig.min()), min_eig_obs


def load_data(path, names, missing_code):
    rows = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            t = line.split()
            if not t: continue
            if len(t) != len(names): raise SystemExit(f'data row has {len(t)} fields, NAMES has {len(names)}')
            rows.append([np.nan if s == missing_code else float(s) for s in t])
    return np.array(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--model-dir', required=True)
    ap.add_argument('--data', required=True, help='the exact local data file the model read')
    ap.add_argument('--output', required=True)
    ap.add_argument('--diagnostic-allow-indefinite-latent', action='store_true')
    a = ap.parse_args(argv)
    names, use, miss, prods = read_inp(os.path.join(a.model_dir, 'model.inp'))
    mats = read_mats(os.path.join(a.model_dir, 'matrix_values.csv'))
    M = build(mats, prods)
    data = load_data(a.data, names, miss)
    ll, n, drop, npat, mineig, mineig_obs = loglik(M, prods, data, names, miss, a.diagnostic_allow_indefinite_latent)
    pll, pn = printed_ll(os.path.join(a.model_dir, 'model.out'))
    res = dict(model_dir=os.path.basename(os.path.normpath(a.model_dir)), data_sha256=sha256(a.data),
               matrix_values_sha256=sha256(os.path.join(a.model_dir, 'matrix_values.csv')),
               products={k: list(v) for k, v in prods.items()}, conditioned_on=M['exo'], indicators=M['dep'],
               n_used=n, n_dropped_no_outcome_or_missing_x=drop, mplus_n=pn, n_matches_mplus=(pn == n),
               missing_patterns=npat,
               exact_LL=round(ll, 6), mplus_printed_LL=pll,
               difference=None if pll is None else round(ll - pll, 6),
               min_latent_residual_eigenvalue=mineig, min_observed_cov_eigenvalue=mineig_obs,
               diagnostic_only=bool(a.diagnostic_allow_indefinite_latent and mineig < 0),
               note='Evaluation at saved estimates only; no optimisation, SE or P value; no person-level output.')
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    with open(a.output, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=2)
    print(json.dumps({k: res[k] for k in ('model_dir', 'n_used', 'mplus_n', 'exact_LL', 'mplus_printed_LL', 'difference')}))


if __name__ == '__main__':
    main()
