"""为稿件补齐既有父模型及MI链证据；只读取旧结果，不调用Mplus或改动数据。"""
from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import json
import math
import shutil

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
OLD = ROOT.parent / "round2B_20261006"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    source_dir = ROOT / "audit/MI_source_snapshot"
    protocol = json.loads((source_dir / "mi_protocol.json").read_text(encoding="utf-8-sig"))
    targets = {k for k, v in protocol["methods"].items() if v}
    terminal = [r for r in rows(source_dir / "mi_convergence.csv")
                if int(r[".it"]) == protocol["maxit"] and r["vrb"] in targets]
    assert len(terminal) == len(targets) == 10
    assert {r["vrb"] for r in terminal} == targets
    psrf = [float(r["psrf"]) for r in terminal]
    assert all(math.isfinite(v) for v in psrf)
    with (ROOT / "audit/MI_terminal_chain_summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["variable", "iteration", "ac", "psrf"])
        writer.writeheader()
        writer.writerows(dict(variable=r["vrb"], iteration=r[".it"], ac=r["ac"], psrf=r["psrf"]) for r in terminal)
    binding = []
    destination = ROOT / "audit/parent_history_parameters"
    destination.mkdir(exist_ok=True)
    for member in range(1, 11):
        model_id = f"PARENT_MI{member:02}"
        source = OLD / "models" / model_id / "attempt01/parameters_high_precision.csv"
        values = [r for r in rows(source) if r["matrix"] == "psi" and r["row"] == r["column"] == "SY"]
        assert len(values) == 1
        value = values[0]
        assert math.isfinite(float(value["estimate"])) and float(value["estimate"]) < 0
        target = destination / f"{model_id}_parameters_high_precision.csv"
        if target.exists():
            assert sha(target) == sha(source)
        else:
            shutil.copy2(source, target)
        binding.append(dict(model=model_id, parameter=value["parameter"], sy_residual=value["estimate"],
                            se=value["se"], source_round="round2B_20261006",
                            source_relative_path=source.relative_to(OLD).as_posix(),
                            source_sha256=sha(source), copied_evidence=target.relative_to(ROOT).as_posix(),
                            role="HISTORICAL_INADMISSIBLE_DIAGNOSTIC_NOT_POOLED"))
    with (ROOT / "audit/parent_history_SY.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(binding[0]))
        writer.writeheader()
        writer.writerows(binding)
    # 只复用已执行的同样本聚类单变量形状诊断，补足论文引用的实际出处。
    univariate, univariate_sources = [], []
    target_root = ROOT / "audit/univariate_shape_history"
    target_root.mkdir(exist_ok=True)
    for shape in ("free", "linear"):
        model_id = "D3274_U0_" + shape
        directory = ROOT.parent / "round2_20261006/models" / model_id / "attempt01"
        fit = rows(directory / "fit.csv")[0]
        mean = [r for r in rows(directory / "parameters.csv") if r["paramHeader"] == "Means" and r["param"] == "SY"]
        assert len(mean) == 1 and int(fit["Observations"]) == 3274
        text = (directory / "model.inp").read_text(encoding="utf-8-sig")
        assert "CLUSTER=fid" in text and "y5@10" in text
        output = (directory / "model.out").read_text(encoding="utf-8-sig")
        assert "THE MODEL ESTIMATION TERMINATED NORMALLY" in output
        for filename in ("model.inp", "model.out", "fit.csv", "parameters.csv"):
            source = directory / filename
            target = target_root / model_id / filename
            target.parent.mkdir(exist_ok=True)
            if target.exists():
                assert sha(target) == sha(source)
            else:
                shutil.copy2(source, target)
            univariate_sources.append(dict(model=model_id, file=filename, source_sha256=sha(source),
                evidence=target.relative_to(ROOT).as_posix()))
        univariate.append(dict(model=model_id, shape=shape, N=fit["Observations"],
            sy_mean_0_10=mean[0]["est"], sy_se_0_10=mean[0]["se"], p_printed=mean[0]["pval"],
            sy_mean_0_1=float(mean[0]["est"])*10, sy_se_0_1=float(mean[0]["se"])*10,
            **{k: fit[k] for k in ("Parameters", "ChiSqM_Value", "ChiSqM_DF", "LL", "LLCorrectionFactor", "AIC", "BIC")}))
    with (ROOT / "audit/univariate_shape_summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(univariate[0]))
        writer.writeheader()
        writer.writerows(univariate)
    from scipy.stats import chi2
    free, linear = univariate
    df = int(free["Parameters"]) - int(linear["Parameters"])
    cd = (int(free["Parameters"])*float(free["LLCorrectionFactor"]) - int(linear["Parameters"])*float(linear["LLCorrectionFactor"])) / df
    statistic = 2*(float(free["LL"])-float(linear["LL"]))/cd
    comparison = rows(OLD / "audit/clustered_shape_comparison.csv")[0]
    assert df == 3 and abs(statistic-float(comparison["statistic"])) < 1e-8
    assert abs(float(chi2.sf(statistic,df))-float(comparison["p"])) < 1e-10
    shape_result = dict(df=df, correction=cd, statistic=statistic, p=float(chi2.sf(statistic,df)),
        precision="Printed likelihood and correction factors; old models, no new estimation", sources=univariate_sources)
    (ROOT / "audit/univariate_shape_binding.json").write_text(json.dumps(shape_result,ensure_ascii=False,indent=2),encoding="utf-8")
    result = dict(status="PASS", new_model_calls=0, historical_parent_members=len(binding),
                  sy_residual_min=min(float(r["sy_residual"]) for r in binding),
                  sy_residual_max=max(float(r["sy_residual"]) for r in binding),
                  imputed_targets=len(targets), terminal_iteration=protocol["maxit"],
                  psrf_min=min(psrf), psrf_max=max(psrf),
                  prior_univariate_models=len(univariate), prior_shape_statistic=statistic,
                  protocol_sha256=sha(source_dir / "mi_protocol.json"),
                  convergence_sha256=sha(source_dir / "mi_convergence.csv"),
                  note="Source binding and summary only; not a fresh imputation or model-fit validation",
                  created_at=datetime.now(timezone.utc).isoformat())
    (ROOT / "audit/reporting_support.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
