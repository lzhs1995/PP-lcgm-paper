from pathlib import Path
import json, csv
R = Path(__file__).resolve().parents[1]
forbidden = [p for p in R.rglob("*") if p.is_file() and (p.name.lower() in {"data.dat", "auxiliary_inputs.csv"} or p.suffix.lower() in {".rds", ".rdata", ".mids"})]
assert not forbidden, forbidden
v = json.loads((R / "results/INDEPENDENT_VERIFICATION.json").read_text(encoding="utf-8"))
assert v["status"] == "PASS_FULL_TRANSFORM_AND_RUBIN_GENDER_URBAN" and v["m"] == 20 and v["models"] == 21 and v["N"] == 2085 and v["communities"] == 432
assert v["full_H4_complete"] is False and v["B_start_sensitivity_passed"] is True
rows = list(csv.DictReader((R / "results/PRIMARY_H42.csv").open(encoding="utf-8")))
assert len(rows) == 1 and rows[0]["path"] == "SY:SXIZ" and rows[0]["contrast"] == "difference"
assert abs(float(rows[0]["estimate"]) - 0.1598951744) < 1e-12 and abs(float(rows[0]["p"]) - 0.20129718633724) < 1e-12
assert len(list((R / "models").glob("*/receipt.json"))) == 21
print("PASS_PUBLIC_GENDER_URBAN_READBACK", v["primary"])
