"""只读验证公开包和发布阻断条件；不创建提交或写入远端。"""
from pathlib import Path
import importlib.util
import json

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
loader = importlib.util.spec_from_file_location("publish", ROOT / "code/23_publish_github.py")
publish = importlib.util.module_from_spec(loader)
loader.loader.exec_module(publish)

results = []
stage = ROOT / "public_stage_preview"
count = publish.verify_packages(stage, publish.read(stage / "PACKAGE_MANIFEST.json"))
results.append(dict(check="actual_preview_archive_integrity", passed=True, payload_files=count))

for path in ("../data.dat", "/data.dat", "C:/data.dat", "x/../../data.dat", "x\\data.dat"):
    try:
        publish.safe_name(path)
    except AssertionError:
        results.append(dict(check="reject_unsafe_archive_path", path=path, passed=True))
    else:
        raise AssertionError("Unsafe archive path accepted")

# check先读取真实origin，但绝不commit/push；当前回执必须是预演，故应被阻断。
assert publish.read(ROOT / "runtime/package_validation.json")["preview"] is True
try:
    publish.check()
except AssertionError as error:
    assert "Only final packages" in str(error)
    results.append(dict(check="preview_cannot_publish", passed=True, reason=str(error)))
else:
    raise AssertionError("Preview unexpectedly passed final publication gate")

report = dict(status="PASS", checks=results, remote_mutations=0, local_git_mutations=0,
              final_publication_verified=False)
dest = ROOT / "tests/publication_validation.json"
dest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False), flush=True)
