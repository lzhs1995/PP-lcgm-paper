"""生成有明确采用范围的Round2D报告；草稿与最终发布文件分离。"""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import argparse
import csv
import hashlib
import importlib.util
import json

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
            input_path=relative+"/model.inp",output_path=relative+"/model.out" if (directory/"model.out").exists() else "",
            receipt_path=relative+"/receipt.json" if r else ""))
    return rows

def report_text(state,pooled,slopes,h4,decisions,ledger,audit,terminal,preview):
    latent = sum(m.boolean(state[(z,"D1")]["eligible"]) for z in m.ZN)
    observed = sum(m.boolean(state[(z,"E1")]["eligible"]) for z in m.ZN)
    hg = sum(m.boolean(state[("SD","H4_"+g)]["eligible"]) for g in m.GN)
    counts = Counter(r["category"] for r in ledger)
    statuses = Counter(r["status"] for r in ledger)
    mode = "执行中草稿：不用于最终采用判断" if preview else "执行终态报告：科学完成范围逐项列明"
    report = ["# PP-LGCM Round2D：核心调节、资源差异与论文交付", "", mode, "",
        "本轮承接SW作为主要工作父模型，直接推进家内差异是否改变亲近度变化—抑郁变化关联的问题。已修复的CES-D计分、基期来源和家庭共同值不再重做。外部建议经过本机代码、输入和输出核对后分别采纳或调整，详见[外部建议裁定](reports/REVIEW_SYNTHESIS.md)。这份报告不代表两位网页端已经复核本轮新结果。", "",
        "## 1. 本轮实际达到的范围", "",
        f"四项潜交互中 **{latent}/4** 项形成满足预定门槛的十份条件MI估计；观测基期路线 **{observed}/4** 项形成相应估计；SD的三项资源组间差异中 **{hg}/3** 项形成可合并对比。未通过、未执行和备用未触发均在下表保留，不转写为无效应。", "",
        f"当前记录的队列终态原因：`{terminal.get('reason','IN_PROGRESS')}`。{terminal.get('message','当前Mplus作业仍在估计，不能发布最终合并。')}","",
        "SW通过的是双过程父模型的条件推断。新增第三轨迹和交互必须评价自身，不能由父模型通过推定通过，也不能由父模型主路径不显著推定没有调节。", "",
        "## 2. 调节结果与采用状态", "",
        "四个潜交互分别是SD、性别差、老大差、长子差的 `SX × IZ → SY`。分析N依次3274、2339、3159、2894，要求2012年对应Z实际可计算，不取四分支交集。", "",
        table(["潜在Z","N","δ (SE)","95%条件MI区间","P / Holm P","状态"],m.core_table_rows(state,pooled,"D1")),
        "观测基期Z₀是另一估计对象。SD路线为资源组检验事前指定，其他分支仅在潜交互未通过限定核查后触发；不会按P值选择路线。", "",
        table(["观测Z₀","N","δ (SE)","95%条件MI区间","P / Holm P","状态"],m.core_table_rows(state,pooled,"E1")),
        "四个潜交互与四个观测路线分别按固定家族数4进行Holm校正，未估计项不补作P=0或P=1。条件斜率使用完整参数协方差逐份计算后合并，见 `results/conditional_slopes.csv`。", "",
        "SD原始值在基期约75.6%为零，标准化后最小值−0.4759262086。预定观测参考z=−1超出实际及非负SD允许范围，必须作外推标记。潜在IZ的高斯参考值与观测范围不是同一对象。", "",
        "## 3. H4.2b：直接检验组间差异", "",
        "本轮仅检验观测2012年SD与教育、城乡、有无个人收入的组间调节差异。`δ`、`δ+δG`和`δG`分别是资源0组调节、资源1组调节和两组差异，不比较组内星号。", ""]
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
        "教育1＝初中及以上；城乡1＝国家统计局2012城市分类；收入1＝个人收入金额大于零。第三项是有无个人收入，不能写成高收入。三项差异采用固定家族数3的Holm；两组调节与差异共九个对比另给Bonferroni同时95%区间。只有同向且幅度差异可判时，才使用“更敏感/较不敏感”的方向解释。", "",
        "## 4. 实际执行，不混淆计算与科学检验", "",
        f"调用登记共 **{len(ledger)}** 次；其中合成接口检查 **{counts.get('SYNTHETIC',0)}** 次，CFPS实际数据调用 **{len(ledger)-counts.get('SYNTHETIC',0)}** 次。类别包括目标拟合、必要数值核查、限定修复和触发的备用拟合；它们不是同样多的独立研究假设。", "",
        table(["调用类别","次数"],sorted(counts.items())),
        table(["原始调用终态","次数"],sorted(statuses.items())),
        "每次调用的完整输入输出、状态、样本、时间和哈希见[模型索引](MODEL_INDEX.md)及 `MODEL_EXECUTION.csv`。正常终止、单份合法、数值稳定及整个MI家族可合并是不同层级。D0失败后仍独立尝试D1，非法D0不用于普通LRT。", "",
        "预登记上限为单次6小时、累计估计168小时，单槽单核；上限不是必须跑满的配额。遇到执行预算或资源等待终点时，仍保留尚未执行的目标及具体原因。没有为了跨过0.05扩充交互、换切点或删除控制。", "",
        "数值实现的补充只涉及明确的终态错误、Mplus自身建议的限定EM修复以及已通过同规格的起始值复用，详见 `audit/NUMERICAL_AND_REPORTING_AMENDMENT.md` 与实际调用记录。某项修复未被触发时，不宣称已经运行或提速。早期worker将独立控制台写到Documents的相对路径问题已定位；原始完整OUT仍保留，缺失的早期独立控制台不能虚称齐全。", "",
        "## 5. 独立数值核对与数据边界", "",
        f"独立Python复核状态为 **{audit['status']}**。已核对{audit['model_count']}份终态模型记录、{audit['printed_parameter_rows']}行打印参数、{audit['high_precision_parameters']}个高精度自由参数、{audit['rebuilt_matrices']}个适用模型矩阵；条件路径/对比检查{audit['pooled_path_or_contrast_checks']}项，既有SW结构检查{audit['existing_SW_structure_checks']}项。计数包含明确区分的合成模型，不代表同等数量的实证发现。", "",
        "该复核直接读取原始TECH1、RESULTS、TECH3和打印输出，与生产表逐项对照；没有重新拟合CFPS个人数据。公开材料足以独立复算所保存的参数和条件MI对比，不能据此宣称云端已重估微观记录。程序测试的通过也不等于实际模型成立。", "",
        "本轮复用十份家庭—个人分层MI，350项新增Z/纵向冻结检查通过。既有家庭共同值和观测保持等数据层修复有效；实际插补预测矩阵审计仍未证明与三过程LMS相容。基期Z特征存在于预测矩阵中，但完整潜交互分布、全部后期Z和非线性结构没有建立为相容联合模型。", "",
        "修正八题CES-D的α与当前各期总分、缺失掩码及人数已绑定；本轮没有重读全部原始条目。计分已解决与测量不变性未检验分开记录。", "",
        "## 6. 七项意见与全部原假设", "",
        table(["原问题","当前状态","范围"],m.seven_issue_rows(state)),
        table(["原假设","预测","检验范围及状态"],m.hypothesis_rows(state,decisions)),
        "本轮延期：父母性别异质性、IX交互家族、其他时间组合、自由形状Y、其他抑郁量尺、四期窗口、新插补和bootstrap。未执行事项没有从状态表中消失，也没有写成无效应。", "",
        "## 7. 正文v49与附录v41", "",
        "当前稿将SW放在主要位置，C1保留为强约束敏感性，XLIN不采用；补足共同八题、两项5−原分反向、完整作答、尺度常数、基期控制编码、四Z资格及支持范围。原单变量0.037的原始分0/10尺度与0/1表达0.370明确区分，不解释为当前标准化SW的恒定年变化。", "",
        "原有72个Zotero引用域保留；当前方法内容替代了重复的历史长脚注。本文没有刷新本机Zotero库，也没有进行或声称NotebookLM验收。新稿的原生Word导出、逐表逐格PDF检查和页面审阅绑定最终DOCX/PDF哈希；预览检查不能代替最终检查。", "",
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
    seven = [dict(issue=a,status=b,scope=c) for a,b,c in m.seven_issue_rows(state)]
    writecsv(directory/"SEVEN_ISSUES.csv",seven,["issue","status","scope"])
    hypotheses = [dict(hypothesis=a,prediction=b,scope_and_status=c) for a,b,c in m.hypothesis_rows(state,decisions)]
    writecsv(directory/"HYPOTHESES.csv",hypotheses,["hypothesis","prediction","scope_and_status"])
    index = ["# 实际模型调用索引", "", "每行是一次实际调用；合成接口与真实数据分开。已注册但未终态的调用只会出现在执行中草稿。原始OUT内的显著系数不自动获得采用资格。", "",
        table(["调用","类别","状态","N","秒","输入","输出","回执"],
            [[r["id"],r["category"],r["status"],r["N"],m.fmt(r["seconds"],1),f"[INP]({r['input_path']})",f"[OUT]({r['output_path']})" if r["output_path"] else "—",f"[JSON]({r['receipt_path']})" if r["receipt_path"] else "—"] for r in ledger]),
        "`.inp.txt`与`.out.txt`镜像只为网页端直接阅读，字节须与原件相同。`parameter_gate.json`对应单次合法性，`results/*_family.json`对应完整MI家族及数值检查；两层不能互相替代。", ""]
    (directory/"MODEL_INDEX.md").write_text("\n".join(index),encoding="utf-8")
    raw = f"https://raw.githubusercontent.com/lzhs1995/PP-lcgm-paper/{TAG}/{PREFIX}"
    feedback = f"""# 给ChatGPT网页端与Claude网页端的Round2D复核说明

这是上一轮SW父模型之后的执行交付。请先读取[REPORT]({raw}/REPORT.md)、[外部建议裁定]({raw}/reports/REVIEW_SYNTHESIS.md)、[采用状态]({raw}/results/family_status.csv)和[模型索引]({raw}/MODEL_INDEX.md)，再对照当前正文与附录。

请直接核对实际文件，不把任务书、程序测试或“正常结束”替代真实模型验收。包清单见[PACKAGE_MANIFEST]({raw}/PACKAGE_MANIFEST.json)，全部ZIP解压至同一目录后，`code/09_independent_verify.py --root <目录> --require-terminal --evidence-output <另一个输出目录>`可重算公开聚合证据并保持解压包不变；需要numpy、pandas与scipy，这不会重新拟合微观数据。

请重点回应：

1. 四项潜交互和触发的观测路线是否按各自资格、尺度、模型及完整成员报告？有没有将不可估计、未执行或区间宽误写成无效应？
2. 首份MI的起点和积分检查是否与实际采用的尝试绑定？是否保留全部失败成员和终态原因？
3. 条件斜率是否使用完整协方差并逐份合并？SD观测参考−1是否明确为外推？
4. 三项H4差异是否直接检验三阶参数？九个同时区间是否足以支持所用的方向措辞？有个人收入是否被正确区别于高收入？
5. MI预测矩阵的具体相容性缺口与固定模型条件推断的范围，是否表达准确？请不要把已修好的家庭共同值再次泛化为未修复。
6. 正文v49/附录v41与本批实际结果是否同步？72个原有引文域、CES-D共同八题、原始分与标准化时间尺度、所有原假设状态有无遗漏？
7. 哪些问题可在本轮关闭，哪些只达到工作模型层面，哪些属于明确延期？请提出有终点、针对现有证据的下一步，避免重复已完成的计分和父模型修复。

本包不含真实PID/FID、微观收入、个人DAT、逐人因子得分或插补对象。可复核保存统计量、代码与聚合证据；不能宣称已在云端独立重估全部CFPS个人记录。两位网页端此前审阅过的资料不等于已经审阅本轮新增结果。

关于建议分歧：本轮保留四项SX×IZ主线，不扩IX交互；C1结构嵌套于SW，但不使用普通缩放df=6卡方直接作边界显著性判断；不根据父模型SE预判交互毫无信息，不用临时SESOI或任意家庭数减参数数的自由度。具体理由和已核实的文献疑点见外部建议裁定。
"""
    (directory/"FOR_WEB_REVIEWERS.md").write_text(feedback,encoding="utf-8")
    readme = f"""# PP-LGCM Round2D：核心调节与资源差异

本目录是Round2C之后的限定执行证据。科学采用以[完整报告](REPORT.md)与[各家族状态](results/family_status.csv)为准。

阅读顺序：

1. [报告](REPORT.md)及[七项意见](SEVEN_ISSUES.csv)。
2. [四Z和资源差异状态](results/family_status.csv)、[合并路径](results/pooled_paths.csv)、[H4对比](results/H4_contrasts.csv)。
3. [正文v49可读文本](manuscripts/main_readable.md)和[附录v41可读文本](manuscripts/appendix_readable.md)；原生DOCX/PDF在同一目录。
4. [模型索引](MODEL_INDEX.md)、[独立复核](evidence/independent_verification.json)及[网页端复核说明](FOR_WEB_REVIEWERS.md)。
5. [包清单](PACKAGE_MANIFEST.json)与[文件清单](FILE_MANIFEST.csv)。所有ZIP请解压到同一目录，不按包划分推断范围。

每包≤25,000,000字节。微观数据、真实PID/FID、逐人得分及MI对象不公开；参数和TECH3聚合保存文件可公开复算。未执行、不可合并和合法但估计不精确的结果均保留，不按显著性删选。历史资料仍可追溯到[Round2C固定提交]({BASE}/tree/63c5eb3bfb7525d4e6dbf4876f0d0a9998c47ef0/round2C_20261007)。

本目录预定不可移动标签为`{TAG}`；发布后的完整提交哈希与匿名回读回执另行提供。
"""
    (directory/"README.md").write_text(readme,encoding="utf-8")
    scope = dict(round="Round2D",preview=args.preview,ready_for_publication=False,
        queue_terminal=terminal,independent_status=audit["status"],
        active_contract_sha256=sha(ROOT/"RUN_CONTRACT.json"),
        latent_families_reportable=sum(m.boolean(state[(z,"D1")]["eligible"]) for z in m.ZN),
        observed_families_reportable=sum(m.boolean(state[(z,"E1")]["eligible"]) for z in m.ZN),
        H4_families_reportable=sum(m.boolean(state[("SD","H4_"+g)]["eligible"]) for g in m.GN),
        remaining_scientific_scope=["window and scale sensitivity","Y shape sensitivity","MI and latent-interaction congeniality","other original hypotheses explicitly marked untested"],
        public_microdata=False,created_at=datetime.now(timezone.utc).isoformat(),
        note="Publication readiness is set only after final document, privacy, package and evidence verification.")
    (directory/"DELIVERY_SCOPE.json").write_text(json.dumps(scope,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(dict(directory=str(directory),preview=args.preview,calls=len(ledger)),ensure_ascii=False))

if __name__ == "__main__":
    main()
