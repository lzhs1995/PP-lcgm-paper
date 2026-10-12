"""冻结前修改副本，保留原附件。禁止针对已冻结代码执行。"""
from pathlib import Path
import json, shutil
R=Path('C:/Users/LZHS/pp_lgcm_review/round2F_20261011')
assert not (R/'contracts/FROZEN_CODE_2F.json').exists()
C=json.loads((R/'contracts/RUN_CONTRACT_2F.json').read_text())
C['status']='APPROVED_CONSENSUS_PENDING_FREEZE'
C['paths_default']['R2F_ROOT']=str(R).replace('\\','/')
C['points']=30
C['pilot_points']=[20,30]
C['budget']['categories']={'SMOKE':4,'NUMERIC':8,'TARGET':18,'REPAIR':3,'DIAG':6}
C['budget']['accounting']='All actual engine wall seconds are charged, including suspension; no polling-gap deductions. Batch wall starts at P0 and never resets.'
C['budget']['resource_wait_seconds']=1800
C['budget']['per_call_active_seconds']={'synthetic':180,'linear':180,'observed_LMS':600}
C['convergence']={'default':[], 'tight':['LOGCRITERION=0.00001; RLOGCRITERION=0.000000001;']}
C['expected_printed_criteria']={'tight':C['expected_printed_criteria']['tight']}
C['decision_rules']={'F1_pass':'E1B: q30 two legal starts agree, q20 to q30 precision passes for both sources, and exact LL agrees.', 'F2_pass':'Free E1: same numerical checks; q20 SY-only inadmissible results are diagnostic comparisons only; both q30 results must be USABLE.', 'A':'Both pass: free E1 primary first, E1B sensitivity second.', 'A1':'Only free passes: complete free E1.', 'B':'Only constrained passes: E1B strong-constraint sensitivity only.', 'C':'Neither passes: no MI family.', 'family':'Exactly ten same-spec q30/tight members, one repair per member from same-member legal E0, max three repairs. Resume incomplete families member by member.', 'budget_guard':'Reserve 9*1.25*selected q30 MI01 wall time, no diagnostics before admitted families finish.'}
C['diagnostics_order']=['F5 fixed SY 0.020/0.034/0.080','F6 complete-control E0 and numerically qualified specification','O1 P99 top-code if budget allows']
C['deferred']=['H4','other Z branches','latent IZ','window/scale/Y-shape','E0B family','processor pair','SE decomposition']
C['data']['CC']['rule']='Nine original analysis covariates complete before MI (expanded into 24 controls); sat12 is not a selection variable. All control values identical across ten members.'
C['sy_fixed_grid_rationale']='0.034 is the rounded mean of ten Round2E SD E0 SY residual estimates (0.0339186401); 0.020 and 0.080 bracket it descriptively. Not a confidence interval.'
(R/'contracts/RUN_CONTRACT_2F.json').write_text(json.dumps(C,ensure_ascii=False,indent=2),encoding='utf-8')
for f in C['reused_round2E_code_sha256']:shutil.copy2(Path(C['paths_default']['R2F_R2E'])/'code'/f,R/'code'/f)
p=R/'code/r2f_engine.py';s=p.read_text()
s=s.replace('3) 记录挂起间隙：两次轮询之间墙钟跳跃超过合同阈值即登记；单次时限与引擎预算按“有效秒”\n   （墙钟减去挂起间隙）计算，墙钟预算仍计全部真实时间。','3) 轮询间隙仅作诊断；单次时限与总预算均按完整墙钟计费，绝不把监督器延迟直接当作待机扣减。')
s=s.replace("    def __enter__(self):\n", "    def __enter__(self):\n")
s=s.replace("        self.hook = os.environ.get('R2F_ENGINE_TEST_CLOCK_JUMP')", "        self.hook = os.environ.get('R2F_ENGINE_TEST_CLOCK_JUMP')")
s=s.replace("    for name, digest in json.loads(manifest.read_text(encoding='utf-8')).items():", "    cf = root / 'contracts/FROZEN_CONTRACT_SHA256.txt'\n    if not cf.exists() or sha(root / 'contracts/RUN_CONTRACT_2F.json') != cf.read_text().strip():\n        raise RuntimeError('Frozen execution contract changed')\n    for name, digest in json.loads(manifest.read_text(encoding='utf-8')).items():")
s=s.replace("    db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', ('batch_start', clock.now()))", "    bw = json.loads((root / 'runtime/batch_window.json').read_text())\n    db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', ('batch_start', bw['start_epoch']))")
s=s.replace("                        # 只扣除超出本轮计划休眠的部分，正常轮询时间仍计为有效秒", "                        # 仅记录轮询延迟，不判断为睡眠，不扣预算。")
s=s.replace("                    active = (now - start) - sum(g['seconds'] for g in gaps)","                    active = now - start")
s=s.replace("                    if active >= limit:","                    if active >= limit or now - batch_start >= wall_cap:")
s=s.replace("            seconds = (finish - start) - gap_seconds", "            seconds = finish - start")
s=s.replace("'suspend_affected': bool(gaps)", "'suspend_affected': None, 'polling_gap_affected': bool(gaps), 'accounting': 'gross engine wall; no suspension deduction'")
s=s.replace("            print(json.dumps({k: result[k] for k in ('id', 'status', 'seconds', 'gap_seconds', 'keep_awake')}))", "            print(json.dumps({k: result[k] for k in ('id', 'status', 'seconds', 'gap_seconds', 'keep_awake')}))\n    write_json(dest / 'keep_awake_release.json', {'state': awake.state, 'utc': utc()})")
p.write_text(s,encoding='utf-8')
p=R/'code/r2f_local.R';s=p.read_text()
s=s.replace("  if (file.exists(cf)) return(rj(cf))", "  if (file.exists(cf)) { old <- rj(cf); stopifnot(old$points == if (spec(z, sp, ctrl)$kind == 'linear') 0L else points, identical(old$conv, conv), identical(old$data_sha256, hashf(source_data)), identical(old$input_sha256, hashf(file.path(d, 'model.inp')))); return(old) }")
s=s.replace("rf <- file.path(ROOT, 'models', id, 'receipt.json'); if (file.exists(rf)) return(rj(rf))", "rf <- file.path(ROOT, 'models', id, 'receipt.json'); if (file.exists(rf)) { old <- rj(rf); ic <- rj(file.path(dirname(rf),'input_contract.json')); stopifnot(identical(ic$input_sha256,hashf(file.path(dirname(rf),'model.inp'))),identical(old$output_sha256,hashf(file.path(dirname(rf),'model.out')))); if (!is.null(a$points)) stopifnot(old$points == a$points); return(old) }")
# 精确LL缓存必须绑定输入；Python数值诊断独立限制线程。
s=s.replace("  if (file.exists(out)) return(rj(out))", "  if (file.exists(out)) { ex <- rj(out); if (identical(ex$data_sha256,hashf(data)) && identical(ex$matrix_values_sha256,hashf(file.path(dest,'matrix_values.csv')))) return(ex); stop('Stale exact LL cache') }")
s=s.replace("  res <- tryCatch(processx::run(PY, args", "  args <- c('-X','utf8',args)\n  res <- tryCatch(processx::run(PY, args")
# 非法残差只允许诊断数值比较，不能更改原回执的USABLE。
s += '''\n# 同科学规格的数值比较；低积分的SY负残差只作诊断。
numeric_compare_2f <- function(a,b,mode='start', diagnostic=FALSE) {
  eligible <- function(x) !is.null(x) && (usable(x) || (diagnostic && identical(x$status,'INADMISSIBLE_SY_ONLY'))) && isTRUE(x$normal) && is.finite(x$LL)
  if (!eligible(a) || !eligible(b)) return(list(passed=FALSE,outcome='UNAVAILABLE_OR_FAILED',mode=mode))
  if (!identical(a$structural_signature,b$structural_signature)) return(list(passed=FALSE,outcome='STRUCTURE_MISMATCH',mode=mode))
  aa <- list(key=utils::read.csv(file.path(a$dest,'key_paths.csv')),receipt=a)
  bb <- list(key=utils::read.csv(file.path(b$dest,'key_paths.csv')),receipt=b)
  ans <- compare_numeric(aa,bb,mode)
  ans$outcome <- if(isTRUE(ans$passed)) 'AGREE' else 'NOT_REPLICATED'
  ans$diagnostic_comparison <- diagnostic
  ans
}
family_valid_2f <- function(F) {
  if(is.null(F) || !identical(sort(names(F$members)),sort(as.character(1:10))))) return(FALSE)
  m <- F$members
  all(vapply(m,usable,TRUE)) && all(vapply(m,function(x) identical(x$spec,F$spec) && x$points==30 && identical(x$conv,'tight') && identical(x$sample,'CFPS') && identical(x$data_tag,'Z0'),TRUE)) && length(unique(vapply(m,function(x)x$structural_signature,'')))==1L && identical(sort(vapply(m,function(x)as.integer(x$member),1L)),1:10)
}
'''
p.write_text(s,encoding='utf-8')
p=R/'code/r2f_exact_ll.py';s=p.read_text().replace('import numpy as np',"os.environ['OPENBLAS_NUM_THREADS']='1'\nos.environ['OMP_NUM_THREADS']='1'\nimport numpy as np")
s=s.replace("    # product terms: for row r", "    if np.any(M['P'][np.ix_(ie,ix)] != 0):\n        raise SystemExit('UNSUPPORTED: endogenous-exogenous residual covariance')\n    # product terms: for row r")
p.write_text(s,encoding='utf-8')
p=R/'code/r2f_setup.R';s=p.read_text()+"\nwriteLines(hashf(file.path(root,'contracts/RUN_CONTRACT_2F.json')), file.path(root,'contracts/FROZEN_CONTRACT_SHA256.txt'))\ncat('CONTRACT FROZEN\\n')\n";p.write_text(s,encoding='utf-8')
print('CONSENSUS_PATCHES_APPLIED')
