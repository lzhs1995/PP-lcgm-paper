"""用独立Word实例导出当前稿件，保留用户其他实例；不刷新Zotero或改写DOCX。"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import pythoncom
import win32com.client
import win32process

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    directory = ROOT/"manuscript"/("preview_in_progress" if args.preview else "delivery")
    built = json.loads((directory/"build_status.json").read_text(encoding="utf-8"))
    assert built["preview"] is args.preview
    records = []
    app = None
    pythoncom.CoInitialize()
    try:
        app = win32com.client.DispatchEx("Word.Application")
        if app.Documents.Count:
            app = None
            raise RuntimeError("Word routed to an instance containing existing documents; preserved")
        app.Visible = False
        app.DisplayAlerts = 0
        # 仅记录自己的实例；不按进程名结束任何Word进程。
        own_pid = None
        for stem in ("PP_LGCM_review_v49_round2D", "PP_LGCM_appendix_review_v41_round2D"):
            src = directory/(stem+".docx")
            dst = src.with_suffix(".pdf")
            source_hash = digest(src)
            print("OPEN",src.name,flush=True)
            doc = app.Documents.Open(str(src),ReadOnly=True,AddToRecentFiles=False,ConfirmConversions=False)
            try:
                try:
                    own_pid = win32process.GetWindowThreadProcessId(doc.ActiveWindow.Hwnd)[1]
                except (AttributeError, pythoncom.com_error):
                    own_pid = None
                doc.Repaginate()
                pages = int(doc.ComputeStatistics(2))
                doc.ExportAsFixedFormat(str(dst),17)
                record = dict(document=src.name,pdf=dst.name,pages=pages,
                    fields=int(doc.Fields.Count),footnotes=int(doc.Footnotes.Count),
                    tables=int(doc.Tables.Count),revisions=int(doc.Revisions.Count),
                    Word_version=str(app.Version),Word_instance_pid=own_pid,
                    docx_sha256=source_hash,pdf_sha256=digest(dst),
                    exported_at=datetime.now(timezone.utc).isoformat(),preview=args.preview,
                    export="NATIVE_WORD",Zotero_refresh="NOT_PERFORMED",visual_review="PENDING")
                assert digest(src) == source_hash
                records.append(record)
                (directory/"native_word_export.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
                print(json.dumps(record,ensure_ascii=False),flush=True)
            finally:
                doc.Close(False)
    finally:
        if app is not None:
            app.Quit()
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    main()
