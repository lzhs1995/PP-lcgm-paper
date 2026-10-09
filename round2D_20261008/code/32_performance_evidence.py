"""只读回溯Round2D估计耗时和手册；不提交或改写任何Mplus模型。"""
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import csv
import hashlib
import json
import re
import statistics
import fitz

ROOT = Path('C:/Users/LZHS/pp_lgcm_review/round2D_20261008')
OUT = ROOT/'audit/performance_review_20261009'
PRIVATE = ROOT/'runtime/performance_sources_20261009'

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def dt(s):
    return datetime.fromisoformat(s)

def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def logs():
    # 只读真实登记调用；绝不把未提交模板计入估计时间。
    with (ROOT/'audit/CALL_REGISTER.csv').open(encoding='utf-8-sig', newline='') as f:
        registered = list(csv.DictReader(f))
    dirs = {read(p)['id']:p.parent for p in (ROOT/'models').glob('*/*/*/input_contract.json')}
    result, steps, provenance = [], [], []
    previous = None
    for call in registered:
        p = dirs[call['id']]
        rp = p/'receipt.json'
        receipt = read(rp) if rp.exists() else {}
        process = read(p/'process.json') if (p/'process.json').exists() else {}
        inp = (p/'model.inp').read_text(encoding='utf-8', errors='replace')
        out_text = (p/'model.out').read_text(encoding='utf-8', errors='replace') if (p/'model.out').exists() else ''
        console = p/'mplus_console.log'
        its = []
        if console.exists():
            for line in console.read_text(encoding='utf-8', errors='replace').splitlines():
                cells = line.split()
                if len(cells) != 8 or not cells[0].isdigit() or cells[5] not in {'EM','EMA','FS','QN'}:
                    continue
                try:
                    it = dict(id=call['id'], iteration=int(cells[0]), algorithm=cells[5],
                        loglikelihood=float(cells[1].replace('D','E').replace('d','e')),
                        absolute_change=float(cells[2].replace('D','E')),
                        relative_change=float(cells[3].replace('D','E')),
                        step_seconds=float(cells[6]), cumulative_seconds=float(cells[7]))
                except ValueError:
                    continue
                # 实际Mplus日志有时第5列另含标记。保留原始列数条件，未匹配不猜测。
                its.append(it)
            # 本机常见格式是7列，算法位于第5列。
            if not its:
                for line in console.read_text(encoding='utf-8', errors='replace').splitlines():
                    cells = line.split()
                    if len(cells) != 7 or not cells[0].isdigit() or cells[4] not in {'EM','EMA','FS','QN'}:
                        continue
                    try:
                        its.append(dict(id=call['id'], iteration=int(cells[0]), algorithm=cells[4],
                            loglikelihood=float(cells[1].replace('D','E').replace('d','e')),
                            absolute_change=float(cells[2].replace('D','E')),
                            relative_change=float(cells[3].replace('D','E')),
                            step_seconds=float(cells[5]), cumulative_seconds=float(cells[6])))
                    except ValueError:
                        continue
        steps.extend(its)
        settings = re.search(r'ANALYSIS:(.*?)(?:MODEL:|OUTPUT:)', inp, re.S|re.I)
        num = re.search(r'Number of Free Parameters\s+(\d+)', out_text)
        dim = re.search(r'Dimensions of numerical integration\s+(\d+)', out_text)
        integration = re.search(r'Number of integration points\s+(\d+)', out_text)
        started = dt(process['started']) if process.get('started') else dt(call['created'])
        seconds = receipt.get('seconds')
        gap = (started-previous).total_seconds() if previous else None
        if seconds is not None:
            from datetime import timedelta
            previous = started+timedelta(seconds=seconds)
        else:
            previous = None
        row = dict(id=call['id'], kind=call['kind'], category=call['category'],
            status=receipt.get('status','RUNNING'), started=started.isoformat(),
            engine_wall_seconds=seconds, since_previous_engine_end_seconds=gap,
            log_rows=len(its), last_log_iteration=its[-1]['iteration'] if its else None,
            last_log_elapsed_seconds=its[-1]['cumulative_seconds'] if its else None,
            max_step_seconds=max(x['step_seconds'] for x in its) if its else None,
            median_step_seconds=statistics.median(x['step_seconds'] for x in its) if its else None,
            integration_dimensions=int(dim[1]) if dim else None,
            integration_points=int(integration[1]) if integration else None,
            free_parameters=int(num[1]) if num else None,
            analysis_block=re.sub(r'\s+',' ',settings[1]).strip() if settings else '',
            console_bytes=console.stat().st_size if console.exists() else None)
        result.append(row)
        for f in ['model.inp','input_contract.json','process.json','receipt.json','model.out','mplus_console.log']:
            source=p/f
            if source.exists():
                provenance.append(dict(path=source.relative_to(ROOT).as_posix(), sha256=sha(source),
                    bytes=source.stat().st_size, still_running=not rp.exists()))
    completed = [r for r in result if r['engine_wall_seconds'] is not None]
    groups = defaultdict(list)
    for r in completed:
        groups[(r['category']=='SYNTHETIC',r['kind'])].append(r['engine_wall_seconds'])
    summary = [dict(synthetic=k[0],kind=k[1],completed=len(v),seconds=sum(v),median_seconds=statistics.median(v)) for k,v in groups.items()]
    write_csv(OUT/'call_timing.csv',result)
    write_csv(OUT/'optimizer_steps.csv',steps)
    write_csv(OUT/'timing_groups.csv',summary)
    payload = dict(created_at=datetime.now(timezone.utc).isoformat(), registered=len(result),
        terminal=len(completed), timing_groups=summary,
        total_terminal_engine_seconds=sum(r['engine_wall_seconds'] for r in completed),
        between_call_seconds=sum(r['since_previous_engine_end_seconds'] or 0 for r in result),
        gap_warning='Between-call interval includes parsing, preparation, resource waits and deliberate maintenance; it is not a pure R overhead measurement.',
        active_model_rows=[r for r in result if r['status']=='RUNNING'],source_files=provenance,
        new_model_calls=0, original_files_changed=False)
    (OUT/'timing_audit.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in payload.items() if k not in ['source_files','active_model_rows']},ensure_ascii=False),flush=True)

def manuals():
    paths = [Path("C:/Users/LZHS/Downloads/Mplus/mplus9/ducument/Documentation/Mplus User's Guide Version 8.pdf"),
        Path('C:/Users/LZHS/Downloads/Mplus/mplus9/ducument/Documentation/Version 9 Language Addendum.pdf')]
    keys = ['PROCESSORS','MCONVERGENCE','MITERATIONS','ADAPTIVE','ALGORITHM','INTEGRATION','SVALUES','MSTARTS','CHOLESKY']
    index=[]
    for p in paths:
        with fitz.open(p) as doc:
            texts=[page.get_text() for page in doc]
            # 全文仅保存在不会被21公开脚本收集的runtime目录。
            (PRIVATE/(p.stem+'.txt')).write_text('\n\n'.join(f'--- PDF PAGE {i+1} ---\n{t}' for i,t in enumerate(texts)),encoding='utf-8')
            matches=[dict(pdf_page=i+1,terms=[k for k in keys if k in t.upper()]) for i,t in enumerate(texts) if any(k in t.upper() for k in keys)]
            index.append(dict(path=str(p),sha256=sha(p),pages=len(doc),matches=matches))
    (OUT/'local_manual_index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([dict(path=r['path'],pages=r['pages'],matched_pages=len(r['matches'])) for r in index]),flush=True)

if __name__ == '__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    PRIVATE.mkdir(parents=True,exist_ok=True)
    logs()
    manuals()
