"""收集已公开的聚合证据；白名单复制，不复制参与者数据或文献全文。"""
from prepare_closeout import *

SOURCES={
 'SW_paths.csv':'round2C_20261007/results/conditional_MI_paths.csv',
 'SW_fit.csv':'round2C_20261007/results/model_fit.csv',
 'SW_members.csv':'round2C_20261007/results/SW_member_estimates.csv',
 'SW_within_covariance.csv':'round2C_20261007/results/SW_within_covariance.csv',
 'SD_E0_paths.csv':'round2F_20261011/baseline/results/POOLED_KEY_PATHS.csv',
 'SD_E0_multiplicity.csv':'round2F_20261011/baseline/results/MULTIPLICITY.csv',
 'SD_E0_parameter_matrices.json':'round2F_20261011/baseline/results/MI_PARAMETER_MATRICES.json',
 'SD_E0_recomputed.csv':'round2F_20261011/audit/independent/baseline_SD_E0_recomputed.csv',
 'NUMERIC_PATH_COMPARISONS.csv':'round2F_20261011/reports/NUMERIC_PATH_COMPARISONS.csv',
 'CALLS_2F.csv':'round2F_20261011/reports/CALLS.csv',
 'CALLS_2E.csv':'round2E_20261010/reports/EXECUTION_DETAILS.csv',
 'SUMMARY_2F.json':'round2F_20261011/reports/SUMMARY.json',
 'DIAGNOSTIC_PARAMETERS.csv':'round2F_20261011/reports/DIAGNOSTIC_PARAMETERS.csv',
 'independent_verification_2F.json':'round2F_20261011/audit/independent/independent_verification.json',
 'Z_CONTRACT.json':'round2D_20261008/audit/Z_CONTRACT.json',
 'MI_protocol.json':'round2D_20261008/audit/MI_source_snapshot/mi_protocol.json',
 'MI_terminal_chain_summary.csv':'round2D_20261008/audit/MI_terminal_chain_summary.csv',
 'MI_CONGENIALITY_AUDIT.json':'round2D_20261008/audit/MI_CONGENIALITY_AUDIT.json',
 'observed_longitudinal_descriptives.csv':'round2D_20261008/audit/observed_longitudinal_descriptives.csv',
 'baseline_controls_descriptives.csv':'round2D_20261008/audit/baseline_controls_descriptives.csv',
 'LITERATURE_VERIFICATION.csv':'round2E_20261010/reporting/context_evidence/LITERATURE_VERIFICATION.csv',
 'LITERATURE_VERIFICATION.json':'round2E_20261010/reporting/context_evidence/LITERATURE_VERIFICATION.json',
 'LITERATURE_SOURCE_INVENTORY.json':'round2E_20261010/audit/LITERATURE_SOURCE_INVENTORY.json',
}
def main():
    records=[]
    def cp(src,dst):
        dst.parent.mkdir(parents=True,exist_ok=True)
        if not dst.exists():shutil.copy2(src,dst)
        assert sha(src)==sha(dst)
        records.append(dict(source=str(src),snapshot=str(dst.relative_to(ROOT)),sha256=sha(src)))
    for dst,src in SOURCES.items():cp(ROOT.parent/src,ROOT/'evidence'/dst)
    for folder in (OLD/'models').iterdir():
        if not folder.is_dir():continue
        for name in ['model.out','parameters_high_precision.csv','parameter_covariance.csv','key_paths.csv','receipt.json','exact_ll.json']:
            src=folder/name
            if src.exists():cp(src,ROOT/'evidence/models'/folder.name/name)
    (ROOT/'reports/EVIDENCE_SOURCES.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    for name in ['document_support.py','pdf_checks.py','export_word_pdf.py']:
        dst=ROOT/'reporting'/name
        if not dst.exists():shutil.copy2(OLD/'reporting'/name,dst)
    print('COPIED',len(records),'aggregate evidence files')
if __name__=='__main__':main()
