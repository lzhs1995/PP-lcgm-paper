"""保存本轮报告所复用的聚合证据、文献定位及历史报告版本链；不读微观数据。"""
from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / 'round2D_20261008'
OUT = ROOT / 'reporting/context_evidence'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dump(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = [
        'audit/MI_CONGENIALITY_AUDIT.json', 'audit/MI_actual_predictor_coverage.csv',
        'audit/MI_terminal_chain_summary.csv', 'audit/G_CODING_CONFIRMATION.json',
        'audit/baseline_controls_descriptives.csv', 'audit/baseline_Z_eligibility.csv',
        'audit/control_column_decisions.csv', 'audit/moderator_descriptives.csv',
        'audit/Z_CONTRACT.json', 'audit/PERFORMANCE_REVIEW_20261009.md',
        'audit/PERFORMANCE_CALIBRATION_EXECUTION.md',
        'audit/stage_closeout_20261009/D0_VARIANCE_DIAGNOSTICS.csv',
        'audit/stage_closeout_20261009/changed_bound_sources.json',
        'audit/stage_closeout_20261009/PROSE_SYNC_20261009.md',
        'audit/stage_closeout_20261009/SYNTHETIC_STATUS_CORRECTION.md',
        'audit/stage_closeout_20261009/synthetic_status_correction.json',
        'reports_final/MODEL_EXECUTION.csv', 'reports_final/PERFORMANCE_FINAL.csv',
        'results/SW_structure_pooled.csv', 'results/SW_structure_members.csv',
        'manuscript/delivery/expected_tables.json', 'manuscript/delivery/retained_citations.json',
        'manuscript/delivery/PP_LGCM_review_v49_round2D.docx',
        'manuscript/delivery/PP_LGCM_appendix_review_v41_round2D.docx',
    ]
    bound = []
    for name in names:
        src = OLD / name
        dst = OUT / 'round2D' / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        bound.append(dict(source_round='Round2D', path=name, sha256=sha(src), bytes=src.stat().st_size))
    dump(OUT / 'UPSTREAM_AGGREGATE_BINDINGS.json', bound)

    old_record = json.loads((OLD/'audit/stage_closeout_20261009/changed_bound_sources.json').read_text())
    versions = []
    for row in old_record['changes']:
        src = OLD / row['file']
        published = OLD / 'public_stage' / row['file']
        assert src.read_bytes() == published.read_bytes(), row['file']
        versions.append(dict(file=row['file'], original_sha256=row['original_sha256'],
            interim_stage_sha256=row['stage_sha256'], final_local_sha256=sha(src),
            final_published_sha256=sha(published), final_local_matches_published=True,
            interim_is_final=(row['stage_sha256']==sha(src))))
    dump(OUT / 'REPORT_CODE_VERSION_CHAIN.json', dict(
        upstream_fixed_commit='cf5ab4fb9e1e59742462a7dadd85ff6fdbdb83b0', versions=versions,
        explanation='changed_bound_sources.json is an interim stage snapshot, not the final publication manifest. Subsequent prose/status corrections are documented in the two retained notes. No historical package was rewritten.',
        remaining_limit='The interim manifest was not updated after those corrections; this is a reporting provenance defect. Final published bytes, original model outputs and final status correction evidence are retained separately.'))

    inv = json.loads((ROOT/'audit/LITERATURE_SOURCE_INVENTORY.json').read_text(encoding='utf-8'))
    source = {r['key']:r for r in inv}
    findings = [
        dict(key='li2023', doi='10.1093/geronb/gbad004', pages='925; 930–932 (PDF 1, 6–8)',
             issue='抑郁方向与交互操作化',
             finding='摘要将最亲近关系类型与较低抑郁、最疏远关系类型与较高抑郁相联系。模型4实际包含“有无疏离关系×最近关系类型”的交互；这与本研究连续增长乘积不同。',
             action='纠正原稿方向；保留类型与连续指标的区别，不把全部类别比较概括为单调剂量关系。'),
        dict(key='zhang2025', doi='10.1017/S0144686X24000795', pages='2089; 2093–2094; 2111–2112 (PDF 1, 5–6, 23–24)',
             issue='最远关系限定及互动策略',
             finding='认知水平和下降快慢的所述结论限定于最远关系类型；最近关系未显著。该文以类型标准差/极差表示异质性，未估计本研究的SX×Z乘积。',
             action='补“最远关系”限定；明示其异质性操作化与本研究乘积交互不同。'),
        dict(key='zhangliu2024', doi='10.1177/02654075241283974', pages='3871 (PDF 11)',
             issue='固定基期标准化出处',
             finding='方法明确以后期认知的2006基期均值/标准差、关系指标的2006/08基期参照作标准化，并使用家庭聚类标准误。',
             action='两作者引用统一为Zhang & Liu；固定基期标准化出处经本机原文核对，不能据此证明本研究的其他模型假设。'),
    ]
    for f in findings:
        f['source_sha256'] = source[f['key']]['sha256']
        f['source_pages_total'] = source[f['key']]['pages']
        f['verification_scope'] = 'Full local PDF text extracted; listed substantive passages read. No claim to re-review every cited source.'
    dump(OUT / 'LITERATURE_VERIFICATION.json', findings)
    with (OUT/'LITERATURE_VERIFICATION.csv').open('w',encoding='utf-8-sig',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(findings[0]));w.writeheader();w.writerows(findings)
    dump(OUT/'CONTEXT_EVIDENCE_RECEIPT.json',dict(status='PASS',new_mplus_calls=0,microdata_read=False,
        aggregate_files_bound=len(bound),literature_sources=3,created_utc=datetime.now(timezone.utc).isoformat()))
    print('CONTEXT_EVIDENCE_PASS',len(bound),'aggregate files; 3 locally identified sources',flush=True)


if __name__=='__main__':
    main()
