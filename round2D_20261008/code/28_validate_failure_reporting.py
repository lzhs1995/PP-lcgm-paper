"""用已保存的真实终态验证报告分类，避免把退出码0或部分成员通过当作科学通过。"""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util
import json

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
spec = importlib.util.spec_from_file_location("r2d_reports",ROOT/"code/19_build_reports.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)
checks = []
sources = []

def check(name,condition):
    checks.append(dict(check=name,passed=bool(condition)))
    assert condition,name

def bound(z,kind,member,attempt):
    directory = ROOT/"models"/z/f"{kind}_Z0_MI{member:02d}"/attempt
    source = directory/"receipt.json"
    receipt = report.readjson(source)
    sources.append(dict(path=source.relative_to(ROOT).as_posix(),sha256=report.sha(source)))
    return directory,receipt,report.model_diagnostic(directory,receipt)

sexdir,sex,text = bound("SEXGAP","D1",1,"repair_start")
check("exitcode_zero_does_not_mean_success",sex["exitcode"] == 0 and not sex["normal"]
    and sex["status"] == "ESTIMATION_FAILED" and "无法求逆" in text and "711" in text and "时限" not in text)
sddir,sd,text = bound("SD","D1",1,"base")
check("independent_SD_error_iteration_preserved",sd["status"] == "ESTIMATION_FAILED" and "523" in text)
directory,bad,text = bound("OLDEST","D0",6,"base")
check("normal_termination_does_not_hide_negative_variance",bad["normal"] and not bad["usable"]
    and "负自由方差PSI:SY=" in text and "潜变量或测量协方差验收未通过" in text)
directory,repaired,text = bound("OLDEST","D0",6,"repair_start")
check("failed_start_repair_remains_failed",not repaired["usable"] and "负自由方差PSI:SY=" in text)
directory,good,text = bound("OLDEST","D0",1,"base")
check("single_member_success_does_not_imply_family_success",good["usable"]
    and "完整MI家族另行判断" in text)
check("running_model_not_interpreted",report.model_diagnostic(Path("not_read_for_running_model"),{})
    == "尚无终态；不解释中间迭代值")
text = report.model_diagnostic(Path("no_file_needed"),dict(status="TIMEOUT",limit_seconds=21600))
check("timeout_is_distinct_from_estimation_failure","时限" in text and "21600" in text and "求逆" not in text)
text = report.model_diagnostic(Path("no_file_needed"),dict(status="INADMISSIBLE",negative=[],geometry_ok=True,vcov_ok=False))
check("parameter_uncertainty_and_latent_geometry_separate",text == "参数估计协方差验收未通过")
state,*_ = report.m.get_state(preview=True)
ledger = report.execution_ledger(preview=True)
rows = report.family_execution_details(state,ledger)
old = next(r for r in rows if r["z"] == "OLDEST" and r["spec"] == "D0")
check("five_usable_members_not_pooled_after_sixth_failure",old["usable_members_in_family_receipt"] == 5
    and old["distinct_members_attempted"] == 6 and old["members_not_attempted"] == 4
    and not old["eligible"] and "第6份" in old["detail"] and "整个家族未合并" in old["detail"])
check("four_latent_and_three_H4_targets_remain_visible",
    len([r for r in rows if r["spec"] == "D1"]) == 4
    and len([r for r in rows if r["spec"].startswith("H4_")]) == 3)
result = dict(status="PASS",checked_at=datetime.now(timezone.utc).isoformat(),checks=checks,
    source_receipts=sources,report_code_sha256=report.sha(ROOT/"code/19_build_reports.py"),
    new_Mplus_calls=0,scope="Terminal classification and family-count reporting only; no new model fit or MI inference")
destination = ROOT/"tests/failure_reporting_validation.json"
destination.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(dict(status=result["status"],checks=len(checks),new_Mplus_calls=0,destination=str(destination)),ensure_ascii=False))
