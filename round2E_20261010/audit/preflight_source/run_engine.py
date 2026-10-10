"""单槽、事务预算与独立时限监督器；不终止本调用以外的进程。"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import psutil

CAPS = {'SMOKE': 6, 'TARGET': 80, 'NUMERIC': 8, 'PERFORMANCE': 1, 'REPAIR': 4, 'BOUNDARY': 2}

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def write_json(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def database(root):
    db = sqlite3.connect(root / 'runtime/budget.sqlite', timeout=20)
    db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value REAL)')
    db.execute('CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, category TEXT, state TEXT, seconds REAL, reserved REAL, pid INTEGER, create_time REAL, start REAL, finish REAL, dest TEXT)')
    db.commit()
    return db

def verify_frozen(root):
    manifest = root / 'contracts/FROZEN_CODE.json'
    if manifest.exists():
        for name, digest in json.loads(manifest.read_text(encoding='utf-8')).items():
            if sha(root / 'code' / name) != digest:
                raise RuntimeError('Frozen code changed: ' + name)

def usage(db):
    rows = db.execute('SELECT id,state,seconds FROM calls').fetchall()
    # 不把未知时长记为零；仅可从独立监督器写出的完整回执恢复。
    unknown = [r[0] for r in rows if r[2] is None]
    if unknown:
        raise RuntimeError('Unknown or still-running duration; no new admission: ' + ','.join(unknown))
    return sum(r[2] for r in rows)

def recover(db):
    for ident, dest in db.execute('SELECT id,dest FROM calls WHERE seconds IS NULL').fetchall():
        f = Path(dest) / 'engine_receipt.json'
        if f.exists():
            r = json.loads(f.read_text(encoding='utf-8'))
            if isinstance(r.get('seconds'), (int, float)):
                db.execute('UPDATE calls SET state=?,seconds=?,finish=? WHERE id=?', (r['status'], r['seconds'], r['finished_epoch'], ident))
    db.commit()

def main():
    job = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    root, dest = Path(job['root']), Path(job['dest'])
    receipt = dest / 'engine_receipt.json'
    if receipt.exists():
        return
    verify_frozen(root)
    assert sha(dest / 'model.inp') == job['input_sha256']
    assert sha(dest / 'data.dat') == job['data_sha256']
    db = database(root)
    recover(db)
    db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', ('batch_start', time.time()))
    db.commit()
    batch_start = db.execute("SELECT value FROM meta WHERE key='batch_start'").fetchone()[0]
    resource_wait_start = time.time()
    while True:
        engine_left = 28800 - usage(db)
        wall_left = 36000 - (time.time() - batch_start)
        if min(engine_left, wall_left) <= 5:
            raise RuntimeError('BUDGET_EXHAUSTED before launch')
        other = []
        for p in psutil.process_iter(['pid', 'name', 'create_time']):
            if 'mplus' in (p.info['name'] or '').lower():
                other.append(p.info)
        available = psutil.virtual_memory().available / 2**30
        cpu = psutil.cpu_percent(interval=0.5)
        paused = (root / 'runtime/PAUSE').exists()
        snapshot = {'utc': utc(), 'available_gib': available, 'cpu_percent': cpu, 'other_mplus': other, 'paused': paused}
        write_json(dest / 'resource_before.json', snapshot)
        if not other and not paused and available >= .5 and cpu < 85:
            break
        write_json(dest / 'engine_progress.json', {'stage': 'resource_wait', 'message': f'waiting {time.time()-resource_wait_start:.0f}s; available={available:.2f}GiB; other_mplus={len(other)}', 'utc': utc()})
        if time.time() - resource_wait_start > 7200:
            raise RuntimeError('RESOURCE_WAIT_LIMIT; no Mplus launched')
        time.sleep(min(10, max(1, wall_left)))
    db.execute('BEGIN IMMEDIATE')
    try:
        used = usage(db)
        total = db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]
        category = db.execute('SELECT COUNT(*) FROM calls WHERE category=?', (job['category'],)).fetchone()[0]
        if total >= 101 or category >= CAPS[job['category']]:
            raise RuntimeError('CALL_CAP before launch')
        limit = min(job['cap_seconds'], 28800-used-2, 36000-(time.time()-batch_start)-2)
        if limit <= 0:
            raise RuntimeError('BUDGET_EXHAUSTED before launch')
        db.execute('INSERT INTO calls (id,category,state,seconds,reserved,dest) VALUES (?,?,?,?,?,?)',
                   (job['id'], job['category'], 'CLAIMED', None, limit, str(dest)))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    start = time.time()
    status, exitcode, proc, cpu_seconds, max_rss = 'START_FAILED', None, None, 0.0, 0
    try:
        with (dest / 'mplus_console.log').open('wb') as log:
            proc = subprocess.Popen([job['mplus'], 'model.inp'], cwd=dest, stdout=log, stderr=subprocess.STDOUT)
            ps = psutil.Process(proc.pid)
            born = ps.create_time()
            db.execute('UPDATE calls SET pid=?,create_time=?,start=?,state=? WHERE id=?', (proc.pid, born, start, 'RUNNING', job['id']))
            db.commit()
            write_json(dest / 'process.json', {'pid': proc.pid, 'create_time': born, 'exe': job['mplus'], 'cwd': str(dest), 'input_sha256': job['input_sha256'], 'started_epoch': start, 'limit_seconds': limit})
            last = 0
            while proc.poll() is None:
                elapsed = time.time() - start
                try:
                    cpu_seconds = sum(ps.cpu_times()[:2])
                    max_rss = max(max_rss, ps.memory_info().rss)
                except psutil.Error:
                    pass
                if elapsed - last >= 10:
                    write_json(dest / 'engine_progress.json', {'stage': 'estimating', 'message': f'{elapsed:.0f}/{limit:.0f}s; CPU={cpu_seconds:.1f}s', 'utc': utc(), 'seconds': elapsed})
                    last = elapsed
                if elapsed >= limit:
                    # 持有Popen句柄和创建时间，只结束自有进程树。
                    if ps.is_running() and abs(ps.create_time()-born) < .001:
                        for child in ps.children(recursive=True):
                            child.kill()
                        ps.kill()
                    proc.wait(timeout=20)
                    status, exitcode = 'TIMEOUT', 124
                    break
                time.sleep(min(1, max(.05, limit-elapsed)))
            else:
                exitcode = proc.returncode
                status = 'EXITED'
    except BaseException as exc:
        status = 'ENGINE_ERROR'
        write_json(dest / 'engine_error.json', {'error': repr(exc), 'utc': utc()})
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait(timeout=20)
    finally:
        seconds = time.time() - start
        result = {'id': job['id'], 'status': status, 'seconds': seconds, 'cpu_seconds': cpu_seconds, 'max_rss': max_rss,
                  'limit_seconds': limit, 'exitcode': exitcode, 'started_epoch': start, 'finished_epoch': time.time(), 'finished_utc': utc()}
        # 先原子写独立回执，再更新事务台账；断点恢复幂等。
        write_json(receipt, result)
        db.execute('UPDATE calls SET state=?,seconds=?,start=?,finish=? WHERE id=?', (status, seconds, start, result['finished_epoch'], job['id']))
        db.commit()
        rows = db.execute('SELECT id,category,state,seconds,reserved,start,finish FROM calls ORDER BY start').fetchall()
        write_json(root / 'runtime/budget_status.json', {'calls': len(rows), 'engine_seconds': usage(db), 'wall_seconds': time.time()-batch_start,
                   'updated_utc': utc(), 'rows': [dict(zip(['id','category','state','seconds','reserved','start','finish'], r)) for r in rows]})
        print(json.dumps(result))

if __name__ == '__main__':
    main()
