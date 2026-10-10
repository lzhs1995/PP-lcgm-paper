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
