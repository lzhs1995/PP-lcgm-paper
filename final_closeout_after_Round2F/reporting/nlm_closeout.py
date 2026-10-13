"""仅最终PDF审阅，逐轮留存来源与原文；不调用统计引擎。"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runtime/nlm'
EXE = 'C:/Users/LZHS/.local/bin/nlm.exe'
HELPERS = Path('C:/Users/LZHS/Desktop/cnm/tasks/01_R_analysis/work/clauder-rstudio-workbench_repo_20261004/skills/mplusautomation-guide/scripts')
sys.path.insert(0, str(HELPERS))
import nlm_reliability as nr

PDFS = [ROOT/'manuscript/delivery'/n for n in ['PP_LGCM_scoped_final_candidate.pdf', 'PP_LGCM_scoped_supplement.pdf']]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def dump(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
def progress(stage, message):
    dump(OUT/'progress.json', dict(stage=stage,message=message,updated_at=now(),pid=os.getpid(),new_mplus_calls=0))
    log=ROOT/'executor_logs/executor.log'; log.parent.mkdir(exist_ok=True)
    with log.open('a',encoding='utf-8') as f: f.write(f'{now()} SOLO_CODEX {stage}: {message}\n')
    print(stage, message, flush=True)
def call(args, file, timeout=180):
    progress('NLM_CALL', ' '.join(args[:3]))
    c=subprocess.run([EXE,*args],capture_output=True,timeout=timeout)
    dump(file,dict(returncode=c.returncode,stdout=nr.as_text(c.stdout),stderr=nr.as_text(c.stderr),utc=now()))
    if c.returncode:
        dump(file.with_suffix('.auth.json'),nr.run_list(EXE,'default'))
        raise RuntimeError(f'NLM command failed: {file.name}')
    return nr.compact_json(nr.as_text(c.stdout))
def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    gate=None
    for attempt in range(1,4):
        gate=nr.run_list(EXE,'default');dump(OUT/f'auth_{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")}_{attempt}.json',gate)
        dump(OUT/'auth_gate.json',gate)
        if gate['status']=='AUTH_VALID':break
        progress('AUTH_RECHECK',f'attempt={attempt} status={gate["status"]}')
        if attempt<3:time.sleep(5)
    if gate['status']!='AUTH_VALID':raise RuntimeError(gate['status'])
    progress('AUTH_VALID',f"notebook_count={gate['notebook_count']}")
    p=OUT/'notebook_create.json'
    if p.exists():payload=nr.compact_json(json.loads(p.read_text())['stdout'])
    else:payload=call(['notebook','create','PP-LGCM scoped closeout final PDFs 20261013','--json'],p)
    nb=payload.get('id') or payload.get('notebook_id') or payload.get('notebook',{}).get('id')
    assert nb,payload
    dump(OUT/'notebook.json',dict(notebook_id=nb,pdf_only=True))
    return nb
def run(number, focus):
    nb=prepare();rd=OUT/f'round_{number:02d}';rd.mkdir(exist_ok=True)
    # 只清理本任务曾经上传的旧source；不删除其他参考材料。
    if number>=5 and not (rd/'cleanup.json').exists():
        known=set()
        for prior in OUT.glob('round_*/sources.json'):
            if int(prior.parent.name.split('_')[1])<number:
                known.update(x['id'] for x in json.loads(prior.read_text(encoding='utf-8')))
        listing=call(['source','list',nb,'--json'],rd/'source_list_before.json')
        entries=listing if isinstance(listing,list) else listing.get('sources',listing.get('items',[]))
        ids=sorted(known & {x.get('id') for x in entries})
        if ids:call(['source','delete',*ids,'--confirm','--json'],rd/'delete_old_sources.json')
        dump(rd/'cleanup.json',{'deleted_own_source_ids':ids,'other_sources_preserved':True})
    # 已上传的本轮文件必须和当前PDF一致，避免断点恢复时误用旧版。
    sources=[]
    for i,pdf in enumerate(PDFS):
        f=rd/f'upload_{i}.json'
        if f.exists():payload=nr.compact_json(json.loads(f.read_text())['stdout'])
        else:
            assert pdf.suffix=='.pdf'
            payload=call(['source','add',nb,'--file',str(pdf),'--wait','--wait-timeout','300','--json'],f,360)
        sid=payload.get('id') or payload.get('source_id') or payload.get('source',{}).get('id')
        assert sid,payload
        sources.append(dict(id=sid,pdf=pdf.name,sha256=sha(pdf)))
    sf=rd/'sources.json'
    if sf.exists():assert json.loads(sf.read_text())==sources,'PDF changed after upload; start new round'
    else:dump(sf,sources)
    ids=[s['id'] for s in sources]
    topics={
      'structure':'重点审查两稿全部表格和文字的数字、方向、样本数、表号和跨稿引用是否一致；区分主文5表与补充A1-A30、当前采用结果与标记的历史审计。',
      'methods':'重点审查测量、时间单位、缺失值/插补合并、模型与参数含义、文献归因和结论强度；不将已明确披露而未执行的研究当作本轮必须补跑。',
      'final':'重点审查所有文字与表格的一致性、方法和结论、表注、脚注、符号、编号、参考文献和无来源断言。排版问题需具体原文，不凭文本抽取空格臆造视觉缺陷。'
    }
    prompt='请仅依据本轮两个PDF：'+ '与'.join('['+p.name+']' for p in PDFS)+'进行独立完整审查，不使用旧版本或其他sources。'+topics[focus]
    prompt+='\n这是作者已明确收缩范围的候选稿，保留SW和SD E0；完整调节MI及H4未完成，均需诚实披露。本轮不新增模型；必要新研究列为限制，不能以显著性为修订目标。补充末尾是明确标识的原假设和历史方法，不自动当成现行结论。'
    prior=OUT/'adjudication_for_next_round.txt'
    if prior.exists():prompt+='\n以下为以前发现的本地证据裁决，仅供区分重复和新发现，不能作为PDF事实替代；请继续自行检查：\n'+prior.read_text(encoding='utf-8')
    prompt+='\n必须使用NotebookLM原生带来源定位的数字引用（如[1]），分别引用两份PDF原文，不要自己把文件名写在方括号中充当引用。如果无法访问来源，请明确报告失败，不得宣称审阅通过。先分别引用主文表4的一条完整路径和补充A22的原句以确认源文件读取。随后覆盖两份完整PDF。列出每个可核实问题的位置、短引文、理由和最小修正；允许指出以前裁决有误。结尾写 NEW_ISSUES_COUNT: 实际新增问题数 和 A5_NO_NEW_ISSUES: YES或NO。没有新问题才写本轮未发现新问题。最多1600汉字，保留结束标记。'
    (rd/'prompt.txt').write_text(prompt,encoding='utf-8')
    if (rd/'result.json').exists():
        progress('REUSE_REVIEW',str(rd));return
    progress('QUERY',f'round={number}, focus={focus}, source_ids={ids}')
    result=nr.run_query(EXE,nb,prompt,ids,rd/'query',filename=PDFS[0].name,attempts=1,timeout=240)
    dump(rd/'result.json',dict(round=number,focus=focus,sources=sources,result=result,created_utc=now()))
    progress('REVIEW_READY',f'round={number}, status={result["status"]}; awaiting evidence adjudication')
    if result['status']!='PASS':raise RuntimeError(result)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('round',type=int);parser.add_argument('focus',choices=['structure','methods','final']);args=parser.parse_args()
    run(args.round,args.focus)
