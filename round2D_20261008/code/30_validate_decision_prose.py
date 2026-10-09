"""验证最终文字不会把未估计、名义显著或另一方向写成假设支持。"""
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy
import hashlib
import importlib.util
import json

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
path = ROOT / "code/15_build_manuscripts.py"
loader = importlib.util.spec_from_file_location("manuscript_decision",path)
m = importlib.util.module_from_spec(loader)
loader.loader.exec_module(m)
checks = []


def check(name, value):
    checks.append(dict(check=name,passed=bool(value)))
    assert value,name


def rejected(function):
    try:
        function()
    except AssertionError:
        return True
    return False


state, pooled, slopes, contrasts, decisions = m.get_state(preview=True)
check("current_preview_is_not_a_final_judgment",
      "不作最终采用判断" in m.analysis_summary(state,pooled,decisions,preview=True))
if any(r["status"] == "IN_PROGRESS" for r in state.values()):
    check("running_family_cannot_enter_final_prose",
          rejected(lambda:m.analysis_summary(state,pooled,decisions)))

# 以下都是明确标记的汇报规则情景，不是CFPS估计或假设P值。
terminal = {key:dict(z=key[0],spec=key[1],eligible=False,status="NOT_POOLABLE") for key in state}
missing = [dict(resource=g,judgment="NOT_ESTIMABLE") for g in m.GN]
summary = m.analysis_summary(terminal,[],missing)
check("no_pooling_is_not_a_null_effect",
      "未取得可合并估计" in summary and "尚不能统计裁决" in summary and "无效应" not in summary)
row = dict(z="SD",spec="D1",label="dc",estimate=.2,se=.1,lower=.004,upper=.396,p=.0455,p_holm=.182)
nominal = m.group_result_text([row],"SD","D1")
check("nominal_interval_does_not_override_multiplicity",
      "Holm校正检验未通过" in nominal and "不能据此确认调节" in nominal)
supported = {**row,"estimate":.4,"lower":.204,"upper":.596,"p":.0000633,"p_holm":.0002532}
check("adjusted_interaction_is_reported_with_model_scope",
      "通过预定Holm校正检验" in m.group_result_text([supported],"SD","D1"))
mixed = deepcopy(terminal)
mixed[("SD","D1")]["eligible"] = True
mixed[("SD","D1")]["status"] = "CONDITIONAL_MI_REPORTABLE"
check("missing_adopted_coefficient_blocks_final_text",
      rejected(lambda:m.analysis_summary(mixed,[],missing)))
for group in ("EDU","URBAN"):
    mixed[("SD","H4_"+group)]["eligible"] = True
    mixed[("SD","H4_"+group)]["status"] = "CONDITIONAL_MI_REPORTABLE"
judgments = [dict(resource="EDU",judgment="MORE_SENSITIVE_IN_RESOURCE_ONE"),
             dict(resource="URBAN",judgment="LESS_SENSITIVE_IN_RESOURCE_ONE"),
             dict(resource="INC",judgment="NOT_ESTIMABLE")]
b = m.resource_hypothesis_text(mixed,judgments,"H4.2b")
a = m.resource_hypothesis_text(mixed,judgments,"H4.2a")
check("H4_opposing_predictions_remain_distinct",
      "教育：支持预定方向" in b and "城乡：证据方向与预测相反" in b
      and "教育：证据方向与预测相反" in a and "城乡：支持预定方向" in a)
check("unestimated_resource_remains_visible","有无个人收入：未取得可合并检验" in b)
summary = m.analysis_summary(mixed,[supported],judgments)
check("partial_resource_coverage_not_claimed_complete",
      "SD资源差异有2项可合并" in summary and "教育支持H4.2b" in summary and "城乡显示相反方向" in summary)
check("ineligible_family_cannot_support_H4",
      rejected(lambda:m.resource_hypothesis_text(terminal,judgments,"H4.2b")))
report = dict(status="PASS",checked_at=datetime.now(timezone.utc).isoformat(),checks=checks,
              source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),new_Mplus_calls=0,
              scope="Prose validation; synthetic decision examples are not empirical estimates or P values")
dest = ROOT / "tests/decision_prose_validation.json"
dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(dict(status="PASS",checks=len(checks),new_Mplus_calls=0,destination=str(dest))))
