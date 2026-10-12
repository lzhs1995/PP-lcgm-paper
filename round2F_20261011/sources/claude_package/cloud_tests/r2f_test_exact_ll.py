"""r2f_exact_ll.py 的独立单元测试（不依赖 Mplus）。
1) 蒙特卡罗路线：按原始结构方程逐人模拟潜变量（SXZ = SX*z0，不用“条件线性”化简），对测量误差解析积分，
   平均得到每人观测数据密度，与核对器的逐人对数似然比较（含缺失模式、不同 z0、负 z0）。
2) 拒收路线：Ψ 不定且无诊断标志、DEFINE、非零 GAMMA、潜×潜乘积、数据列数不符。
用法：python3 r2f_test_exact_ll.py <path/to/r2f_exact_ll.py> <work_dir>"""
import csv, json, math, os, subprocess, sys
from pathlib import Path
import numpy as np

tool, work = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(); work.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(26101010)
ETA = ['IX', 'SX', 'IY', 'SY', 'SXZ', 'Z0', 'C1']; IND = ['X1', 'X2', 'X3', 'Y1', 'Y2', 'Y3', 'Z0', 'C1']
EX = ['Z0', 'C1']; EN = ['IX', 'SX', 'IY', 'SY']


def base_params():
    P = {}
    P['alpha'] = {'IX': .2, 'SX': -.1, 'IY': .3, 'SY': .05, 'SXZ': 0, 'Z0': 0, 'C1': 0}
    P['nu'] = {k: 0.0 for k in IND}
    P['lam'] = {('X1', 'IX'): 1, ('X2', 'IX'): 1, ('X3', 'IX'): 1, ('X2', 'SX'): .6, ('X3', 'SX'): 1,
                ('Y1', 'IY'): 1, ('Y2', 'IY'): 1, ('Y3', 'IY'): 1, ('Y2', 'SY'): .5, ('Y3', 'SY'): 1, ('Z0', 'Z0'): 1, ('C1', 'C1'): 1}
    P['theta'] = {('X1', 'X1'): .3, ('X2', 'X2'): .25, ('X3', 'X3'): .35, ('Y1', 'Y1'): .4, ('Y2', 'Y2'): .3, ('Y3', 'Y3'): .45,
                  ('Y1', 'X1'): .05, ('Z0', 'Z0'): 0, ('C1', 'C1'): 0}
    P['psi'] = {('IX', 'IX'): .6, ('SX', 'SX'): .3, ('SX', 'IX'): .1, ('IY', 'IY'): .5, ('SY', 'SY'): .08, ('SY', 'IY'): -.02,
                ('SXZ', 'SXZ'): 0, ('Z0', 'Z0'): 1, ('C1', 'C1'): .25}
    P['beta'] = {('IY', 'IX'): -.35, ('SY', 'IX'): .1, ('SY', 'SX'): -.3, ('SY', 'IY'): .4, ('SY', 'SXZ'): .25,
                 ('IX', 'Z0'): .1, ('SX', 'Z0'): -.05, ('IY', 'Z0'): .2, ('SY', 'Z0'): .03,
                 ('IX', 'C1'): .3, ('SX', 'C1'): .1, ('IY', 'C1'): -.2, ('SY', 'C1'): .05}
    return P


