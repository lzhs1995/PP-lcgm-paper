"""核对实际EM修复只改变算法；读取已保存输入，不运行或中止任何模型。"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_input(path):
    # 仅消去本次尝试名称和明确允许的EM选项，剩余字节必须相同。
    value = path.read_text(encoding="utf-8-sig")
    assert value.count("ALGORITHM=INTEGRATION") == 1, path
    value, n = re.subn(r"\ATITLE:.*?(?=^DATA:)", "TITLE: ignored attempt name\n", value,
                      flags=re.M | re.S)
    assert n == 1, path
    return value.replace("ALGORITHM=INTEGRATION EM;", "ALGORITHM=INTEGRATION;")


def main():
    records = []
    for note in sorted((ROOT / "audit").glob("*_optimizer_repair.json")):
        definition = json.loads(note.read_text(encoding="utf-8-sig"))
        # 维护记录按既定Z0队列命名；从真实input_contract绑定，避免依赖目录猜测。
        candidates = []
        for saved in (ROOT / "models" / definition["z"]).glob("*/repair_em/input_contract.json"):
            contract = json.loads(saved.read_text(encoding="utf-8-sig"))
            if contract["spec"] == definition["spec"] and contract["member"] == definition["member"]:
                candidates.append((saved.parent, contract))
        assert len(candidates) == 1, (note.name, len(candidates))
        repaired, target_contract = candidates[0]
        source = repaired.parent / definition["source_attempt"]
        source_contract = json.loads((source / "input_contract.json").read_text(encoding="utf-8-sig"))
        assert sha(source / "model.out") == definition["source_output_sha256"]
        assert sha(source / "mplus_console.log") == definition["console_sha256"]
        assert "OPTION ALGORITHM=EM" in (source / "mplus_console.log").read_text(errors="replace")
        assert target_contract["settings"]["optimizer"] == "EM"
        target_settings = {k: v for k, v in target_contract["settings"].items() if k != "optimizer"}
        assert target_settings == source_contract["settings"]
        assert source_contract["data_sha256"] == target_contract["data_sha256"]
        assert sha(source / "data.dat") == sha(repaired / "data.dat") == source_contract["data_sha256"]
        assert normalized_input(source / "model.inp") == normalized_input(repaired / "model.inp")
        records.append(dict(
            id=target_contract["id"], source_id=source_contract["id"],
            source_input_sha256=sha(source / "model.inp"),
            repaired_input_sha256=sha(repaired / "model.inp"),
            data_sha256=target_contract["data_sha256"],
            settings_unchanged_except_optimizer=True,
            model_and_all_other_input_unchanged=True,
            source_status=json.loads((source / "receipt.json").read_text(encoding="utf-8-sig"))["status"],
        ))
    assert records, "No actual optimizer repair available for verification"
    report = dict(status="PASS", checked_at=datetime.now(timezone.utc).isoformat(),
                  repairs=records, new_Mplus_calls=0,
                  scope="Input identity only; does not establish convergence or model admissibility")
    path = ROOT / "audit/optimizer_input_verification.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
