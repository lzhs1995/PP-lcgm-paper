"""生成终态调用、目标处置与耗时证据；只读取聚合参数和独立引擎回执。"""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import csv
import json
import statistics
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def csvwrite(p,rows):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    out=ROOT/'reports';out.mkdir(exist_ok=True)
    S=read(ROOT/'runtime/selection.json');assert S['terminal']['status']=='FINISHED'
    assert read(ROOT/'audit/independent/independent_verification.json')['status']=='PASS'
    records=[];negative=[];fits=[]
    for path in sorted((ROOT/'models').glob('*/receipt.json')):
        r=read(path);d=path.parent;e=read(d/'engine_receipt.json');j=read(d/'input_contract.json')
        rec={k:r.get(k) for k in ['id','z','spec','member','sample','attempt','category','status','seconds','processors','points','sy','integration_dimensions']}
        rec.update(cpu_seconds_recorded=e.get('cpu_seconds'),limit_seconds=e['limit_seconds'],
          input_sha256=j['input_sha256'],output_sha256=r.get('output_sha256'),
          time_over_limit=max(0,e['seconds']-e['limit_seconds']),started_epoch=e['started_epoch'],finished_epoch=e['finished_epoch'])
        records.append(rec)
        hp=d/'parameters_high_precision.csv'
        if hp.exists():
            p=pd.read_csv(hp)
            for _,x in p[(p.matrix.isin(['psi','theta']))&(p.row==p.column)&(p.estimate<0)].iterrows():
                negative.append(dict(id=r['id'],sample=r['sample'],matrix=x['matrix'],variable=x['row'],
                  estimate=x['estimate'],se=x['se'],estimate_over_se=x['estimate']/x['se'],status=r['status']))
            if r['sample']=='CFPS' and r['spec']=='E0':
                from raw_mplus import RawModel
                raw=RawModel(d)
                fits.append(dict(id=r['id'],status=r['status'],**{k:float(raw.extra[k]) for k in
                  ['CFI','TLI','RMSEA : Estimate','SRMR','H0 Loglikelihood','Number of Free Parameters']}))
    csvwrite(out/'EXECUTION_DETAILS.csv',records);csvwrite(out/'NEGATIVE_VARIANCES.csv',negative);csvwrite(out/'E0_FIT.csv',fits)
    b=read(ROOT/'runtime/budget_status.json')
    last_utc=datetime.fromisoformat(b['updated_utc']);batch_start=last_utc.timestamp()-b['wall_seconds']
    ended=datetime.strptime(S['terminal']['utc'],'%Y-%m-%d %H:%M:%S UTC').replace(tzinfo=timezone.utc)
    groups=[]
    for sample,sp in [('SYNTHETIC',None),('CFPS','E0'),('CFPS','E1'),('CFPS','E0B'),('CFPS','E1B')]:
        rr=[r for r in records if r['sample']==sample and (sp is None or r['spec']==sp)]
        if not rr:continue
        ts=[r['seconds'] for r in rr]
        groups.append(dict(group=sample+'_'+(sp or 'interfaces'),calls=len(rr),
          engine_wall_seconds=sum(ts),minimum_seconds=min(ts),median_seconds=statistics.median(ts),maximum_seconds=max(ts),
          cpu_seconds_recorded=sum(r['cpu_seconds_recorded'] or 0 for r in rr)))
    csvwrite(out/'PERFORMANCE_FINAL.csv',groups)
    summary=dict(calls=len(records),cfps_calls=sum(r['sample']=='CFPS' for r in records),
      synthetic_calls=sum(r['sample']=='SYNTHETIC' for r in records),statuses=dict(Counter(r['status'] for r in records)),
      engine_wall_seconds=sum(r['seconds'] for r in records),cpu_seconds_recorded=sum(r['cpu_seconds_recorded'] or 0 for r in records),
      batch_wall_until_queue_terminal_seconds=ended.timestamp()-batch_start,ledger_wall_at_last_engine=b['wall_seconds'],
      batch_started_utc=datetime.fromtimestamp(batch_start,timezone.utc).isoformat(),queue_terminal_utc=ended.isoformat(),
      cap_overshoots=[r for r in records if r['time_over_limit']>1],
      performance_pair='NOT_RUN: primary SD E1 pilot inadmissible; synthetic CPU checks do not establish CFPS acceleration',
      H4='DEFERRED_BY_USER_STAGE_CHOICE',new_latent_IZ_calls=0,primary_E1_adopted=0,
      interpretation='Engine-wall timing includes modern standby; recorded process CPU time is a separate sampled quantity, not a controlled speed comparison.')
    save(out/'EXECUTION_SUMMARY.json',summary)
    targets=[]
    for z in S['branches']:
        for sp in ['E0','E1']:
            for k in range(1,11):
                attempted=[r for r in records if r['sample']=='CFPS' and r['z']==z and r['spec']==sp and r['member']==k]
                actual=S['branches'][z][sp] or {};selected=actual.get(str(k))
                if sp=='E1' and k==1 and not selected:selected=S['branches'][z].get('low')
                status=selected['status'] if selected else 'NOT_RUN'
                why=('15-point pilot did not pass; 20-point MI01 and numerical checks not admitted' if sp=='E1' and k==1 else
                  'Earlier family member/pilot failed; no selected-member pooling' if not attempted else 'Actual call retained')
                targets.append(dict(z=z,spec=sp,member=k,attempted=bool(attempted),status=status,
                  call_ids=';'.join(x['id'] for x in attempted),reason=why))
    csvwrite(out/'TARGET_DISPOSITIONS.csv',targets)
    save(out/'SLEEP_TIMEOUT_DIAGNOSTIC.json',dict(
      event_evidence='audit/SYSTEM_POWER_EVENTS.json',standby_entry_utc='2026-10-10T04:02:09.2692806Z',
      standby_exit_utc='2026-10-10T04:28:58.6364917Z',
      affected_call='CFPS_SEXGAP_E1_01_q15_repair',
      conclusion='The large monitoring gap overlaps recorded Kernel-Power modern-standby events. The watchdog stopped the owned job immediately after resume. The 202-second wall-cap overrun is reported, not clipped; all elapsed time remains charged.',
      limitation='Recorded CPU usage is about 331 seconds; a 2002-second wall record is not evidence of 2002 seconds of active Mplus calculation. No retry was added after batch termination.'))
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
