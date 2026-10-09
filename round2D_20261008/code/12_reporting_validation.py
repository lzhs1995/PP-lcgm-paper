"""汇总规则的独立数值验证，不用合成成功冒充真实分析已完成。"""
from pathlib import Path
import importlib.util
import json
import numpy as np
import pandas as pd

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
spec = importlib.util.spec_from_file_location("r2d_verify", ROOT/"code/09_independent_verify.py")
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)
tests = []

def check(name, value):
    passed = bool(value)
    tests.append(dict(test=name, passed=passed))
    assert passed, name

check("Holm_declared_family_four", np.allclose(verify.holm_fixed_family([.04, .005], 4), [.12, .02]))
check("Holm_missing_preserved", np.allclose(verify.holm_fixed_family([.04, np.nan, .005], 4), [.12, np.nan, .02], equal_nan=True))
check("Holm_monotonicity_and_cap", np.allclose(verify.holm_fixed_family([.01, .04, .02, .9], 4), [.04, .08, .06, .9]))
check("Holm_no_valid_tests", np.isnan(verify.holm_fixed_family([np.nan], 4)).all())
check("missing_H4_not_estimable", verify.h4_magnitude_decision(pd.DataFrame()) == "NOT_ESTIMABLE")

def h4(low, high, difference):
    return pd.DataFrame(dict(contrast=["delta_low", "delta_high", "difference"],
        simultaneous_lower=[low[0], high[0], difference[0]],
        simultaneous_upper=[low[1], high[1], difference[1]]))

cases = [
    ("positive_larger", h4((.1,.3),(.4,.6),(.1,.5)), "MORE_SENSITIVE_IN_RESOURCE_ONE"),
    ("negative_larger_magnitude", h4((-.3,-.1),(-.6,-.4),(-.5,-.1)), "MORE_SENSITIVE_IN_RESOURCE_ONE"),
    ("positive_smaller", h4((.4,.6),(.1,.3),(-.5,-.1)), "LESS_SENSITIVE_IN_RESOURCE_ONE"),
    ("negative_smaller_magnitude", h4((-.6,-.4),(-.3,-.1),(.1,.5)), "LESS_SENSITIVE_IN_RESOURCE_ONE"),
    ("different_signs", h4((-.5,-.1),(.1,.4),(.2,.8)), "MAGNITUDE_DIRECTION_UNDETERMINED"),
    ("difference_interval_contains_zero", h4((.1,.4),(.2,.6),(-.1,.5)), "MAGNITUDE_DIRECTION_UNDETERMINED"),
    ("one_group_not_identified", h4((-.1,.4),(.2,.6),(.1,.5)), "MAGNITUDE_DIRECTION_UNDETERMINED"),
]
for name, data, expected in cases:
    check(name, verify.h4_magnitude_decision(data) == expected)
pd.DataFrame(tests).to_csv(ROOT/"tests/reporting_Python_validation.csv", index=False, encoding="utf-8-sig")
result = dict(passed=True, tests=len(tests), Mplus_calls=0,
    note="Synthetic rule tests only; actual pooled paths and contrasts await terminal analysis")
(ROOT/"tests/reporting_Python_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result))