def write_model(d, P, inp_extra='', product='sxz | sx XWITH z0;', gamma=False):
    d.mkdir(parents=True, exist_ok=True)
    (d / 'model.inp').write_text('TITLE: unit\nDATA: FILE = "data.dat";\nVARIABLE:\nNAMES = x1 x2 x3 y1 y2 y3 z0 c1;\n MISSING=.;\n'
                                 ' USEVARIABLES=x1-x3 y1-y3 z0 c1;\n' + inp_extra + 'ANALYSIS: TYPE=RANDOM;\nMODEL:\n' + product + '\n', encoding='utf-8')
    rows = [('NU', '1', k, P['nu'][k]) for k in IND] + [('ALPHA', '1', e, P['alpha'][e]) for e in ETA]
    rows += [('LAMBDA', r, c, P['lam'].get((r, c), 0.0)) for r in IND for c in ETA]
    rows += [('THETA', r, c, P['theta'].get((r, c), 0.0)) for i, r in enumerate(IND) for c in IND[:i + 1]]
    rows += [('PSI', r, c, P['psi'].get((r, c), 0.0)) for i, r in enumerate(ETA) for c in ETA[:i + 1]]
    rows += [('BETA', r, c, P['beta'].get((r, c), 0.0)) for r in ETA for c in ETA]
    if gamma:
        rows.append(('GAMMA', 'IX', 'C1', .1))
    with open(d / 'matrix_values.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['matrix', 'row', 'column', 'value']); w.writerows(rows)


def write_data(d, X):
    with open(d / 'data.dat', 'w', encoding='utf-8') as f:
        for r in X:
            f.write(' '.join('.' if (isinstance(v, float) and math.isnan(v)) else repr(float(v)) for v in r) + '\n')


def run_tool(d, extra=()):
    p = subprocess.run([sys.executable, '-I', str(tool), '--model-dir', str(d), '--data', str(d / 'data.dat'),
                        '--output', str(d / 'out.json'), *extra], capture_output=True, text=True)
    return p, (json.loads((d / 'out.json').read_text()) if p.returncode == 0 else None)


def mc_loglik(P, row, ndraw=400000):
    """原始结构方程逐步模拟；对测量误差解析积分。"""
    x = {'Z0': row[6], 'C1': row[7]}
    Pm = np.array([[P['psi'].get((a, b), P['psi'].get((b, a), 0.0)) for b in EN] for a in EN])
    z = rng.multivariate_normal(np.zeros(4), Pm, size=ndraw)
    B = P['beta']; A = P['alpha']
    ex = lambda f: sum(B.get((f, e), 0) * x[e] for e in EX)
    IX = A['IX'] + ex('IX') + z[:, 0]; SX = A['SX'] + ex('SX') + z[:, 1]; SXZ = SX * x['Z0']
    IY = A['IY'] + B[('IY', 'IX')] * IX + ex('IY') + z[:, 2]
    SY = A['SY'] + B[('SY', 'IX')] * IX + B[('SY', 'SX')] * SX + B[('SY', 'IY')] * IY + B[('SY', 'SXZ')] * SXZ + ex('SY') + z[:, 3]
    eta = {'IX': IX, 'SX': SX, 'IY': IY, 'SY': SY}
    ys = IND[:6]; obs = [i for i in range(6) if not math.isnan(row[i])]
    mu = np.stack([P['nu'][ys[i]] + sum(P['lam'].get((ys[i], f), 0) * eta[f] for f in EN) for i in obs], axis=1)
    T = np.array([[P['theta'].get((ys[i], ys[j]), P['theta'].get((ys[j], ys[i]), 0.0)) for j in obs] for i in obs])
    r = np.array([row[i] for i in obs])[None, :] - mu
    Ti = np.linalg.inv(T); _, ld = np.linalg.slogdet(T)
    lp = -0.5 * (len(obs) * math.log(2 * math.pi) + ld + np.einsum('ij,jk,ik->i', r, Ti, r))
    m = lp.max(); return m + math.log(np.mean(np.exp(lp - m)))


results = []
def check(name, ok, detail=''):
    results.append({'test': name, 'result': 'PASS' if ok else 'FAIL', 'detail': str(detail)[:300]})

P = base_params(); nan = float('nan')
people = [[.9, 1.1, 1.4, .2, .5, .9, -.48, 1.], [1.2, nan, 1.9, nan, .1, nan, 1.07, 0.], [-.3, .1, nan, .8, .6, .2, 8.76, 1.],
          [.0, .4, .7, nan, nan, -.5, -1.6, 0.], [nan, nan, nan, .3, .4, .6, 2.5, 1.]]
for i, row in enumerate(people):
    d = work / f'person{i}'; write_model(d, P); write_data(d, [row])
    p, out = run_tool(d)
    mc = mc_loglik(P, row)
    check(f'monte_carlo_person{i}', out is not None and abs(out['exact_LL'] - mc) < 0.02, (out and out['exact_LL'], round(mc, 4)))
# 全体：逐人之和 = 一次读入全部
d = work / 'all'; write_model(d, P); write_data(d, people); p, out = run_tool(d)
indiv = [json.loads((work / f'person{i}' / 'out.json').read_text())['exact_LL'] for i in range(len(people))]
check('sum_of_persons', out is not None and abs(out['exact_LL'] - sum(indiv)) < 1e-5 and out['n_used'] == 5 and out['missing_patterns'] == 5, out and out['missing_patterns'])
# z0 缺失或全部结局缺失的行被剔除（与 Mplus 条件于 x 的处理一致）
d = work / 'drop'; write_model(d, P); write_data(d, people + [[1, 1, 1, 1, 1, 1, nan, 1.], [nan] * 6 + [.5, 1.]]); p, out = run_tool(d)
check('drop_missing_x_and_empty_y', out is not None and out['n_used'] == 5 and out['n_dropped_no_outcome_or_missing_x'] == 2 and abs(out['exact_LL'] - sum(indiv)) < 1e-5)
# 拒收
Pn = base_params(); Pn['psi'][('SY', 'SY')] = -.05
d = work / 'neg'; write_model(d, Pn); write_data(d, people); p, out = run_tool(d)
check('reject_indefinite_psi', out is None and 'INADMISSIBLE' in (p.stdout + p.stderr), (p.stdout + p.stderr)[-120:])
p, out = run_tool(d, ['--diagnostic-allow-indefinite-latent'])
check('diagnostic_flag_marks_output', out is not None and out['diagnostic_only'] is True)
d = work / 'define'; write_model(d, P, inp_extra='DEFINE: zg = z0*c1;\n'); write_data(d, people); p, out = run_tool(d)
check('reject_define', out is None and 'UNSUPPORTED' in (p.stdout + p.stderr))
d = work / 'gamma'; write_model(d, P, gamma=True); write_data(d, people); p, out = run_tool(d)
check('reject_nonzero_gamma', out is None and 'UNSUPPORTED' in (p.stdout + p.stderr))
d = work / 'latlat'; write_model(d, P, product='sxz | sx XWITH ix;'); write_data(d, people); p, out = run_tool(d)
check('reject_latent_by_latent', out is None and 'UNSUPPORTED' in (p.stdout + p.stderr))
d = work / 'cols'; write_model(d, P); write_data(d, [r[:7] for r in people]); p, out = run_tool(d)
check('reject_column_mismatch', out is None and 'fields' in (p.stdout + p.stderr))

(work / 'exact_ll_unit_results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
for x in results:
    print(f"{x['test']:32s} {x['result']}  {x['detail']}")
print('EXACT_LL_UNIT', 'PASSED' if all(x['result'] == 'PASS' for x in results) else 'FAILED', len(results))
