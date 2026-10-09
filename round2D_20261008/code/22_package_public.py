"""按压缩后体积拆成独立ZIP，每包严格不超过25,000,000字节并逐文件回验。"""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import csv
import hashlib
import json
import zipfile
import zlib

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
LIMIT = 25_000_000

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview",action="store_true")
    args = parser.parse_args()
    stage = ROOT/("public_stage_preview" if args.preview else "public_stage")
    scan = json.loads((ROOT/"runtime/public_privacy_scan.json").read_text(encoding="utf-8"))
    assert scan["status"] == "PASS" and scan["preview"] == args.preview
    scope = json.loads((stage/"DELIVERY_SCOPE.json").read_text(encoding="utf-8"))
    assert scope["preview"] == args.preview and (args.preview or scope["ready_for_publication"])
    assert not (stage/"packages").exists(),"A staged snapshot is immutable once packaged; rebuild a fresh stage for changes"
    with (ROOT/"runtime/public_scan_file_hashes.csv").open(encoding="utf-8",newline="") as f:
        checked = list(csv.DictReader(f))
    for r in checked:
        p = stage/r["path"]
        assert p.stat().st_size == int(r["bytes"]) and sha(p) == r["sha256"],r["path"]
    actual = {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()}
    assert actual == {r["path"] for r in checked}|{"evidence/public_privacy_scan.json"}
    paths = sorted(p for p in stage.rglob("*") if p.is_file())
    manifest = [dict(path=p.relative_to(stage).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in paths]
    with (stage/"FILE_MANIFEST.csv").open("w",encoding="utf-8",newline="") as f:
        w = csv.DictWriter(f,fieldnames=["path","bytes","sha256"])
        w.writeheader();w.writerows(manifest)
    paths.append(stage/"FILE_MANIFEST.csv")
    expected = {p.relative_to(stage).as_posix():sha(p) for p in paths}
    grouped = {"01_reports_manuscripts":[],"02_models_code":[]}
    for p in sorted(paths):
        rel = p.relative_to(stage).as_posix()
        group = "02_models_code" if rel.startswith(("models/","code/","tests/","provenance_SW/")) else "01_reports_manuscripts"
        grouped[group].append(p)
    (stage/"packages").mkdir()
    packages,all_archived = [],[]
    def write_batch(group,index,batch):
        dest = stage/"packages"/f"{group}_{index:02d}.zip"
        with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for p in batch:
                name = p.relative_to(stage).as_posix()
                info = zipfile.ZipInfo(name,date_time=(2026,10,8,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                z.writestr(info,p.read_bytes(),compresslevel=6)
        assert dest.stat().st_size <= LIMIT,dest
        with zipfile.ZipFile(dest) as z:
            assert z.testzip() is None
            assert len(set(z.namelist())) == len(batch)
            for name in z.namelist():
                assert not name.startswith(("/","\\")) and ".." not in Path(name).parts
                assert hashlib.sha256(z.read(name)).hexdigest() == expected[name],name
                all_archived.append(name)
        receipt = dict(path=dest.relative_to(stage).as_posix(),bytes=dest.stat().st_size,files=len(batch),
                       sha256=sha(dest),CRC="PASS",decompressed_file_hashes="PASS")
        packages.append(receipt)
        print(json.dumps(receipt),flush=True)
    for group,items in grouped.items():
        batch,index,size = [],1,22
        for p in items:
            data = p.read_bytes()
            comp = zlib.compressobj(level=6,wbits=-15)
            packed = comp.compress(data)+comp.flush()
            cost = len(packed)+76+2*len(p.relative_to(stage).as_posix().encode("utf-8"))+128
            assert cost < LIMIT-1000,"One aggregate file exceeds ZIP limit; split with a recorded reconstruction map"
            if batch and size+cost > LIMIT-1000:
                write_batch(group,index,batch)
                batch,index,size = [],index+1,22
            batch.append(p);size += cost
        if batch:
            write_batch(group,index,batch)
    assert len(all_archived) == len(set(all_archived)) == len(expected)
    assert set(all_archived) == set(expected)
    report = dict(limit_bytes=LIMIT,preview=args.preview,packages=packages,
        files_in_internal_manifest=len(manifest),unique_files_in_packages=len(all_archived),
        manifest_excludes_itself=True,packages_extract_into_one_directory=True,public_microdata=False,
        note="FILE_MANIFEST lists payload files except itself; PACKAGE_MANIFEST and ZIP files are external manifests/artifacts, not recursively included.",
        created_at=datetime.now(timezone.utc).isoformat())
    (stage/"PACKAGE_MANIFEST.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    validation = dict(status="PASS",stage=str(stage),package_manifest_sha256=sha(stage/"PACKAGE_MANIFEST.json"),**report)
    (ROOT/"runtime/package_validation.json").write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PACKAGE_VALIDATION_PASS",len(packages),max(r["bytes"] for r in packages),flush=True)

if __name__ == "__main__":
    main()
