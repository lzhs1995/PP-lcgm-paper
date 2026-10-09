"""按白名单整理公开聚合证据并在本地扫描标识；不会连接或写入GitHub。"""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import csv
import hashlib
import json
import re
import shutil
import zipfile
import fitz

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
MODEL_NAMES = {"model.inp","model.out","receipt.json","input_contract.json","resource_before.json",
    "process.json","mplus_console.log","fit.csv","parameters.csv","parameters_high_precision.csv",
    "parameter_covariance.csv","estimates.dat","tech3.dat","fit_raw.json","tech1.json","tech4.json",
    "local_residuals.json","parameter_gate.json","geometry.json","key_paths.csv","key_printed_comparison.csv",
    "MplusAutomation_readback_error.json","extraction_error.json","key_error.json"}
ALLOWED = {".md",".json",".csv",".txt",".r",".py",".yaml",".yml",".inp",".out",".dat",".log",".pdf",".docx",".png",".svg"}
TOKEN = re.compile(r"(?<![\w.+\-])\d{5,12}(?![\w.])")

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_files(preview):
    pairs = []
    reports = ROOT/("reports_draft" if preview else "reports_final")
    docs = ROOT/"manuscript"/("preview_in_progress" if preview else "delivery")
    for p in reports.iterdir():
        if p.is_file():
            pairs.append((p,p.name))
    for name in ("REVIEW_SYNTHESIS.md","RUN_CONTRACT.json"):
        pairs.append((ROOT/name,"reports/"+name if name.endswith(".md") else name))
    for directory in ("code","results","audit","provenance_SW","tests","evidence"):
        for p in (ROOT/directory).rglob("*"):
            if not p.is_file() or p.suffix.lower() not in ALLOWED or "__pycache__" in p.parts:
                continue
            if p.name == "data.dat" or p.suffix.lower() == ".dat" and p.name not in {"estimates.dat","tech3.dat"}:
                continue
            if any(x.startswith("maintenance_prepared") for x in p.parts):
                continue
            # 保留修订脚本和审阅回执；旧排版预览仅在本地存档，避免与正式v49/v41混读。
            if "preview_in_progress" in p.relative_to(ROOT).parts or p.name.startswith("preview_stale_page_"):
                continue
            pairs.append((p,p.relative_to(ROOT).as_posix()))
    for p in docs.iterdir():
        if p.is_file() and p.suffix.lower() in ALLOWED:
            pairs.append((p,"manuscripts/"+p.name))
    for p in (ROOT/"figures").glob("figure1_sample_flow.*"):
        pairs.append((p,"figures/"+p.name))
    # 只公开实际调用，不把仅准备而未提交的输入混入已执行模型。
    with (reports/"MODEL_EXECUTION.csv").open(encoding="utf-8-sig",newline="") as f:
        calls = list(csv.DictReader(f))
    for call in calls:
        directory = ROOT/call["directory"]
        for p in directory.iterdir():
            if p.is_file() and (p.name in MODEL_NAMES or p.name.startswith("matrix_") and p.suffix == ".csv"):
                pairs.append((p,p.relative_to(ROOT).as_posix()))
    # 接续合同与终态证据均为聚合执行记录；不扩大到整个runtime目录。
    for name in ("queue_terminal.json","execution_limit.json",
                 "postqueue_launch_contract.json","postqueue_native_submit.json",
                 "postqueue_native_first_poll.json","postqueue_waiting_validation.json",
                 "postqueue_waiting_observation.json","postqueue/state.json",
                 "postqueue/upstream_terminal_verified.json",
                 "stage_closeout_20261009/hold_takeover_receipt.json",
                 "stage_closeout_20261009/native_waiting_cancellations.json",
                 "stage_closeout_20261009/native_original_cancellation.json",
                 "stage_closeout_20261009/native_summary_execution.json",
                 "stage_closeout_20261009/native_summary_execution_corrected.json",
                 "stage_closeout_20261009/latest_observation.json"):
        p = ROOT/"runtime"/name
        if p.exists():
            pairs.append((p,"runtime/"+name))
    # 已完成的数据入口与稿件母版绑定不含个人记录。
    for name in ("source.json","document.xml"):
        p = ROOT/"manuscript/source_template"/name
        if p.exists():
            pairs.append((p,"manuscript_source/"+name))
    assert len({target for _,target in pairs}) == len(pairs),"Duplicate public target"
    return pairs

def text_parts(path):
    if path.suffix.lower() == ".docx":
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.endswith((".xml",".rels")):
                    yield name,z.read(name).decode("utf-8",errors="replace")
    elif path.suffix.lower() == ".pdf":
        with fitz.open(path) as doc:
            for i,page in enumerate(doc):
                yield f"page_{i+1}",page.get_text()
    elif path.suffix.lower() not in {".png"}:
        yield "text",path.read_text(encoding="utf-8-sig",errors="replace")

