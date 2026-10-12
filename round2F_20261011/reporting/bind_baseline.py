"""只读复制本轮解释必需的Round2E聚合证据，不复制微观文件。"""
from pathlib import Path
import csv, hashlib, json, shutil

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.parent/'round2E_20261010'
MODEL_FILES={'model.inp','model.out','estimates.dat','tech3.dat','receipt.json','engine_receipt.json',
    'input_contract.json','key_paths.csv','parameters_high_precision.csv','parameter_covariance.csv'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    target=ROOT/'baseline'
    records=[]
    def copy(src,rel):
        dst=target/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst);assert sha(src)==sha(dst)
        records.append(dict(path=rel,bytes=dst.stat().st_size,sha256=sha(dst)))
    ids=[f'CFPS_SD_E0_{i:02d}_base' for i in range(1,11)]
    ids+=['CFPS_SD_E0B_01_diagnostic','CFPS_SD_E1B_01_diagnostic','CFPS_SD_E1_01_q15','CFPS_SD_E1_01_q15_repair',
        'CFPS_SEXGAP_E1_01_q15','CFPS_SEXGAP_E1_01_q15_repair']
    for mid in ids:
        assert (OLD/'models'/mid/'receipt.json').exists(),mid
        for name in sorted(MODEL_FILES):
            p=OLD/'models'/mid/name
            if p.exists():copy(p,f'models/{mid}/{name}')
    for name in ['POOLED_KEY_PATHS.csv','FAMILY_STATUS.csv','SUMMARY.json','MULTIPLICITY.csv','MI_PARAMETER_MATRICES.json']:
        copy(OLD/'results'/name,'results/'+name)
    for name in ['PP_LGCM_review_v50_round2E.docx','PP_LGCM_appendix_review_v42_round2E.docx',
            'expected_tables.json','hypothesis_status.csv','native_word_export.json','manuscript_validation.json']:
        copy(OLD/'manuscript/delivery'/name,'manuscripts/'+name)
    for name in ['SYSTEM_POWER_EVENTS.json','EXECUTION_DETAILS.csv','E0_FIT.csv','NEGATIVE_VARIANCES.csv']:
        p=OLD/'audit'/name
        if p.exists():copy(p,'audit/'+name)
    (target/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(round='Round2E',
        commit='a323b0eace23bb471a5b4b7e66fff5361de5d874',new_estimates=False,files=records),indent=2),encoding='utf-8')
    print('BASELINE_BOUND',len(records),'files',len(ids),'prior attempts')

if __name__=='__main__':main()
