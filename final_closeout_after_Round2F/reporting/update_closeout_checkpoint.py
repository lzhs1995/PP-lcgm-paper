"""持久化收尾阶段，避免恢复后误开统计队列。"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
phase=sys.argv[1];plan=ROOT/'supervisor_outbox/approved-plan-pp-lgcm-closeout-20261013.md'
proof={'TASK_ID':'pp-lgcm-closeout-20261013','ROLE':'CODEX_SUPERVISOR','PHASE':phase,'ROUND':8,
 'LAST_GOOD_CHECKPOINT':'CURRENT_PDF_VISUAL_AND_NLM_5_6_8_ACCEPTED','RESTART_FROM':'NLM_FINAL_READBACK',
 'APPROVED_PLAN_PATH':str(plan),'APPROVED_PLAN_HASH':hashlib.sha256(plan.read_bytes()).hexdigest(),
 'COMPACT_EPOCH':2,'COMPACT_RESUME_REQUIRED':'false','NEW_MPLUS_CALLS':0,
 'SUBAGENT_LAUNCH':'existing Codex pane %6; readiness observed; formal V2 not established',
 'SUBAGENT_MODEL':'existing gpt-6-astra launch configuration; no model change',
 'READ_SET':'approved-plan;agent-state;executor.log;canonical thesis-refiner SKILL;NLM contract;publication scripts',
 'NEXT_ACTION':'Read final PDF review, adjudicate, package and publish after acceptance','UPDATED_AT':datetime.now(timezone.utc).isoformat()}
text=''.join(f'{k}={v}\n' for k,v in proof.items())
for name in ['agent-state-pp-lgcm-closeout-20261013.status','supervisor-progress-pp-lgcm-closeout-20261013.status','compact-resume-proof-pp-lgcm-closeout-20261013.status']:
 (ROOT/name).write_text(text,encoding='utf-8')
with (ROOT/'executor_logs/executor.log').open('a',encoding='utf-8') as f:f.write(f'{proof["UPDATED_AT"]} SOLO_CODEX {phase}; zero estimates; final review and publication remaining\n')
print(phase)
