"""原worker在维护等待时归档控制台与未提交输入；不结束任何进程。

inspect可在估计期间运行。capture要求Mplus已结束、原worker已进入维护等待；
prepare要求调用者已经通过原生ClaudeR取消该等待worker。随后才可恢复06_queue.R。
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json
import shutil
import psutil

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
BASE = ROOT / "models/SD/D1_Z0_MI01/base"
JOB = "8d074cab"
WORKER = 9180
PARENT = 26032


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    path = ROOT / "runtime" / name
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def inspect():
    progress = read(ROOT / "runtime/progress.json")
    models = [p.info for p in psutil.process_iter(["pid", "name", "create_time", "ppid"])
              if "mplus" in (p.info["name"] or "").lower()]
    worker = None
    if psutil.pid_exists(WORKER):
        process = psutil.Process(WORKER)
        worker = dict(pid=process.pid, name=process.name(), created=process.create_time(),
                      ancestor_pids=[p.pid for p in process.parents()])
    value = dict(job_id=JOB, progress=progress, Mplus_processes=models, old_worker=worker,
                 maintenance_hold=(ROOT / "runtime/PAUSE_FOR_CODE_UPDATE").exists(),
                 base_has_terminal_receipt=(BASE / "receipt.json").exists(),
                 utc=datetime.now(timezone.utc).isoformat(), action="READ_ONLY_NO_PROCESS_CHANGE")
    save("maintenance_inspection.json", value)
    print(json.dumps(value, ensure_ascii=False), flush=True)
    return value


def capture():
    value = inspect()
    assert value["maintenance_hold"] and value["base_has_terminal_receipt"]
    assert not value["Mplus_processes"], "Mplus still active; do not stop or replace it"
    assert value["progress"]["stage"] == "resource_wait" and value["progress"]["pid"] == WORKER
    assert value["old_worker"] and PARENT in value["old_worker"]["ancestor_pids"]
    with (ROOT / "audit/CALL_REGISTER.csv").open(encoding="utf-8-sig", newline="") as f:
        calls = list(csv.DictReader(f))
    assert calls[-1]["id"] == "SD_D1_Z0_1_base", "Another model has executed; inspect console ownership"
    receipt = read(BASE / "receipt.json")
    assert sha(BASE / "model.out") == receipt["output_sha256"]
    source = Path("C:/Users/LZHS/Documents/mplus_console.log")
    target = BASE / "mplus_console.log"
    if target.exists():
        assert sha(target) == sha(source)
    else:
        shutil.copy2(source, target)
    assert sha(source) == sha(target)
    save("maintenance_capture.json", dict(job_id=JOB, worker=value["old_worker"],
        source_console=str(source), console_sha256=sha(target), base_receipt=receipt,
        captured_at=datetime.now(timezone.utc).isoformat(),
        note="Current model terminated naturally or under its existing time limit; next launch held before registration"))
    print("MAINTENANCE_CAPTURED_CANCEL_ONLY_WAITING_JOB", JOB, flush=True)


def prepare():
    capture_record = read(ROOT / "runtime/maintenance_capture.json")
    assert capture_record["job_id"] == JOB
    value = inspect()
    assert not value["Mplus_processes"] and value["maintenance_hold"]
    worker = value["old_worker"]
    assert worker is None or worker["created"] != capture_record["worker"]["created"], "Original waiting worker still exists"
    assert sha(BASE / "mplus_console.log") == capture_record["console_sha256"]
    assert sha(BASE / "model.out") == capture_record["base_receipt"]["output_sha256"]
    with (ROOT / "audit/CALL_REGISTER.csv").open(encoding="utf-8-sig", newline="") as f:
        registered = {r["id"] for r in csv.DictReader(f)}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    archive = ROOT / "audit" / ("maintenance_prepared_" + stamp)
    archived = []
    for config in sorted((ROOT / "models").glob("*/*/*/input_contract.json")):
        row = read(config)
        if row["id"] in registered:
            continue
        directory = config.parent
        assert not any((directory / name).exists() for name in ("model.out", "process.json", "receipt.json"))
        target = archive / directory.relative_to(ROOT / "models")
        target.parent.mkdir(parents=True, exist_ok=True)
        archived.append(dict(id=row["id"], old_directory=str(directory), archive=str(target),
                             input_sha256=sha(directory / "model.inp"),
                             reason="Prepared by old in-memory code; never registered or executed"))
        directory.rename(target)
    reopened = None
    family = ROOT / "results/SD_D1_family.json"
    receipt = read(BASE / "receipt.json")
    hint = "OPTION ALGORITHM=EM" in (BASE / "mplus_console.log").read_text(encoding="utf-8", errors="replace")
    if family.exists() and receipt["status"] in {"TIMEOUT", "NOT_CONVERGED"} and hint:
        previous = read(family)
        assert previous["eligible"] is False
        attempted = [m for m in previous["members"] if m["status"] != "NOT_RUN"]
        assert len(attempted) == 1 and attempted[0]["attempt"] == "base"
        target = ROOT / "audit" / ("SD_D1_pre_optimizer_repair_" + stamp + ".json")
        shutil.copy2(family, target)
        assert sha(family) == sha(target)
        family.unlink()
        reopened = dict(archived_cache=str(target),
            reason="Old worker did not contain registered EM repair; reuse terminal base receipt and trigger one existing-budget repair")
    hold = ROOT / "runtime/PAUSE_FOR_CODE_UPDATE"
    hold_archive = ROOT / "runtime" / ("maintenance_hold_completed_" + stamp + ".txt")
    hold.rename(hold_archive)
    result = dict(status="READY_FOR_NATIVE_RESUME", previous_job_id=JOB, prepared_inputs_archived=archived,
                  family_reopened=reopened, base_model_reestimated=False, processes_terminated_by_script=0,
                  active_engine_sha256=sha(ROOT / "code/03_engine.R"),
                  active_queue_sha256=sha(ROOT / "code/06_queue.R"), completed_at=datetime.now(timezone.utc).isoformat())
    save("maintenance_resume_ready.json", result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("inspect", "capture", "prepare"))
    action = parser.parse_args().action
    {"inspect": inspect, "capture": capture, "prepare": prepare}[action]()
