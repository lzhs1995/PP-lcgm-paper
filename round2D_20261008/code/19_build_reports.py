"""生成有明确采用范围的Round2D报告；草稿与最终发布文件分离。"""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
loader = importlib.util.spec_from_file_location("manuscript",ROOT/"code/15_build_manuscripts.py")
m = importlib.util.module_from_spec(loader)
loader.loader.exec_module(m)
BASE = "https://github.com/lzhs1995/PP-lcgm-paper"
TAG = "review-round2D-20261008"
PREFIX = "round2D_20261008"

def readjson(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def readcsv(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def writecsv(path,rows,columns):
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w = csv.DictWriter(f,fieldnames=columns,extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

def table(headers,rows):
    def esc(value):
        return str(value if value is not None else "—").replace("|","\\|").replace("\n","<br>")
    return "\n".join(["| "+" | ".join(map(esc,headers))+" |","| "+" | ".join("---" for _ in headers)+" |"]+
        ["| "+" | ".join(map(esc,row))+" |" for row in rows])+"\n"

def values_list(value):
    # jsonlite的单元素可自动简化为字符串；空NULL也可能保存为{}。
    if not value:
        return []
    return [value] if isinstance(value,str) else list(value)

def model_diagnostic(directory, receipt):
    """只解释已保存终态，不读取运行中迭代值，不重新裁定模型状态。"""
    if not receipt:
        return "尚无终态；不解释中间迭代值"
    status = receipt["status"]
    if status == "USABLE":
        return "本次模型与参数验收通过；完整MI家族另行判断"
    if status == "TIMEOUT":
        limit = receipt.get("limit_seconds")
        return "达到预定计算时限"+(f"（{float(limit):g}秒）" if limit is not None else "")+"；未获得可采用终值"
    if status == "NOT_CONVERGED":
        return "估计未收敛；原始OUT保留迭代与收敛诊断"
    if status == "ESTIMATION_FAILED":
        path = directory/"model.out"
        text = re.sub(r"\s+"," ",path.read_text(encoding="utf-8",errors="replace")) if path.exists() else ""
        if "THE ESTIMATED COVARIANCE MATRIX COULD NOT BE INVERTED" in text:
            iteration = re.search(r"COMPUTATION COULD NOT BE COMPLETED IN ITERATION\s+(\d+)",text)
            return "估计协方差矩阵无法求逆"+(f"（第{iteration[1]}次迭代）" if iteration else "")+"；估计未正常结束"
        return "估计计算失败，未正常结束；具体错误见原始OUT"
    if status == "INADMISSIBLE":
        details = []
        negatives = values_list(receipt.get("negative"))
        if negatives:
            parameters = readcsv(directory/"parameters_high_precision.csv")
            for key in negatives:
                matrix,variable = key.split(":",1)
                match = [p for p in parameters if p["matrix"].lower() == matrix.lower()
                    and p["row"] == p["column"] == variable]
                assert len(match) == 1,(directory,key)
                value = float(match[0]["estimate"])
                try:
                    se = float(match[0]["se"])
                except (ValueError,TypeError):
                    se = math.nan
                assert math.isfinite(value) and value < 0
                se_text = f"{se:.8g}" if math.isfinite(se) and se >= 0 else "不可用"
                details.append(f"负自由方差{matrix.upper()}:{variable}={value:.8g}（SE={se_text}）")
        if receipt.get("geometry_ok") is False:
            details.append("潜变量或测量协方差验收未通过")
        if receipt.get("vcov_ok") is False:
            details.append("参数估计协方差验收未通过")
        if any("SADDLE" in w.upper() for w in values_list(receipt.get("warnings"))):
            details.append("Mplus报告鞍点警告")
        return "；".join(details) if details else "模型验收未通过；详见parameter_gate与原始OUT"
    return {"INPUT_REJECTED":"输入被拒绝，未进入有效估计", "NO_OUTPUT":"未取得模型输出",
        "EXTRACTION_FAILED":"输出提取失败，不能据此宣称模型估计失败",
        "KEY_PATH_ERROR":"目标路径读取未通过", "PRINTED_MISMATCH":"保存参数与打印输出未对应"}.get(status,status)

def execution_ledger(preview):
    registered = readcsv(ROOT/"audit/CALL_REGISTER.csv")
    prepared = {readjson(p)["id"]:p.parent for p in (ROOT/"models").glob("*/*/*/input_contract.json")}
    rows = []
    for call in registered:
        directory = prepared[call["id"]]
        receipt = directory/"receipt.json"
        r = readjson(receipt) if receipt.exists() else {}
        assert preview or r, "Registered call is not terminal: "+call["id"]
        relative = directory.relative_to(ROOT).as_posix()
        rows.append(dict(**call,directory=relative,sample=r.get("sample",""),
            status=r.get("status","RUNNING_OR_PENDING_READBACK"),usable=r.get("usable",False),
            normal_termination=r.get("normal",False),seconds=r.get("seconds"),
            N=r.get("N"),households=r.get("households"),output_sha256=r.get("output_sha256",""),
            diagnostic_detail=model_diagnostic(directory,r),
            negative_variances=";".join(values_list(r.get("negative"))),
            geometry_ok=r.get("geometry_ok"),parameter_covariance_ok=r.get("vcov_ok"),
            integration_dimensions=r.get("integration_dimensions"),
            input_path=relative+"/model.inp",output_path=relative+"/model.out" if (directory/"model.out").exists() else "",
            receipt_path=relative+"/receipt.json" if r else ""))
    return rows

def family_execution_details(state,ledger):
    """区分单份通过、完整家族通过及未执行，不将失败成员静默删除。"""
    rows = []
    for (z,spec),current in state.items():
        calls = [r for r in ledger if r["z"] == z and r["spec"] == spec
            and r["category"] != "SYNTHETIC" and r["attempt"] != "completecase"]
        path = ROOT/"results"/f"{z}_{spec}_family.json"
        tried = len({int(r["member"]) for r in calls})
        usable = None
        detail = m.state_label(current["status"])
        if path.exists():
            family = readjson(path)
            members = [r for r in family["members"] if r["status"] != "NOT_RUN"]
            assert tried == len(members),(z,spec,tried,len(members))
            usable = sum(r["usable"] is True for r in members)
            if family["eligible"]:
                detail = "十份模型验收通过"+("；MI01积分及起点核查也通过" if spec not in {"D0","E0"} else "")
            else:
                failed = [r for r in members if not r["usable"]]
                if failed:
                    last = failed[-1]
                    bound = [r for r in calls if int(r["member"]) == last["member"] and r["attempt"] == last["attempt"]]
                    assert len(bound) == 1,(z,spec,last)
                    detail = f"第{last['member']}份："+bound[0]["diagnostic_detail"]+"；整个家族未合并"
                else:
                    detail = m.concise_reason(current)
        elif current["status"] == "IN_PROGRESS":
            detail = ("已有成员调用记录" if tried else "尚未执行")+"；尚无家族终态"
        rows.append(dict(z=z,spec=spec,eligible=m.boolean(current["eligible"]),status=current["status"],
            distinct_members_attempted=tried,usable_members_in_family_receipt=usable,
            members_not_attempted=10-tried,detail=detail))
    return rows

def report_text(state,pooled,slopes,h4,decisions,ledger,audit,terminal,preview):
    latent = sum(m.boolean(state[(z,"D1")]["eligible"]) for z in m.ZN)
    observed = sum(m.boolean(state[(z,"E1")]["eligible"]) for z in m.ZN)
    hg = sum(m.boolean(state[("SD","H4_"+g)]["eligible"]) for g in m.GN)
    counts = Counter(r["category"] for r in ledger)
    statuses = Counter(r["status"] for r in ledger)
    mode = "执行中草稿：不用于最终采用判断" if preview else "阶段交付报告：本批已收口，原完整研究计划未全部执行"
    citation_path = ROOT/"manuscript"/("preview_in_progress" if preview else "delivery")/"retained_citations.json"
    citation_metadata = readjson(citation_path)
    retained_citation_count = citation_metadata["citation_count"]
    removed_citation_count = len(citation_metadata.get("deliberately_removed_citations",[]))
    report = ["# PP-LGCM Round2D：阶段成果、潜调节计算与未竟问题", "", mode, "",
        "本次按用户批准的阶段计算预算结束追加估计。请先读[阶段结论与下一步评议](STAGE_SUMMARY.md)；四项观测基期路线、三项H4对比及性能探针均列为延期，未把未执行解释为无效应。", "",
        "本轮承接SW作为主要工作父模型，直接推进家内差异是否改变亲近度变化—抑郁变化关联的问题。已修复的CES-D计分、基期来源和家庭共同值不再重做。外部建议经过本机代码、输入和输出核对后分别采纳或调整，详见[外部建议裁定](reports/REVIEW_SYNTHESIS.md)及[正文／附录75个实际编号的处理对照](audit/MANUSCRIPT_REVIEW_RESPONSE.md)。这份报告不代表两位网页端已经复核本轮新结果。", "",
        "## 1. 本轮实际达到的范围", "",
        f"四项潜交互中 **{latent}/4** 项形成满足预定门槛的十份条件MI估计；观测基期路线 **{observed}/4** 项形成相应估计；SD的三项资源组间差异中 **{hg}/3** 项形成可合并对比。未通过、未执行和备用未触发均在下表保留，不转写为无效应。", "",
        m.analysis_summary(state,pooled,decisions,preview), "",
        f"当前记录的队列终态原因：`{terminal.get('reason','IN_PROGRESS')}`。{terminal.get('message','当前Mplus作业仍在估计，不能发布最终合并。')}","",
        "SW通过的是双过程父模型的条件推断。新增第三轨迹和交互必须评价自身，不能由父模型通过推定通过，也不能由父模型主路径不显著推定没有调节。", "",
        "## 2. 调节结果与采用状态", "",
        "四个潜交互分别是SD、性别差、老大差、长子差的 `SX × IZ → SY`。分析N依次3274、2339、3159、2894，要求2012年对应Z实际可计算，不取四分支交集。", "",
        table(["潜在Z","N","δ (SE)","95%条件MI区间","P / Holm P","状态"],m.core_table_rows(state,pooled,"D1")),
        "观测基期Z₀是另一估计对象。原计划事前指定SD路线用于资源组检验，其他分支为潜交互未通过后的备用；本阶段按计算预算延期，尚未实际估计，不按P值选择路线。", "",
        table(["观测Z₀","N","δ (SE)","95%条件MI区间","P / Holm P","状态"],m.core_table_rows(state,pooled,"E1")),
        "四个潜交互与四个观测路线分别预定按固定家族数4进行Holm校正，未估计项不补作P=0或P=1。条件斜率必须使用完整参数协方差逐份计算后合并；本阶段无合格交互MI家族，对应结果文件为空，不代表已经检验且不显著。", "",
        "SD原始值在基期约75.6%为零，标准化后最小值−0.4759262086。预定观测参考z=−1超出实际及非负SD允许范围，必须作外推标记。潜在IZ的高斯参考值与观测范围不是同一对象。", "",
        "## 3. H4.2b：直接检验组间差异", "",
        "原计划仅检验观测2012年SD与教育、城乡、有无个人收入的组间调节差异，本阶段三项均未执行。`δ`、`δ+δG`和`δG`分别是设计中的资源0组调节、资源1组调节和两组差异，不比较组内星号。", ""]
    hr = []
    for g in m.GN:
        q = {r["contrast"]:r for r in h4 if r["resource"] == g}
        judge = next((r["judgment"] for r in decisions if r["resource"] == g),"NOT_ESTIMABLE")
        if q:
            a = q["difference"]
            hr.append([m.GN[g],m.fmt(q["delta_low"]["estimate"]),m.fmt(q["delta_high"]["estimate"]),m.fmt(a["estimate"]),m.ci(a),m.pv(a["p"]),m.pv(a.get("p_holm_difference")),m.JUDGMENT[judge]])
        else:
            hr.append([m.GN[g],"—","—","—","—","—","—",m.state_label(state[("SD","H4_"+g)]["status"])])
    report += [table(["资源","δ₀","δ₁","差异δG","差异95%区间","P","Holm P","方向/状态"],hr),
        "教育1＝初中及以上；城乡1＝国家统计局2012城市分类；收入1＝个人收入金额大于零。第三项是有无个人收入，不能写成高收入。原设计为三项差异预定家族数3的Holm，并为两组调节与差异共九个对比预定Bonferroni同时95%区间；本阶段尚未产生这些检验或区间。只有同向且幅度差异可判时，才使用“更敏感/较不敏感”的方向解释。", "",
        "## 4. 实际执行，不混淆计算与科学检验", "",
        f"调用登记共 **{len(ledger)}** 次；其中合成接口检查 **{counts.get('SYNTHETIC',0)}** 次，CFPS实际数据调用 **{len(ledger)-counts.get('SYNTHETIC',0)}** 次。类别包括目标拟合、必要数值核查、限定修复和触发的备用拟合；它们不是同样多的独立研究假设。", "",
        table(["调用类别","次数"],sorted(counts.items())),
        table(["原始调用终态","次数"],sorted(statuses.items())),
        "下表将单份验收与整个MI家族分开。单份可用的计数采用家族最终绑定的尝试；没有家族终态时留空，不用正在运行的值预判。完整原因表见 `FAMILY_EXECUTION_DETAILS.csv`，逐次诊断见 `MODEL_EXECUTION.csv`。负方差数值仅用于定位不合法解，不能作为正式效应。", "",
        table(["差异","规格","已调用成员","单份可用","未调用成员","采用或停止依据"],
            [[m.ZN[r["z"]],m.display_spec(r["spec"]),r["distinct_members_attempted"],
              r["usable_members_in_family_receipt"],r["members_not_attempted"],r["detail"]]
             for r in family_execution_details(state,ledger)]),
        "每次调用的完整输入输出、状态、样本、时间和哈希见[模型索引](MODEL_INDEX.md)及 `MODEL_EXECUTION.csv`。正常终止、单份合法、数值稳定及整个MI家族可合并是不同层级。D0失败后仍独立尝试D1，非法D0不用于普通LRT。", "",
        "原预登记上限为单次6小时、累计估计168小时，单槽单核；上限不是必须跑满的配额。本次用户另行批准在当前长子差尝试终态后结束追加，原168小时上限并未耗尽。原合同与新增阶段合同同时保留，延期目标及原因逐项列明。没有为了跨过0.05扩充交互、换切点或删除控制。", "",
        "数值实现的补充只涉及明确的终态错误、Mplus自身建议的限定EM修复以及已通过同规格的起始值复用，详见 `audit/NUMERICAL_AND_REPORTING_AMENDMENT.md` 与实际调用记录。某项修复未被触发时，不宣称已经运行或提速。早期worker将独立控制台写到Documents的相对路径问题已定位；原始完整OUT仍保留，缺失的早期独立控制台不能虚称齐全。", "",
        "## 5. 独立数值核对与数据边界", "",
        f"独立Python复核状态为 **{audit['status']}**。已核对{audit['model_count']}份终态模型记录、{audit['printed_parameter_rows']}行打印参数、{audit['high_precision_parameters']}个高精度自由参数、{audit['rebuilt_matrices']}个适用模型矩阵；条件路径/对比检查{audit['pooled_path_or_contrast_checks']}项，既有SW结构检查{audit['existing_SW_structure_checks']}项。计数包含明确区分的合成模型，不代表同等数量的实证发现。", "",
        "该复核直接读取原始TECH1、RESULTS、TECH3和打印输出，与生产表逐项对照；没有重新拟合CFPS个人数据。公开材料足以独立复算所保存的参数和条件MI对比，不能据此宣称云端已重估微观记录。程序测试的通过也不等于实际模型成立。", "",
        "本轮复用十份家庭—个人分层MI，350项新增Z/纵向冻结检查通过。既有家庭共同值和观测保持等数据层修复有效；实际插补预测矩阵审计仍未证明与三过程LMS相容。基期Z特征存在于预测矩阵中，但完整潜交互分布、全部后期Z和非线性结构没有建立为相容联合模型。", "",
        "修正八题CES-D的α与当前各期总分、缺失掩码及人数已绑定；本轮没有重读全部原始条目。计分已解决与测量不变性未检验分开记录。", "",
        "独立复核另外核对了稿件引用的旧父模型SY残差、十个插补目标的末轮诊断，以及两份旧单变量形状输出的50行打印参数和尺度换算；相应计数在 `historical_reporting_context_checks` 单列，不计作Round2D新调用。新增附表A18说明AIC／BIC对形状选择并不一致；SW自由Y形状敏感性仍延期。", "",
        "## 6. 七项意见与全部原假设", "",
        table(["原问题","当前状态","范围"],m.seven_issue_rows(state)),
        table(["原假设","预测","检验范围及状态"],m.hypothesis_rows(state,decisions)),
        "本阶段延期：剩余潜交互数值核查和MI成员、全部观测基期路线、三项H4比较、SD完整协变量诊断、六次短性能探针。此前延期的父母性别异质性、IX交互家族、其他时间组合、自由形状Y、其他抑郁量尺、四期窗口、新插补和bootstrap继续保留。未执行事项没有从状态表中消失，也没有写成无效应。", "",
        "## 7. 正文v49与附录v41", "",
        "当前稿将SW放在主要位置，C1保留为强约束敏感性，XLIN不采用；补足共同八题、两项5−原分反向、完整作答、尺度常数、基期控制编码、四Z资格及支持范围。原单变量0.037的原始分0/10尺度与0/1表达0.370明确区分，不解释为当前标准化SW的恒定年变化。", "",
        f"保留{retained_citation_count}个原有Zotero引用域，明确移除{removed_citation_count}项错置引文域：Brown／Friedman不再被挂在剔除追访次数控制的句子后。这是纠正本稿归因，不是判定两篇文献错误；删除对象和原因随稿登记，其余域保持原内容。当前方法内容替代了重复的历史长脚注。本文没有刷新本机Zotero库，也没有进行或声称NotebookLM验收。新稿的原生Word导出、逐表逐格PDF检查和页面审阅绑定最终DOCX/PDF哈希；预览检查不能代替最终检查。", "",
        "方法补入十个实际插补目标第30轮的PSRF及范围，附录增加既有父模型、敏感性拟合统计与起点复核范围。旧十份父模型的SY负残差逐成员绑定原高精度输出，作为采用SW的诊断背景，不合并旧不合法系数，也没有为补文字重新估计。", "",
        "文献疑点另按实际来源处理：两篇Zhang（2025）的出版方元数据确认作者及顺序相同，不支持误复制的猜测；Chen等（2021b）讨论instrumental support，已改为工具性支持。Raudenbush与Chan（1992）、mice软件引用及Bartlett等（2015）的方法元数据也已核对，未冒称本轮逐篇全文复读。", "",
        "## 8. 交付范围", "",
        "公开内容为报告、同版DOCX/PDF与在线可读文字、代码、聚合模型输出、高精度参数/协方差、状态及哈希清单。微观DAT、真实PID/FID、逐人得分和插补对象不进入GitHub。`estimates.dat`与`tech3.dat`是模型参数/协方差的聚合保存文件，与个人`data.dat`不同。", "",
        "每个ZIP限制为25,000,000字节；所有包应解压到同一目录。ZIP和内部文件哈希、CRC、公开范围审查与匿名回读分别登记。固定提交链接在发布后的反馈说明中提供。", ""]
    return "\n".join(report)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview",action="store_true")
    args = parser.parse_args()
    directory = ROOT/("reports_draft" if args.preview else "reports_final")
    directory.mkdir(exist_ok=True,parents=True)
    state,pooled,slopes,h4,decisions = m.get_state(args.preview)
    audit = readjson(ROOT/"evidence/independent_verification.json")
    terminal = readjson(ROOT/"runtime/queue_terminal.json") if (ROOT/"runtime/queue_terminal.json").exists() else {}
    if not args.preview:
        assert terminal["status"] == "QUEUE_TERMINAL" and audit["status"] == "PASS"
        assert readjson(ROOT/"results/SUMMARY.json")["status"] == "SUMMARIZED"
        doc = readjson(ROOT/"manuscript/delivery/manuscript_validation.json")
        assert not doc["preview"] and doc["status"] in {"PASS","PASS_PENDING_VISUAL"}
    ledger = execution_ledger(args.preview)
    (directory/"REPORT.md").write_text(report_text(state,pooled,slopes,h4,decisions,ledger,audit,terminal,args.preview),encoding="utf-8")
    writecsv(directory/"MODEL_EXECUTION.csv",ledger,list(ledger[0]))
    family_details = family_execution_details(state,ledger)
    writecsv(directory/"FAMILY_EXECUTION_DETAILS.csv",family_details,list(family_details[0]))
    seven = [dict(issue=a,status=b,scope=c) for a,b,c in m.seven_issue_rows(state)]
    writecsv(directory/"SEVEN_ISSUES.csv",seven,["issue","status","scope"])
    hypotheses = [dict(hypothesis=a,prediction=b,scope_and_status=c) for a,b,c in m.hypothesis_rows(state,decisions)]
    writecsv(directory/"HYPOTHESES.csv",hypotheses,["hypothesis","prediction","scope_and_status"])
    index = ["# 实际模型调用索引", "", "每行是一次实际调用；合成接口与真实数据分开。已注册但未终态的调用只会出现在执行中草稿。原始OUT内的显著系数不自动获得采用资格。", "",
        table(["调用","类别","状态","N","秒","终态依据","输入","输出","回执"],
            [[r["id"],r["category"],r["status"],r["N"],m.fmt(r["seconds"],1),r["diagnostic_detail"],f"[INP]({r['input_path']})",f"[OUT]({r['output_path']})" if r["output_path"] else "—",f"[JSON]({r['receipt_path']})" if r["receipt_path"] else "—"] for r in ledger]),
        "`.inp.txt`与`.out.txt`镜像只为网页端直接阅读，字节须与原件相同。`parameter_gate.json`对应单次合法性，`results/*_family.json`对应完整MI家族及数值检查；两层不能互相替代。", ""]
    (directory/"MODEL_INDEX.md").write_text("\n".join(index),encoding="utf-8")
    raw = f"https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/{TAG}/{PREFIX}"
    feedback = f"""# 给ChatGPT网页端与Claude网页端的Round2D阶段评议说明

这是上一轮SW父模型之后的阶段交付。潜调节长耗时且未形成完整可采用MI估计，已按用户批准的预算停止追加。观测基期替代、H4和六次短测速均延期，尚未执行。请先读[STAGE_SUMMARY]({raw}/STAGE_SUMMARY.md)、[完整报告]({raw}/REPORT.md)、[外部建议裁定]({raw}/reports/REVIEW_SYNTHESIS.md)、[采用状态]({raw}/results/family_status.csv)和[模型索引]({raw}/MODEL_INDEX.md)，再对照正文v49和附录v41阶段稿。

请直接核对实际文件，不把任务书、程序测试或“正常结束”替代真实模型验收。包清单见[PACKAGE_MANIFEST]({raw}/PACKAGE_MANIFEST.json)，全部ZIP解压至同一目录后，`code/09_independent_verify.py --root <目录> --require-terminal --evidence-output <另一个输出目录>`可重算公开聚合证据并保持解压包不变；需要numpy、pandas与scipy，这不会重新拟合微观数据。

请重点回应：

1. 当前停止追加的决定是否合理？请结合[FAMILY_EXECUTION_DETAILS]({raw}/FAMILY_EXECUTION_DETAILS.csv)及[逐目标延期台账]({raw}/TARGET_DISPOSITIONS.csv)，区分信息矩阵求逆失败、负方差、超时和未执行；不要将其转写成四种调节均不存在。
2. 六个增长因子、同源比值指标、零值集中及连续高斯近似，哪些可能影响识别和条件数？请提出能区分这些解释的最小诊断，不能只猜一个唯一原因，也不要按P值删除控制或同期残差。
3. [性能复核]({raw}/audit/PERFORMANCE_REVIEW_20261009.md)与[最终耗时表]({raw}/PERFORMANCE_FINAL.csv)显示主要耗时在引擎。PROCESSORS=1有改进空间，但两维15点积分是225节点，Monte Carlo5000不保证更快，纯EM修复也未获得合法解。六个短探针尚未运行；是否应先做有限1/2/4核校准或合法起点映射？请给出次数、时限、数值精度标准和停止条件，不直接建议再运行数十小时。
4. 是否优先采用SW加观测2012年Z₀的备用设计？该设计改变估计对象；请给出理论得失、最小SD试运行与验收要求。H4尚未执行，若将来恢复，须直接检验三阶差异，有个人收入须区别于高收入。
5. 当前MI预测矩阵与潜交互的具体相容性缺口应如何处理？请区分数据层已修复、条件工作推断和新插补敏感性，不重复宣布家庭共同值未修复；使用因子得分或Bayes也需说明估计对象与不确定性变化。
6. 正文v49/附录v41与本批实际结果是否同步？引文保留及明确删除记录、CES-D共同八题、原始分与标准化时间尺度、MI链诊断、所有原假设状态有无遗漏？Brown/Friedman错置引文已明确移除，请勿以机械保留原72域为验收要求。
7. 哪些问题可关闭，哪些只达到工作模型层面，哪些延期？请将建议按“无需新估计即可确认／有界小试／暂不值得继续”排序，注明改变什么、最多几次／多久、成功与停止标准，并引用本包具体文件。

本包不含真实PID/FID、微观收入、个人DAT、逐人因子得分或插补对象。可复核保存统计量、代码与聚合证据；不能宣称已在云端独立重估全部CFPS个人记录。两位网页端此前审阅过的资料不等于已经审阅本轮新增结果。

关于建议分歧：本轮保留四项SX×IZ主线，不扩IX交互；C1结构嵌套于SW，但不使用普通缩放df=6卡方直接作边界显著性判断；不根据父模型SE预判交互毫无信息，不用临时SESOI或任意家庭数减参数数的自由度。具体理由和已核实的文献疑点见外部建议裁定。
"""
    (directory/"FOR_WEB_REVIEWERS.md").write_text(feedback,encoding="utf-8")
    readme = f"""# PP-LGCM Round2D：阶段成果与未竟问题（2026-10-09收口）

本目录是Round2C之后的阶段交付。SW父工作模型可报告；四项潜调节未形成完整可采用MI估计，观测替代与H4尚未执行，已按计算预算停止追加。请以[阶段结论](STAGE_SUMMARY.md)、[完整报告](REPORT.md)与[各家族状态](results/family_status.csv)为准；正文与附录均为阶段稿。

阅读顺序：

1. [阶段结论与评议重点](STAGE_SUMMARY.md)、[报告](REPORT.md)及[七项意见](SEVEN_ISSUES.csv)。
2. [四Z和资源差异状态](results/family_status.csv)、[合并路径](results/pooled_paths.csv)、[H4对比](results/H4_contrasts.csv)。
3. [正文v49可读文本](manuscripts/main_readable.md)和[附录v41可读文本](manuscripts/appendix_readable.md)；原生DOCX/PDF在同一目录。
4. [分支采用与停止原因](FAMILY_EXECUTION_DETAILS.csv)、[模型索引](MODEL_INDEX.md)、[独立复核](evidence/independent_verification.json)及[网页端复核说明](FOR_WEB_REVIEWERS.md)。
5. [包清单](PACKAGE_MANIFEST.json)与[文件清单](FILE_MANIFEST.csv)。所有ZIP请解压到同一目录，不按包划分推断范围。

每包≤25,000,000字节。微观数据、真实PID/FID、逐人得分及MI对象不公开；参数和TECH3聚合保存文件可公开复算。未执行、不可合并和合法但估计不精确的结果均保留，不按显著性删选。历史资料仍可追溯到[Round2C固定提交]({BASE}/tree/63c5eb3bfb7525d4e6dbf4876f0d0a9998c47ef0/round2C_20261007)。

本目录预定不可移动标签为`{TAG}`；发布后的完整提交哈希与匿名回读回执另行提供。
"""
    (directory/"README.md").write_text(readme,encoding="utf-8")
    scope = dict(round="Round2D",preview=args.preview,ready_for_publication=False,
        release_type="PARTIAL_RESEARCH_STAGE_FOR_EXTERNAL_REVIEW",scientific_project_complete=False,
        latest_stage_contract="audit/stage_closeout_20261009/closeout_contract.json",
        queue_terminal=terminal,independent_status=audit["status"],
        active_contract_sha256=sha(ROOT/"RUN_CONTRACT.json"),
        latent_families_reportable=sum(m.boolean(state[(z,"D1")]["eligible"]) for z in m.ZN),
        observed_families_reportable=sum(m.boolean(state[(z,"E1")]["eligible"]) for z in m.ZN),
        H4_families_reportable=sum(m.boolean(state[("SD","H4_"+g)]["eligible"]) for g in m.GN),
        remaining_scientific_scope=["valid core latent interaction inference","observed baseline alternatives not executed", "H4 resource comparisons not executed", "performance probes not executed", "window and scale sensitivity","Y shape sensitivity","MI and latent-interaction congeniality","other original hypotheses explicitly marked untested"],
        public_microdata=False,created_at=datetime.now(timezone.utc).isoformat(),
        note="Publication readiness is set only after final document, privacy, package and evidence verification.")
    (directory/"DELIVERY_SCOPE.json").write_text(json.dumps(scope,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(dict(directory=str(directory),preview=args.preview,calls=len(ledger)),ensure_ascii=False))

if __name__ == "__main__":
    main()