def scan(stage):
    private = read(ROOT/"private/privacy_scan_identifiers.json")
    identifiers = set(private["identifiers"])
    hits,excluded,inventory = [],[],[]
    for p in sorted(stage.rglob("*")):
        if not p.is_file():
            continue
        relative = p.relative_to(stage).as_posix()
        if "private" in p.relative_to(stage).parts or p.name == "data.dat" or p.suffix.lower() in {".rds",".rdata",".dta",".sav",".gh5",".wbk"}:
            excluded.append(relative)
        if p.suffix.lower() == ".dat" and p.name not in {"estimates.dat","tech3.dat"}:
            excluded.append(relative)
        if p.suffix.lower() == ".csv":
            with p.open(encoding="utf-8-sig",newline="") as f:
                headers = next(csv.reader(f),[])
            if set(x.lower().strip() for x in headers)&{"pid","fid","person_id","household_id"}:
                excluded.append(relative)
        for part,value in text_parts(p):
            present = set(TOKEN.findall(value)) & identifiers
            if present:
                hits.append(dict(path=relative,part=part,identifiers=sorted(present)))
        inventory.append(dict(path=relative,bytes=p.stat().st_size,sha256=sha(p)))
    # 命中值只写在private；公共报告只给计数，不输出真实标识。
    (ROOT/"private/public_scan_hits.json").write_text(json.dumps(hits,ensure_ascii=False,indent=2),encoding="utf-8")
    result = dict(status="PASS" if not hits and not excluded else "FAIL",files_scanned=len(inventory),
        exact_identifier_hits=len(hits),prohibited_file_or_column_hits=len(excluded),
        current_cohort_unique_identifier_tokens=len(identifiers),preview="preview" in stage.name,
        procedure="Explicit aggregate file whitelist; exact cohort PID/FID tokens; individual-data formats and identifier columns excluded",
        individual_data_included=False if not excluded else None,
        source_list_sha256=sha(ROOT/"private/privacy_scan_identifiers.json"),created_at=datetime.now(timezone.utc).isoformat())
    (ROOT/"runtime/public_privacy_scan.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    if not hits and not excluded:
        (stage/"evidence/public_privacy_scan.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False),flush=True)
    assert not hits and not excluded,"Publication scan failed; inspect private hit report without publishing identifiers"
    return inventory

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview",action="store_true")
    args = parser.parse_args()
    if not args.preview:
        assert read(ROOT/"runtime/queue_terminal.json")["status"] == "QUEUE_TERMINAL"
        assert read(ROOT/"evidence/independent_verification.json")["status"] == "PASS"
        validation = read(ROOT/"manuscript/delivery/manuscript_validation.json")
        assert validation["status"] in {"PASS_PENDING_VISUAL","PASS"} and not validation["preview"]
        visual = read(ROOT/"manuscript/delivery/visual_review.json")
        assert visual["status"] == "PASS" and not visual["preview"]
        for r in visual["documents"]:
            assert sha(ROOT/"manuscript/delivery"/r["pdf"]) == r["pdf_sha256"]
    stage = ROOT/("public_stage_preview" if args.preview else "public_stage")
    if stage.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        archive = ROOT/"runtime/stage_archives"/(stage.name+"_"+stamp)
        archive.parent.mkdir(exist_ok=True,parents=True)
        stage.rename(archive)
    stage.mkdir()
    pairs = source_files(args.preview)
    for source,relative in pairs:
        target = stage/relative
        target.parent.mkdir(exist_ok=True,parents=True)
        shutil.copy2(source,target)
        assert sha(source) == sha(target)
        if target.suffix in {".inp",".out"}:
            target.with_suffix(target.suffix+".txt").write_bytes(target.read_bytes())
    (stage/".gitattributes").write_bytes(b"* -text\n")
    scope = read(stage/"DELIVERY_SCOPE.json")
    scope["ready_for_publication"] = not args.preview
    scope["publication_checks"] = "All attempted models have verified terminal dispositions; stage-document gates passed; this is not acceptance of failed models or completion of all hypotheses. Privacy scan must also pass."
    (stage/"DELIVERY_SCOPE.json").write_text(json.dumps(scope,ensure_ascii=False,indent=2),encoding="utf-8")
    inventory = scan(stage)
    with (ROOT/"runtime/public_scan_file_hashes.csv").open("w",encoding="utf-8",newline="") as f:
        writer = csv.DictWriter(f,fieldnames=["path","bytes","sha256"])
        writer.writeheader();writer.writerows(inventory)
    print("STAGED",stage,len(inventory),flush=True)

if __name__ == "__main__":
    main()
