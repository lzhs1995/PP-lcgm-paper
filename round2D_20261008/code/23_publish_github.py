"""发布已经终态验收的Round2D，并从匿名远端下载资料包重新核验。

check只读；commit创建本地提交；push发布至用户指定仓库；verify匿名回读。
任何预览、未终态模型或未完成的稿件验收均不能进入commit/push。
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import io
import json
import shutil
import subprocess
import sys
import zipfile

import requests

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
STAGE = ROOT / "public_stage"
REPO = Path("C:/Users/LZHS/Desktop/cnm/tasks/01_R_analysis/work/cfps_review_20261005/github_publish")
GIT = "C:/Program Files/Git/cmd/git.exe"
PREFIX = "round2D_20261008"
TAG = "review-round2D-20261008"
REMOTE = "lzhs1995/PP-lcgm-paper"
LIMIT = 25_000_000


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, obj):
    dest = ROOT / "runtime" / name
    dest.parent.mkdir(exist_ok=True, parents=True)
    dest.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def git(*args):
    run = subprocess.run([GIT, "-C", str(REPO), *args], capture_output=True)
    if run.returncode:
        raise RuntimeError(run.stderr.decode("utf-8", errors="replace"))
    return run.stdout


def check_origin():
    origin = git("remote", "get-url", "origin").decode().strip().lower().rstrip("/").removesuffix(".git")
    assert origin in {"https://github.com/" + REMOTE.lower(), "git@github.com:" + REMOTE.lower()}, "Unauthorized remote"


def read_refs():
    return {line.split()[1]: line.split()[0] for line in
            git("ls-remote", "origin", "refs/heads/main", "refs/tags/" + TAG).decode().splitlines()}


def safe_name(name):
    assert not name.startswith(("/", "\\")) and "\\" not in name
    assert ".." not in name.split("/") and ":" not in name, "Unsafe archive path"
    return name


def verify_payload(stage):
    """对最终或解压快照执行逐文件哈希与镜像核对；不修改快照。"""
    with (stage / "FILE_MANIFEST.csv").open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == len({r["path"] for r in rows}), "Duplicate manifest paths"
    for row in rows:
        path = stage / safe_name(row["path"])
        assert path.is_file() and path.stat().st_size == int(row["bytes"]), row["path"]
        assert sha(path) == row["sha256"], row["path"]
        if path.suffix in {".inp", ".out"}:
            assert path.read_bytes() == path.with_suffix(path.suffix + ".txt").read_bytes(), row["path"]
    return rows


def verify_packages(stage, package_manifest):
    expected = {r["path"]: r for r in verify_payload(stage)}
    expected["FILE_MANIFEST.csv"] = {"bytes": (stage / "FILE_MANIFEST.csv").stat().st_size,
                                     "sha256": sha(stage / "FILE_MANIFEST.csv")}
    seen = set()
    for item in package_manifest["packages"]:
        archive = stage / safe_name(item["path"])
        assert archive.stat().st_size == item["bytes"] <= LIMIT
        assert sha(archive) == item["sha256"]
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None and len(z.namelist()) == item["files"]
            for name in z.namelist():
                safe_name(name)
                assert name not in seen and name in expected, name
                data = z.read(name)
                assert len(data) == int(expected[name]["bytes"])
                assert hashlib.sha256(data).hexdigest() == expected[name]["sha256"], name
                seen.add(name)
    assert seen == set(expected), "Archive coverage mismatch"
    allowed = seen | {"PACKAGE_MANIFEST.json"} | {p["path"] for p in package_manifest["packages"]}
    actual = {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()}
    assert actual == allowed, "Unmanifested staged files"
    return len(seen)


def check():
    check_origin()
    package = read(ROOT / "runtime/package_validation.json")
    assert package["status"] == "PASS" and package["preview"] is False, "Only final packages can be published"
    assert Path(package["stage"]) == STAGE
    assert sha(STAGE / "PACKAGE_MANIFEST.json") == package["package_manifest_sha256"]
    scope = read(STAGE / "DELIVERY_SCOPE.json")
    assert scope["preview"] is False and scope["ready_for_publication"] is True
    assert scope["public_microdata"] is False and scope["independent_status"] == "PASS"
    assert read(STAGE / "runtime/queue_terminal.json")["status"] == "QUEUE_TERMINAL"
    assert read(STAGE / "results/SUMMARY.json")["status"] == "SUMMARIZED"
    assert read(STAGE / "evidence/independent_verification.json")["status"] == "PASS"
    stage_check = read(STAGE / "evidence/stage_release_verification.json")
    assert stage_check["status"] == "PASS" and stage_check["scientific_project_complete"] is False
    assert scope["release_type"] == "PARTIAL_RESEARCH_STAGE_FOR_EXTERNAL_REVIEW"
    privacy = read(STAGE / "evidence/public_privacy_scan.json")
    assert privacy["status"] == "PASS" and privacy["preview"] is False
    visual = read(STAGE / "manuscripts/visual_review.json")
    assert visual["status"] == "PASS" and visual["preview"] is False
    for document in visual["documents"]:
        assert sha(STAGE / "manuscripts" / document["pdf"]) == document["pdf_sha256"]
    count = verify_packages(STAGE, read(STAGE / "PACKAGE_MANIFEST.json"))
    result = dict(status="PASS", files_in_packages=count, package_count=len(package["packages"]),
                  package_manifest_sha256=package["package_manifest_sha256"],
                  checked_at=datetime.now(timezone.utc).isoformat())
    save("github_publication_preflight.json", result)
    print(json.dumps(result), flush=True)
    return result


def prepare_commit():
    checked = check()
    receipt = ROOT / "runtime/github_local_commit.json"
    if receipt.exists():
        existing = read(receipt)
        assert existing["package_manifest_sha256"] == checked["package_manifest_sha256"]
        assert git("rev-parse", "HEAD").decode().strip() == existing["commit"]
        assert git("rev-parse", TAG).decode().strip() == existing["commit"]
        assert not git("status", "--porcelain").strip()
        print("REUSE_LOCAL_COMMIT", existing["commit"], flush=True)
        return
    refs = read_refs()
    head = git("rev-parse", "HEAD").decode().strip()
    assert git("branch", "--show-current").decode().strip() == "main"
    assert refs["refs/heads/main"] == head, "Remote advanced: reconcile before publication"
    assert "refs/tags/" + TAG not in refs, "Release tag already exists"
    assert not git("status", "--porcelain").strip(), "Unrelated local changes require review"
    dest = REPO / PREFIX
    assert not dest.exists(), "Target directory already exists; inspect recovery state"
    save("github_prepare_started.json", dict(previous=head, tag=TAG, prefix=PREFIX, **checked))
    shutil.copytree(STAGE, dest)
    readme = REPO / "README.md"
    old_readme = readme.read_bytes()
    (ROOT / "runtime/repository_README_before_round2D.md").write_bytes(old_readme)
    notice = (f"最新阶段资料：[PP-LGCM Round2D成果与未竟问题（2026-10-09收口）]({PREFIX}/README.md)。"
              "潜调节未形成可合并结果，观测替代与H4延期；当前成果、失败证据及网页端评议问题均已列明，历史材料保留。\n\n")
    readme.write_bytes(notice.encode("utf-8") + old_readme)
    expected = {p.relative_to(REPO).as_posix() for p in dest.rglob("*") if p.is_file()} | {"README.md"}
    git("-c", "core.autocrlf=false", "add", "-f", "--", PREFIX, "README.md")
    changed = set(filter(None, git("diff", "--cached", "--name-only", "-z").decode().split("\0")))
    assert changed == expected, "Unexpected staged changes"
    blobs = {}
    for item in git("ls-files", "--stage", "-z").split(b"\0"):
        if item:
            header, path = item.split(b"\t", 1)
            blobs[path.decode()] = header.decode().split()[1]
    for name in changed:
        data = (REPO / name).read_bytes()
        assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == blobs[name]
    name, email = git("show", "-s", "--format=%an%n%ae", head).decode().strip().splitlines()
    git("-c", f"user.name={name}", "-c", f"user.email={email}", "commit", "-m",
        "Publish PP-LGCM Round 2D moderation evidence and manuscript review package")
    commit = git("rev-parse", "HEAD").decode().strip()
    git("tag", TAG, commit)
    save("github_local_commit.json", dict(commit=commit, tag=TAG, previous=head,
        files=len(changed), package_manifest_sha256=checked["package_manifest_sha256"]))
    print("LOCAL_COMMIT", commit, flush=True)


def push():
    check()
    record = read(ROOT / "runtime/github_local_commit.json")
    commit = record["commit"]
    assert git("rev-parse", "HEAD").decode().strip() == commit
    assert git("rev-parse", TAG).decode().strip() == commit
    assert not git("status", "--porcelain").strip()
    refs = read_refs()
    assert refs["refs/heads/main"] in {record["previous"], commit}, "Remote changed; no force push"
    assert refs.get("refs/tags/" + TAG, commit) == commit
    helper = '!"C:/Program Files/GitHub CLI/gh.exe" auth git-credential'
    git("-c", "credential.helper=", "-c", f"credential.helper={helper}", "push", "--atomic", "origin",
        f"{commit}:refs/heads/main", f"refs/tags/{TAG}:refs/tags/{TAG}")
    save("github_push_receipt.json", dict(status="PUSHED", **record, utc=datetime.now(timezone.utc).isoformat()))
    print("PUSHED", commit, flush=True)


def verify():
    check_origin()
    record = read(ROOT / "runtime/github_local_commit.json")
    commit = record["commit"]
    refs = read_refs()
    assert refs["refs/heads/main"] == refs["refs/tags/" + TAG] == commit
    session = requests.Session()
    session.trust_env = False
    session.headers["User-Agent"] = "PP-LGCM-anonymous-evidence-verification"
    response = session.get(f"https://api.github.com/repos/{REMOTE}/git/trees/{commit}?recursive=1", timeout=60)
    response.raise_for_status()
    tree = response.json()
    assert not tree.get("truncated")
    remote = {r["path"]: r["sha"] for r in tree["tree"] if r["type"] == "blob"}
    local = {}
    for item in git("ls-tree", "-r", "-z", commit).split(b"\0"):
        if item:
            header, path = item.split(b"\t", 1)
            local[path.decode()] = header.decode().split()[2]
    assert remote == local, "Remote tree differs from published commit"
    package = read(REPO / PREFIX / "PACKAGE_MANIFEST.json")
    selected = ["README.md"] + [PREFIX + "/" + name for name in [
        "README.md", "REPORT.md", "STAGE_SUMMARY.md", "FOR_WEB_REVIEWERS.md", "DELIVERY_SCOPE.json", "SEVEN_ISSUES.csv",
        "TARGET_DISPOSITIONS.csv", "PERFORMANCE_FINAL.csv", "DEFERRED_ADDITIONAL_WORK.csv",
        "MODEL_INDEX.md", "HYPOTHESES.csv", "FILE_MANIFEST.csv", "PACKAGE_MANIFEST.json",
        "results/family_status.csv", "results/pooled_paths.csv", "results/conditional_slopes.csv",
        "results/H4_contrasts.csv", "results/H4_direction_decisions.csv",
        "evidence/independent_verification.json", "manuscripts/main_readable.md",
        "manuscripts/appendix_readable.md"] + [p["path"] for p in package["packages"]]]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    download = ROOT / "runtime/github_anonymous_download" / stamp
    download.mkdir(parents=True)
    checked, extracted = [], set()
    for name in selected:
        response = session.get(f"https://raw.githubusercontent.com/{REMOTE}/{commit}/{name}", timeout=60)
        response.raise_for_status()
        data = response.content
        digest = hashlib.sha256(data).hexdigest()
        assert digest == sha(REPO / name), name
        checked.append(dict(path=name, bytes=len(data), sha256=digest))
        if name.endswith(".zip"):
            assert len(data) <= LIMIT
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                assert z.testzip() is None
                for member in z.namelist():
                    safe_name(member)
                    assert member not in extracted, member
                    target = download / member
                    target.parent.mkdir(exist_ok=True, parents=True)
                    target.write_bytes(z.read(member))
                    extracted.add(member)
        print("ANONYMOUS_READBACK_PASS", name, flush=True)
    rows = verify_payload(download)
    assert extracted == {r["path"] for r in rows} | {"FILE_MANIFEST.csv"}
    evidence = download.parent / (stamp + "_recalculation")
    run = subprocess.run([sys.executable, "-X", "utf8", str(download / "code/09_independent_verify.py"),
                          "--root", str(download), "--require-terminal", "--evidence-output", str(evidence)],
                         capture_output=True)
    save("github_download_recalculation_process.json", dict(exitcode=run.returncode,
        stdout=run.stdout.decode("utf-8", errors="replace"), stderr=run.stderr.decode("utf-8", errors="replace")))
    assert run.returncode == 0, "Downloaded aggregate recalculation failed"
    recalculated = read(evidence / "independent_verification.json")
    assert recalculated["status"] == "PASS"
    stage_run = subprocess.run([sys.executable, "-X", "utf8", str(download / "code/37_verify_stage_release.py"),
                              "--root", str(download), "--evidence-output", str(evidence)],capture_output=True)
    save("github_download_stage_recalculation_process.json", dict(exitcode=stage_run.returncode,
        stdout=stage_run.stdout.decode("utf-8", errors="replace"), stderr=stage_run.stderr.decode("utf-8", errors="replace")))
    assert stage_run.returncode == 0, "Downloaded stage-status recalculation failed"
    stage_recalculated = read(evidence / "stage_release_verification.json")
    assert stage_recalculated["status"] == "PASS"
    result = dict(status="PASS", commit=commit, tag=TAG, anonymous=True,
        git_blobs_verified=len(remote), files=checked, extracted_payload_files=len(extracted),
        package_CRC="PASS", per_file_download_hashes="PASS", downloaded_aggregate_recalculation=recalculated,
        downloaded_stage_recalculation=stage_recalculated,
        download_directory=str(download), utc=datetime.now(timezone.utc).isoformat())
    save("github_anonymous_readback.json", result)
    print("ANONYMOUS_VERIFICATION_PASS", commit, len(extracted), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("check", "commit", "push", "verify"))
    action = parser.parse_args().action
    {"check": check, "commit": prepare_commit, "push": push, "verify": verify}[action]()
