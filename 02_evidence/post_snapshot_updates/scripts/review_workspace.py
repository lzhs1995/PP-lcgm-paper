"""七项审阅意见续接：隔离证据、版本对照和审计包，不修改研究源文件。"""
from pathlib import Path
import csv
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from lxml import etree

PROJECT = Path(r"C:\Users\LZHS\Desktop\cnm\tasks\01_R_analysis")
PRIOR = Path(r"C:\Users\LZHS\pp_lgcm_runs\20260908_parallel\recovery\20261001_pp_lgcm_reconciliation\10_resume_verified_20261001")
Q = PRIOR / "scientific_followup/measurement_audit"
OUT = Path(r"C:\Users\LZHS\pp_lgcm_review\20261005")
MAIN = PRIOR / "revision_v42_variance_sign_correction/PP_LGCM_variance_sign_candidate_NOT_RELEASED.docx"
APP = PRIOR / "revision_v36_appendix_cesd_candidate/PP_LGCM_appendix_cesd_candidate_NOT_RELEASED.docx"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

def sha(p):
    with Path(p).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def readj(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))

def writej(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def csvout(p, rows):
    rows = list(rows)
    if not rows:
        raise ValueError(f"拒绝把空表记为完成: {p}")
    fields = list(dict.fromkeys(k for row in rows for k in row))
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with Path(p).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def paragraphs(path):
    with zipfile.ZipFile(path) as z:
        doc = etree.fromstring(z.read("word/document.xml"))
    return ["".join(p.xpath(".//w:t/text()", namespaces=NS)) for p in doc.xpath("//w:p", namespaces=NS)]

def init():
    OUT.mkdir(parents=True, exist_ok=True)
    baseline = OUT / "baseline_manifest.json"
    if baseline.exists():
        for row in readj(baseline)["files"]:
            if sha(row["path"]) != row["sha256"]:
                raise RuntimeError(f"基线文件发生变化: {row['path']}")
        print("复用已建立的隔离工作区", OUT)
        return
    original = Path(r"C:\Users\LZHS\OneDrive\20251026 PP-LGCM整合\20260214 附件")
    files = [MAIN, APP] + sorted(original.glob("*.docx"))
    files += sorted(Path(r"C:\Users\LZHS\Desktop\interge_rela").glob("*closeness&depression*.R"))
    files += [PROJECT / "reports/cfps_full_docx_provenance_20261005/manifest.json", PROJECT / "reports/cfps_full_docx_provenance_20261005/validation.json"]
    writej(baseline, {"created_utc": datetime.now(timezone.utc).isoformat(), "original_session": "01a08137-c69d-7ff3-95f6-435b2f63e144", "files": [{"path": str(p), "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]})
    for folder in ["audit_stage1", "summaries", "native", "source_evidence", "manuscript", "analysis", "reviews"]:
        (OUT / folder).mkdir(exist_ok=True)
    for name in ["Astra_LGCM_Audit_Package_Instructions..md", "给astra的打包清单_v2..md"]:
        source = Path(r"C:\Users\LZHS\Downloads") / name
        shutil.copy2(source, OUT / "source_evidence" / name)
    for label, path in [("main_v42", MAIN), ("appendix_v36", APP)]:
        csvout(OUT / f"{label}_paragraphs.csv", [{"paragraph_index": n, "text": t} for n, t in enumerate(paragraphs(path)) if t])
    writej(OUT / "state.json", {"stage": "BASELINE_ESTABLISHED", "updated_at": datetime.now(timezone.utc).isoformat(), "cfps_historical_reproduction": "COMPLETE", "charls": "PAUSED_BY_USER", "primary_scale": "CESD8", "sensitivity_scale": "CESD20sc", "new_mplus": 0, "manuscript_release": False})
    print(json.dumps({"output_root": str(OUT), "baseline_files": len(files), "baseline_verified": True}, ensure_ascii=False))

def inspect():
    for file in [PROJECT / "reports/cfps_full_docx_provenance_20261005/manifest.json", Q / "corrected_raw_results_20261002/summary.json", Q / "cesd2012_scoring.json", Q / "corrected_first_stage_v2/preparation_manifest.json"]:
        if not file.exists():
            print(file.name, "不存在")
            continue
        obj = readj(file)
        print(file.name, list(obj) if isinstance(obj, dict) else type(obj).__name__)
        if "scoring" not in file.name:
            print(json.dumps(obj, ensure_ascii=False)[:1800])
    print("已有关联与调节证据")
    for p in sorted((PRIOR / "scientific_followup").iterdir()):
        print(p.name)

if __name__ == "__main__":
    {"init": init, "inspect": inspect}[sys.argv[1]]()
