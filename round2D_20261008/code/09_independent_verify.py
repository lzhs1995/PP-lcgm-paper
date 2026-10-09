"""独立重读原始 Mplus 输出；不调用 Mplus，不读取个人分析数据。

从 TECH1、RESULTS 和 TECH3 独立构造参数与几何，再核对 R 产物和
逐成员线性对比/Rubin 合并。中间运行只给 IN_PROGRESS 回执；终态才可 PASS。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t, chi2

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
MATRIX_NAMES = {"NU", "LAMBDA", "THETA", "ALPHA", "BETA", "PSI", "GAMMA", "TAU", "KAPPA"}
SYMMETRIC = {"THETA", "PSI"}
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[DEde][+-]?\d+)?"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def frame(path, index_col=None):
    return pd.read_csv(path, encoding="utf-8-sig", index_col=index_col)


def close(actual, expected, context, atol=1e-9, rtol=1e-8):
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if a.shape != b.shape or not np.allclose(a, b, atol=atol, rtol=rtol, equal_nan=True):
        diff = float(np.nanmax(np.abs(a-b))) if a.shape == b.shape and a.size else None
        raise AssertionError(f"{context}: shape {a.shape}/{b.shape}, max difference {diff}")


def as_float(text):
    return float(text.replace("D", "E").replace("d", "e"))


def matrix_cells(lines, integer):
    """按带下划线表头的矩阵块读入，不依赖 R 的矩阵顺序。"""
    cells = {}
    i = 0
    while i + 2 < len(lines):
        name = lines[i].strip()
        if name not in MATRIX_NAMES or not re.fullmatch(r"[ _]+", lines[i+2]) or "_" not in lines[i+2]:
            i += 1
            continue
        columns = lines[i+1].split()
        i += 3
        while i < len(lines) and lines[i].strip():
            tokens = lines[i].split()
            if name in {"NU", "ALPHA", "TAU", "KAPPA"} and re.fullmatch(NUMBER, tokens[0]):
                row, vals = "1", tokens
            else:
                row, vals = tokens[0], tokens[1:]
            assert len(vals) <= len(columns), (name, row)
            for col, value in zip(columns, vals):
                key = name, row, col
                assert key not in cells, f"duplicate TECH1 cell {key}"
                cells[key] = int(value) if integer else as_float(value)
            i += 1
    assert cells, "empty TECH1 section"
    return cells


class RawModel:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.lines = (self.directory / "model.out").read_text(encoding="latin1").splitlines()
        trimmed = [s.strip() for s in self.lines]
        a = trimmed.index("PARAMETER SPECIFICATION")
        b = trimmed.index("STARTING VALUES", a)
        c = next(i for i in range(b+1, len(self.lines)) if re.match(r"^(TECHNICAL \d+ OUTPUT|RESULTS SAVING INFORMATION|SAVEDATA INFORMATION)", self.lines[i]))
        self.spec = matrix_cells(self.lines[a+1:b], True)
        self.values = matrix_cells(self.lines[b+1:c], False)
        ids = sorted(set(v for v in self.spec.values() if v > 0))
        self.p = max(ids)
        assert ids == list(range(1, self.p+1)), "non-contiguous free parameter numbering"
        saved = np.array([as_float(x) for x in (self.directory / "estimates.dat").read_text().split()])
        packed = np.array([as_float(x) for x in (self.directory / "tech3.dat").read_text().split()])
        assert len(saved) >= 2*self.p and len(packed) == self.p*(self.p+1)//2
        self.q, self.se = saved[:self.p], saved[self.p:2*self.p]
        self.v = np.zeros((self.p, self.p))
        # TECH3 文件按下三角逐行保存；此处直接按行展开。
        at = 0
        for i in range(self.p):
            self.v[i, :i+1] = packed[at:at+i+1]
            self.v[:i+1, i] = packed[at:at+i+1]
            at += i+1
        first = {}
        for key, number in self.spec.items():
            if number:
                assert key in self.values, f"free cell absent in STARTING VALUES: {key}"
                self.values[key] = self.q[number-1]
                first.setdefault(number, key)
        self.parameters = pd.DataFrame([
            dict(parameter=i, matrix=first[i][0].lower(), row=first[i][1], column=first[i][2],
                 estimate=self.q[i-1], se=self.se[i-1]) for i in ids
        ])
        a = trimmed.index("Order of data")
        b = trimmed.index("Save file", a)
        labels = [s for s in trimmed[a+1:b] if s and not s.startswith(("(saved", "Parameter estimates", "Standard errors"))]
        extras = saved[2*self.p:]
        assert len(labels) == len(extras), "RESULTS extra statistics count mismatch"
        self.extra = dict(zip(labels, extras))
        close([self.extra["Number of Free Parameters"]], [self.p], "free parameter count")

    def lookup(self, matrix, row, column, number=False):
        source = self.spec if number else self.values
        key = matrix, row, column
        if key in source:
            return source[key]
        if matrix in SYMMETRIC:
            return source.get((matrix, column, row), 0)
        return 0

    def block(self, matrix, rows, columns):
        return np.array([[self.lookup(matrix, row, column) for column in columns] for row in rows], dtype=float)


def canonical_measurement(raw, factors, observations):
    th = raw.block("THETA", observations, observations)
    lam = raw.block("LAMBDA", observations, factors)
    promoted = [o for o in observations if raw.lookup("PSI", o, o, number=True) > 0]
    if promoted:
        proxy_loadings = raw.block("LAMBDA", observations, promoted)
        assert np.count_nonzero(raw.block("PSI", promoted, factors)) == 0
        assert np.count_nonzero(raw.block("BETA", promoted, promoted)) == 0
        lam += proxy_loadings @ raw.block("BETA", promoted, factors)
        th += proxy_loadings @ raw.block("PSI", promoted, promoted) @ proxy_loadings.T
    return th, lam, promoted


def geometry(raw, kind, specification):
    latent = specification in {"D0", "D1"}
    fac = ["IX", "SX", "IZ", "SZ", "IY", "SY"] if latent else ["IX", "SX", "IY", "SY"]
    obs = [f"{v}{k}" for v in ("XYZ" if latent else "XY") for k in range(1, 6)]
    # 生产程序使用 X,Y,Z 的顺序；此处按名称核对全部导出的矩阵。
    B = raw.block("BETA", fac, fac)
    P = raw.block("PSI", fac, fac)
    T, L, promoted = canonical_measurement(raw, fac, obs)
    mats = {"PSI": (P, fac, fac), "THETA": (T, obs, obs), "LAMBDA": (L, obs, fac)}
    checks = {"PSI": P, "THETA": T}
    if kind == "linear":
        A = np.linalg.inv(np.eye(len(fac))-B)
        G = A @ P @ A.T
        S = L @ G @ L.T + T
        mats.update(B=(B, fac, fac), G=(G, fac, fac), SIGMA=(S, obs, obs))
        checks.update(G=G, SIGMA=S)
    elif kind == "lms_latent":
        A = np.linalg.inv(np.eye(len(fac))-B)
        G = A @ P @ A.T
        mu = A @ np.array([raw.lookup("ALPHA", "1", f) for f in fac])
        ia, ib, iy = fac.index("SX"), fac.index("IZ"), fac.index("SY")
        delta = raw.lookup("BETA", "SY", "SXIZ")
        # 联合正态基础增长变量的精确乘积矩，包括非零均值项。
        cov_product = mu[ia]*G[:, ib] + mu[ib]*G[:, ia]
        var_product = (G[ia, ia]*G[ib, ib] + G[ia, ib]**2 +
                       mu[ia]**2*G[ib, ib] + mu[ib]**2*G[ia, ia] +
                       2*mu[ia]*mu[ib]*G[ia, ib])
        q = G.copy()
        q[:, iy] += delta*cov_product
        q[iy, :] += delta*cov_product
        q[iy, iy] += delta**2*var_product
        S = L @ q @ L.T + T
        mats.update(B_without_product=(B, fac, fac), NONLINEAR_COV_C0=(q, fac, fac), NONLINEAR_SIGMA_C0=(S, obs, obs))
        checks.update(NONLINEAR_COV_C0=q, NONLINEAR_SIGMA_C0=S)
    else:
        mats["B_without_product"] = B, fac, fac
        for z in (-1, 0, 1):
            for g in (0, 1):
                bc = B.copy()
                bc[fac.index("SY"), fac.index("SX")] += (
                    raw.lookup("BETA", "SY", "SXZ")*z +
                    raw.lookup("BETA", "SY", "SXG")*g +
                    raw.lookup("BETA", "SY", "SXZG")*z*g)
                A = np.linalg.inv(np.eye(len(fac))-bc)
                S = L @ A @ P @ A.T @ L.T + T
                key = f"CONDITIONAL_Z{z}_G{g}"
                mats[key] = S, obs, obs
                checks[key] = S
    return mats, checks, promoted


def matrix_check(a, expected_rank=None):
    close(a, a.T, "symmetric covariance", atol=1e-8)
    assert np.isfinite(a).all()
    scale = np.sqrt(np.abs(np.diag(a)))
    scale[scale < 1e-10] = 1
    e = np.linalg.eigvalsh(a/np.outer(scale, scale))
    expected_rank = len(a) if expected_rank is None else expected_rank
    return dict(min_eigen=float(e.min()), rank=int(np.sum(e > 1e-7)), expected_rank=expected_rank,
                psd=bool(e.min() >= -1e-7), rank_ok=bool(np.sum(e > 1e-7) == expected_rank),
                positive_definite=bool(e.min() > 1e-7))


def printed_rows(lines):
    start = next(i for i, line in enumerate(lines) if line.strip() == "MODEL RESULTS")
    end = next(i for i in range(start+1, len(lines)) if re.match(r"^(QUALITY OF NUMERICAL|STANDARDIZED MODEL|R-SQUARE|CONFIDENCE INTERVALS|MODEL COMMAND|TECHNICAL \d+)", lines[i]))
    output, header = [], None
    for line in lines[start+1:end]:
        s = line.strip()
        head = re.fullmatch(r"([A-Z0-9_]+)\s+(ON|WITH|BY|\|)", s)
        if head:
            header = ".".join(head.groups())
            continue
        if s in {"Means", "Intercepts", "Variances", "Residual Variances", "Thresholds"}:
            header = s.replace(" ", ".")
            continue
        row = re.fullmatch(r"([A-Z0-9_.$]+)\s+("+NUMBER+r")\s+("+NUMBER+r")\s+("+NUMBER+r")\s+("+NUMBER+r")", s)
        if row:
            assert header, s
            key, *vals = row.groups()
            output.append(dict(paramHeader=header, param=key, **dict(zip(["est", "se", "est_se", "pval"], map(as_float, vals)))))
    return pd.DataFrame(output)


def verify_model(directory):
    receipt = read_json(directory / "receipt.json")
    inp = read_json(directory / "input_contract.json")
    assert receipt["id"] == inp["id"]
    assert sha(directory / "model.inp") == inp["input_sha256"]
    assert sha(directory / "model.out") == receipt["output_sha256"]
    out = (directory / "model.out").read_text(encoding="latin1")
    normal = "THE MODEL ESTIMATION TERMINATED NORMALLY" in out
    assert normal == receipt["normal"]
    rec = dict(id=receipt["id"], category=receipt["category"], status=receipt["status"], usable=receipt["usable"],
               output_sha256=receipt["output_sha256"], printed_rows=0, free_parameters=0, matrices=0, verified=True)
    if not normal:
        assert not receipt["usable"]
        return rec, None
    raw = RawModel(directory)
    hp = frame(directory / "parameters_high_precision.csv")
    assert hp[["parameter", "matrix", "row", "column"]].equals(raw.parameters[["parameter", "matrix", "row", "column"]])
    close(hp[["estimate", "se"]], raw.parameters[["estimate", "se"]], "high precision parameters")
    close(frame(directory / "parameter_covariance.csv", index_col=0), raw.v, "TECH3 export", atol=1e-12)
    close(np.diag(raw.v), raw.se**2, "SE squared vs TECH3", atol=1e-6, rtol=1e-5)
    pr = printed_rows(raw.lines)
    rp = frame(directory / "parameters.csv")
    assert pr[["paramHeader", "param"]].equals(rp[["paramHeader", "param"]]), "printed parameter names or order mismatch"
    close(pr[["est", "se", "est_se", "pval"]], rp[["est", "se", "est_se", "pval"]], "printed parameter CSV", atol=1e-12)
    # 同时核对打印值与高精度值，不把三位打印输出当作原精度。
    for _, row in frame(directory / "key_paths.csv").iterrows():
        number = raw.lookup("BETA", row["row"], row["column"], number=True)
        assert number == int(row["parameter"]) and number > 0
        close([row["estimate"], row["se"]], [raw.q[number-1], raw.se[number-1]], "key paths")
    mats, checks, promoted = geometry(raw, receipt["kind"], receipt["spec"])
    for name, (m, rows, cols) in mats.items():
        export = frame(directory/f"matrix_{name}.csv", index_col=0)
        named = list(export.index) == rows and list(export.columns) == cols
        # 早期 D0 的 LAMBDA 导出仅含 R 默认索引；其顺序由冻结规格与 TECH1 双重绑定。
        default = list(export.index.astype(str)) == [str(i+1) for i in range(len(rows))] and list(export.columns) == [f"V{i+1}" for i in range(len(cols))]
        assert named or default, f"matrix labels {name}"
        close(export, m, f"geometry matrix {name}", atol=1e-8)
    geo = read_json(directory / "geometry.json")
    own_checks = {name: matrix_check(m) for name, m in checks.items()}
    assert set(own_checks) == set(geo["checks"])
    for name, check in own_checks.items():
        for key in ["rank", "expected_rank", "psd", "rank_ok", "positive_definite"]:
            assert check[key] == geo["checks"][name][key], (name, key)
        close([check["min_eigen"]], [geo["checks"][name]["min_eigen"]], f"eigenvalue {name}", atol=1e-8)
    geo_pass = all(v["psd"] and v["rank_ok"] for v in own_checks.values()) and own_checks["THETA"]["positive_definite"]
    if receipt["kind"] == "linear":
        geo_pass = geo_pass and own_checks["SIGMA"]["positive_definite"]
    assert geo_pass == geo["passed"] == receipt["geometry_ok"]
    neg = hp[(hp["matrix"].isin(["psi", "theta"])) & (hp["row"] == hp["column"]) & (hp["estimate"] < 0)]
    sd = np.sqrt(np.diag(raw.v))
    vc_eig = np.linalg.eigvalsh(raw.v/np.outer(sd, sd))
    vc_ok = np.isfinite(raw.v).all() and np.isfinite(raw.se).all() and np.all(raw.se > 0) and vc_eig.min() > 1e-10
    assert bool(vc_ok) == receipt["vcov_ok"]
    flat = re.sub(r"\s+", " ", out)
    fatal = re.search(r"SADDLE POINT|STANDARD ERRORS OF THE MODEL PARAMETER ESTIMATES COULD NOT BE COMPUTED|MODEL MAY NOT BE IDENTIFIED|NON-POSITIVE DEFINITE FIRST-ORDER DERIVATIVE|NOT TRUSTWORTHY|DID NOT CONVERGE|NO CONVERGENCE", flat)
    cov_warning = re.search(r"LATENT VARIABLE COVARIANCE MATRIX \(PSI\) IS NOT POSITIVE|RESIDUAL COVARIANCE MATRIX \(THETA\) IS NOT POSITIVE", flat)
    usable = normal and not fatal and not cov_warning and len(neg) == 0 and vc_ok and geo_pass
    assert bool(usable) == receipt["usable"], "independent model adoption mismatch"
    close([receipt["LL"]], [raw.extra["H0 Loglikelihood"]], "saved log likelihood")
    rec.update(printed_rows=len(pr), free_parameters=raw.p, matrices=len(mats), promoted=promoted)
    return rec, raw


def rubin(Q, U, level=.95):
    q = np.asarray(Q, float)
    if q.ndim == 1:
        q = q[:, None]
    u = np.asarray(U, float)
    assert q.shape[0] == 10 and u.shape == (10, q.shape[1], q.shape[1])
    W, B = u.mean(axis=0), np.atleast_2d(np.cov(q, rowvar=False, ddof=1))
    T = W + 1.1*B
    est, se = q.mean(axis=0), np.sqrt(np.diag(T))
    lam = 1.1*np.diag(B)/np.diag(T)
    r = 1.1*np.diag(B)/np.diag(W)
    with np.errstate(divide="ignore"):
        df = np.where(r > 0, 9*(1+1/r)**2, np.inf)
    crit = student_t.ppf(1-(1-level)/2, df)
    table = pd.DataFrame(dict(estimate=est, se=se, df=df, lower=est-crit*se, upper=est+crit*se,
        p=2*student_t.sf(np.abs(est/se), df), **{"lambda":lam}, MCSE_over_SE=np.sqrt(np.diag(B)/10)/se))
    return table, W, B, T


def numeric_check(a, b, mode):
    ra, rb = read_json(a/"receipt.json"), read_json(b/"receipt.json")
    if not ra["usable"] or not rb["usable"]:
        return False
    ka, kb = frame(a/"key_paths.csv").set_index("label"), frame(b/"key_paths.csv").set_index("label")
    assert set(ka.index) == set(kb.index)
    kb = kb.loc[ka.index]
    d = np.abs(ka.estimate-kb.estimate)
    threshold = np.maximum(.001, .01*kb.se) if mode == "start" else .05*kb.se
    passed = bool((d <= threshold).all() and (np.abs(ka.se-kb.se)/kb.se <= .05).all())
    if mode == "start":
        passed = passed and abs(ra["LL"]-rb["LL"]) <= .01
    return passed


def holm_fixed_family(p, family_size):
    """保留未估计项目为缺失；计算时仍使用预登记家族大小。"""
    p = np.asarray(p, float)
    valid = np.flatnonzero(np.isfinite(p))
    assert len(valid) <= family_size and np.all((p[valid] >= 0) & (p[valid] <= 1))
    adjusted = np.full(p.shape, np.nan)
    if len(valid):
        order = valid[np.argsort(p[valid], kind="stable")]
        adjusted[order] = np.minimum(1, np.maximum.accumulate(p[order]*(family_size-np.arange(len(order)))))
    return adjusted


def h4_magnitude_decision(q):
    """只依据同时区间判断两组同向且幅度差异已识别；不比较两个星号。"""
    if len(q) != 3:
        return "NOT_ESTIMABLE"
    q = q.set_index("contrast")
    assert set(q.index) == {"delta_low", "delta_high", "difference"}
    lower, upper = q.simultaneous_lower, q.simultaneous_upper
    positive = min(lower["delta_low"], lower["delta_high"]) > 0
    negative = max(upper["delta_low"], upper["delta_high"]) < 0
    difference_up = lower["difference"] > 0
    difference_down = upper["difference"] < 0
    if (positive and difference_up) or (negative and difference_down):
        return "MORE_SENSITIVE_IN_RESOURCE_ONE"
    if (positive and difference_down) or (negative and difference_up):
        return "LESS_SENSITIVE_IN_RESOURCE_ONE"
    return "MAGNITUDE_DIRECTION_UNDETERMINED"


def verify_summary_decisions(root):
    if not (root/"results/SUMMARY.json").exists():
        return 0
    results = root/"results"
    contract = read_json(root/"RUN_CONTRACT.json")
    pooled, h4 = frame(results/"pooled_paths.csv"), frame(results/"H4_contrasts.csv")
    checks = 0
    if len(pooled):
        expected = np.full(len(pooled), np.nan)
        for spec in ("D1", "E1"):
            select = (pooled.spec == spec) & (pooled.label == "dc")
            assert not pooled.loc[select, "z"].duplicated().any()
            expected[select] = holm_fixed_family(pooled.loc[select, "p"], 4)
            checks += int(select.sum())
        actual = pooled.p_holm.to_numpy(float)
        assert np.array_equal(np.isnan(actual), np.isnan(expected)), "Missing tests must remain missing"
        close(actual[np.isfinite(expected)], expected[np.isfinite(expected)], "Holm four-target family")
    if len(h4):
        select = h4.contrast == "difference"
        assert not h4.loc[select, "resource"].duplicated().any()
        expected = np.full(len(h4), np.nan)
        expected[select] = holm_fixed_family(h4.loc[select, "p"], 3)
        actual = h4.p_holm_difference.to_numpy(float)
        assert np.array_equal(np.isnan(actual), np.isnan(expected))
        close(actual[np.isfinite(expected)], expected[np.isfinite(expected)], "Holm three-resource family")
        checks += int(select.sum())
    decisions = frame(results/"H4_direction_decisions.csv").set_index("resource")
    assert set(decisions.index) == {"EDU", "URBAN", "INC"}
    for resource in decisions.index:
        q = h4[h4.resource == resource] if len(h4) else h4
        assert decisions.loc[resource, "judgment"] == h4_magnitude_decision(q), resource
        assert decisions.loc[resource, "meaning"] == contract["group_one_meanings"][resource]
        checks += 1
    slopes = frame(results/"conditional_slopes.csv")
    descriptions = frame(root/"audit/moderator_descriptives.csv")
    descriptions = descriptions[descriptions.year == 2012].set_index("z")
    for row in slopes.itertuples():
        support = descriptions.loc[row.z]
        close([row.observed2012_min, row.observed2012_max], [support["min"], support["max"]], "Z reference support")
        status = ("LATENT_GAUSSIAN_REFERENCE" if row.spec == "D1" else
                  "EXTRAPOLATION_OUTSIDE_OBSERVED_SUPPORT" if row.reference_z < support["min"] or row.reference_z > support["max"] else
                  "WITHIN_OBSERVED_RANGE")
        assert row.support_status == status
        assert row.reference_scale == ("latent_IZ" if row.spec == "D1" else "observed2012_Z0")
        checks += 1
    statuses = frame(results/"family_status.csv")
    assert len(statuses) == 19 and not statuses.duplicated(["z", "spec"]).any()
    for row in statuses.itertuples():
        file = results/f"{row.z}_{row.spec}_family.json"
        if row.status == "NOT_RUN_NOT_TRIGGERED":
            assert row.z != "SD" and row.spec in ("E0", "E1") and not file.exists()
            assert read_json(results/f"{row.z}_D1_family.json")["eligible"]
        elif row.status == "CONDITIONAL_MI_REPORTABLE":
            assert file.exists() and read_json(file)["eligible"]
        elif row.status == "NOT_POOLABLE":
            assert file.exists() and not read_json(file)["eligible"]
        else:
            assert not file.exists() and not bool(row.eligible)
            terminal = read_json(root/"runtime/queue_terminal.json")
            reason = terminal.get("reason", "COMPLETED_REGISTERED_QUEUE")
            assert ("BUDGET" in row.status and "BUDGET" in reason) or ("RESOURCE_LIMIT" in row.status and reason == "RESOURCE_WAIT_LIMIT")
        checks += 1
    return checks


def verify_families(root, raw_models):
    results = root/"results"
    summary_exists = (results/"SUMMARY.json").exists()
    pooled = frame(results/"pooled_paths.csv") if summary_exists else None
    slopes = frame(results/"conditional_slopes.csv") if summary_exists else None
    h4 = frame(results/"H4_contrasts.csv") if summary_exists else None
    rows, pooled_checks = [], 0
    for path in sorted(results.glob("*_family.json")):
        family = read_json(path)
        z, sp = family["z"], family["spec"]
        dirs = []
        members = family["members"]
        assert len(members) == 10 and [m["member"] for m in members] == list(range(1, 11))
        for member in members:
            if member["status"] == "NOT_RUN":
                dirs.append(None)
                continue
            directory = root/"models"/z/f"{sp}_Z0_MI{member['member']:02d}"/member["attempt"]
            receipt = read_json(directory/"receipt.json")
            assert receipt["usable"] == member["usable"] and receipt["output_sha256"] == member["output_sha256"]
            dirs.append(directory)
        can_pool = all(d is not None and read_json(d/"receipt.json")["usable"] for d in dirs)
        if can_pool and sp not in {"D0", "E0"}:
            numeric = family["numeric"]
            assert numeric["adopted_MI01_attempt"] == members[0]["attempt"]
            for mode in ("start", "integration"):
                check = numeric[mode]
                parent = dirs[0].parent
                actual = numeric_check(parent/check["reference_attempt"], parent/check["candidate_attempt"], mode)
                assert actual == check["passed"]
                can_pool = can_pool and actual
            assert numeric["start"]["reference_attempt"] == members[0]["attempt"]
            assert numeric["integration"]["candidate_attempt"] == members[0]["attempt"]
        assert can_pool == family["eligible"], (z, sp, "family gate mismatch")
        rows.append(dict(z=z, spec=sp, eligible=can_pool, member_count=sum(d is not None for d in dirs)))
        if not can_pool or not summary_exists:
            continue
        labs = list(frame(dirs[0]/"key_paths.csv").label)
        qs, us = [], []
        for d in dirs:
            raw = raw_models[str(d)]
            keys = frame(d/"key_paths.csv").set_index("label").loc[labs]
            ids = keys.parameter.to_numpy(int)-1
            qs.append(raw.q[ids]); us.append(raw.v[np.ix_(ids, ids)])
        Q, U = np.asarray(qs), np.asarray(us)
        table, W, B, T = rubin(Q, U)
        target = pooled[(pooled.z == z) & (pooled.spec == sp)].set_index("label").loc[labs]
        close(target[list(table)], table, f"Rubin {z} {sp}", atol=1e-7)
        for name, a in (("W", W), ("B", B), ("T", T)):
            output = frame(results/f"{z}_{sp}_pooled_{name}.csv", index_col=0)
            assert list(output.index) == labs == list(output.columns)
            close(output, a, f"Rubin matrix {z} {sp} {name}")
        contrasts = []
        if sp in {"D1", "E1"}:
            for value in (-1, 0, 1):
                a = np.zeros(len(labs)); a[labs.index("bss")] = 1; a[labs.index("dc")] = value
                target = slopes[(slopes.z == z) & (slopes.spec == sp) & (slopes.reference_z == value)]
                contrasts.append((a, target))
        elif sp.startswith("H4_"):
            for name in ("delta_low", "delta_high", "difference"):
                a = np.zeros(len(labs))
                if name != "difference": a[labs.index("dc")] = 1
                if name != "delta_low": a[labs.index("dcg")] = 1
                target = h4[(h4.resource == sp[3:]) & (h4.contrast == name)]
                contrasts.append((a, target))
        for a, target in contrasts:
            q = Q @ a
            u = np.einsum("i,kij,j->k", a, U, a).reshape(10, 1, 1)
            result, _, _, total = rubin(q, u)
            close(target[list(result)], result, f"fixed contrast {z} {sp}", atol=1e-7)
            close([total[0,0]], [a@T@a], "contrast covariance cross-check")
            if sp.startswith("H4_"):
                crit = student_t.ppf(1-.05/18, result.df.iloc[0])
                es, se = result.estimate.iloc[0], result.se.iloc[0]
                close(target[["simultaneous_lower", "simultaneous_upper"]], [[es-crit*se, es+crit*se]], "H4 simultaneous CI")
            pooled_checks += 1
        pooled_checks += len(labs)
    return rows, pooled_checks


def verify_sw_structure(root):
    source = root/"provenance_SW"
    if not (root/"results/SW_structure_receipt.json").exists():
        return 0
    for _, entry in frame(source/"source_manifest.csv").iterrows():
        path = source/entry.relative_file
        assert path.stat().st_size == entry.bytes and sha(path) == entry.source_sha256
    labels = ([f"X_loading_{yr}" for yr in (2016, 2018, 2020)] +
              [f"XY_residual_cov_{yr}" for yr in (2012, 2016, 2018, 2020, 2022)] +
              [f"XY_residual_cor_{yr}" for yr in (2012, 2016, 2018, 2020, 2022)] +
              [f"growth_residual_var_{f}" for f in ("IX", "SX", "IY", "SY")])
    Q, U = [], []
    members = frame(root/"results/SW_structure_members.csv")
    for k in range(1, 11):
        raw = RawModel(source/"models"/f"SW_MI{k:02d}")
        q, jacobian = np.zeros(17), np.zeros((17, raw.p))
        def parameter(mat, row, col):
            i = raw.lookup(mat, row, col, number=True)-1
            assert i >= 0
            return i
        for at, wave in enumerate((2, 3, 4)):
            i = parameter("LAMBDA", f"X{wave}", "SX")
            q[at], jacobian[at, i] = raw.q[i], 1
        for wave in range(1, 6):
            ids = [parameter("THETA", f"X{wave}", f"Y{wave}"),
                   parameter("THETA", f"X{wave}", f"X{wave}"),
                   parameter("THETA", f"Y{wave}", f"Y{wave}")]
            c, vx, vy = raw.q[ids]
            cov_at, corr_at = wave+2, wave+7
            q[cov_at], jacobian[cov_at, ids[0]] = c, 1
            q[corr_at] = c/math.sqrt(vx*vy)
            jacobian[corr_at, ids] = [1/math.sqrt(vx*vy), -q[corr_at]/(2*vx), -q[corr_at]/(2*vy)]
        for at, f in enumerate(("IX", "SX", "IY", "SY"), start=13):
            i = parameter("PSI", f, f)
            q[at], jacobian[at, i] = raw.q[i], 1
        u = jacobian @ raw.v @ jacobian.T
        target = members[members.member == k].set_index("label").loc[labels]
        close(target.estimate, q, "SW structure member estimates")
        close(target.se, np.sqrt(np.diag(u)), "SW structure delta-method SE")
        Q.append(q); U.append(u)
    results, W, B, T = rubin(Q, U)
    target = frame(root/"results/SW_structure_pooled.csv").set_index("label").loc[labels]
    close(target[list(results)], results, "SW structure Rubin", atol=1e-7)
    for name, m in (("W", W), ("B", B), ("T", T)):
        exported = frame(root/f"results/SW_structure_{name}.csv", index_col=0)
        assert list(exported.index) == labels == list(exported.columns)
        close(exported, m, f"SW structure {name}")
    return 17


def verify_reporting_context(root):
    """只用公开副本复核稿件新增的旧父模型、MI链和单变量形状证据。"""
    path = root/"audit/reporting_support.json"
    if not path.exists():
        return {}
    support = read_json(path)
    assert support["status"] == "PASS" and support["new_model_calls"] == 0
    parent = frame(root/"audit/parent_history_SY.csv")
    assert len(parent) == 10 and set(parent.model) == {f"PARENT_MI{k:02d}" for k in range(1,11)}
    for _, row in parent.iterrows():
        source = root/row.copied_evidence
        assert sha(source) == row.source_sha256
        values = frame(source)
        selected = values[(values.matrix == "psi") & (values["row"] == "SY") & (values["column"] == "SY")]
        assert len(selected) == 1 and selected.parameter.iloc[0] == row.parameter
        close(selected[["estimate","se"]].iloc[0], [row.sy_residual,row.se], "historical parent SY binding")
        assert np.isfinite(row.sy_residual) and np.isfinite(row.se) and row.sy_residual < 0 and row.se > 0
    close([parent.sy_residual.min(),parent.sy_residual.max()],
          [support["sy_residual_min"],support["sy_residual_max"]], "historical SY range")
    protocol_file = root/"audit/MI_source_snapshot/mi_protocol.json"
    convergence_file = root/"audit/MI_source_snapshot/mi_convergence.csv"
    assert sha(protocol_file) == support["protocol_sha256"] and sha(convergence_file) == support["convergence_sha256"]
    protocol = read_json(protocol_file)
    targets = [name for name,method in protocol["methods"].items() if method]
    convergence = frame(convergence_file)
    terminal = convergence[(convergence[".it"] == protocol["maxit"]) & convergence.vrb.isin(targets)].set_index("vrb").loc[targets]
    reported = frame(root/"audit/MI_terminal_chain_summary.csv").set_index("variable").loc[targets]
    assert len(terminal) == len(reported) == len(targets) == 10
    assert np.isfinite(terminal[["ac","psrf"]]).all().all()
    close(reported[["ac","psrf"]],terminal[["ac","psrf"]],"MI terminal chain target summary")
    close(reported.iteration,terminal[".it"],"MI terminal iteration")
    close([terminal.psrf.min(),terminal.psrf.max()],[support["psrf_min"],support["psrf_max"]],"MI PSRF range")
    binding = read_json(root/"audit/univariate_shape_binding.json")
    for row in binding["sources"]:
        assert sha(root/row["evidence"]) == row["source_sha256"]
    summary = frame(root/"audit/univariate_shape_summary.csv").set_index("shape")
    assert set(summary.index) == {"free","linear"} and len(summary) == 2
    fit_fields = ["Parameters","ChiSqM_Value","ChiSqM_DF","LL","LLCorrectionFactor","AIC","BIC"]
    printed_count = 0
    for shape in ("free","linear"):
        directory = root/"audit/univariate_shape_history"/("D3274_U0_"+shape)
        output = (directory/"model.out").read_text(encoding="latin1")
        assert "THE MODEL ESTIMATION TERMINATED NORMALLY" in output
        pr = printed_rows(output.splitlines())
        rp = frame(directory/"parameters.csv")
        assert pr[["paramHeader","param"]].equals(rp[["paramHeader","param"]])
        close(rp[["est","se","est_se","pval"]],pr[["est","se","est_se","pval"]],"old univariate printed parameters",atol=1e-12)
        means = pr[(pr.paramHeader == "Means") & (pr.param == "SY")]
        assert len(means) == 1
        q = means.iloc[0]
        close(summary.loc[shape,["sy_mean_0_10","sy_se_0_10","p_printed"]],q[["est","se","pval"]],"old univariate SY mean")
        close(summary.loc[shape,["sy_mean_0_1","sy_se_0_1"]],np.asarray(q[["est","se"]],float)*10,"0/10 to 0/1 scale")
        fit = frame(directory/"fit.csv").iloc[0]
        close(summary.loc[shape,fit_fields],fit[fit_fields],"old univariate fit table")
        assert int(fit.Observations) == int(summary.loc[shape,"N"]) == 3274
        inp = (directory/"model.inp").read_text(encoding="utf-8-sig")
        assert "CLUSTER=fid" in inp and "y5@10" in inp
        printed_count += len(pr)
    unrestricted, restricted = summary.loc["free"],summary.loc["linear"]
    df = unrestricted.Parameters-restricted.Parameters
    correction = (unrestricted.Parameters*unrestricted.LLCorrectionFactor-restricted.Parameters*restricted.LLCorrectionFactor)/df
    statistic = 2*(unrestricted.LL-restricted.LL)/correction
    close([df,correction,statistic,chi2.sf(statistic,df)],
          [binding["df"],binding["correction"],binding["statistic"],binding["p"]],"old clustered shape comparison")
    return dict(historical_parent_SY_members=10,MI_terminal_targets=10,old_univariate_models=2,
                old_univariate_printed_rows=printed_count,new_model_calls=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--require-terminal", action="store_true")
    parser.add_argument("--evidence-output", type=Path, help="Write the independent receipt here to preserve an unpacked evidence snapshot")
    args = parser.parse_args()
    root = args.root
    dest = args.evidence_output if args.evidence_output is not None else root/"evidence"
    dest.mkdir(exist_ok=True, parents=True)
    terminal = (root/"runtime/queue_terminal.json").exists()
    if args.require_terminal:
        assert terminal and (root/"results/SUMMARY.json").exists(), "queue or pooling incomplete"
    records, raw_models, errors = [], {}, []
    for path in sorted((root/"models").glob("*/*/*/receipt.json")):
        try:
            rec, raw = verify_model(path.parent)
            records.append(rec)
            if raw is not None:
                raw_models[str(path.parent)] = raw
        except Exception as exc:
            errors.append(dict(file=str(path.relative_to(root)), error=f"{type(exc).__name__}: {exc}"))
    family_rows, pooled_checks, sw_checks, reporting_checks, context_checks = [], 0, 0, 0, {}
    if not errors:
        try:
            family_rows, pooled_checks = verify_families(root, raw_models)
            sw_checks = verify_sw_structure(root)
            reporting_checks = verify_summary_decisions(root)
            context_checks = verify_reporting_context(root)
        except Exception as exc:
            errors.append(dict(file="results/", error=f"{type(exc).__name__}: {exc}"))
    registered = frame(root/"audit/CALL_REGISTER.csv")
    completed = {r["id"] for r in records}
    incomplete = [s for s in registered.id if s not in completed]
    if terminal and incomplete:
        errors.append(dict(file="audit/CALL_REGISTER.csv", error=f"registered calls without verified receipt: {incomplete}"))
    status = "FAIL" if errors else "PASS" if terminal and (root/"results/SUMMARY.json").exists() else "IN_PROGRESS"
    report = dict(status=status, verified_at=datetime.now(timezone.utc).isoformat(),
        scope="Independent raw-output arithmetic audit; not independent refitting of CFPS microdata",
        model_count=len(records), synthetic_models=sum(r["category"] == "SYNTHETIC" for r in records),
        printed_parameter_rows=sum(r["printed_rows"] for r in records),
        high_precision_parameters=sum(r["free_parameters"] for r in records),
        rebuilt_matrices=sum(r["matrices"] for r in records), pooled_path_or_contrast_checks=pooled_checks,
        existing_SW_structure_checks=sw_checks,
        multiplicity_direction_and_status_checks=reporting_checks,
        historical_reporting_context_checks=context_checks,
        unfinished_calls=incomplete, family_checks=family_rows, errors=errors,
        script_sha256=sha(__file__), contract_sha256=sha(root/"RUN_CONTRACT.json"))
    write_json(dest/"independent_verification.json", report)
    if records:
        pd.DataFrame(records).to_csv(dest/"independent_model_verification.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
