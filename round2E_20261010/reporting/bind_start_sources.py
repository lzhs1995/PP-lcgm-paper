"""复制实际使用的外部起点源聚合输出，令公开包可独立验证完整起点。"""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    sources={}
    for cf in sorted((ROOT/'models').glob('*/input_contract.json')):
        j=json.loads(cf.read_text(encoding='utf-8-sig'))
        if not j.get('source_start'):continue
        src=Path(j['source_start']);h=sha(src/'model.out')
        if src.is_relative_to(ROOT/'models'):
            rel=src.relative_to(ROOT).as_posix()
        else:
            dst=ROOT/'upstream/start_sources'/h[:16]
            dst.mkdir(parents=True,exist_ok=True)
            for name in ['model.inp','model.out','estimates.dat','tech3.dat']:
                shutil.copyfile(src/name,dst/name)
            rel=dst.relative_to(ROOT).as_posix()
        sources[h]=dict(path=rel,source_original=str(src),out_sha256=h,
          estimates_sha256=sha(src/'estimates.dat'),tech3_sha256=sha(src/'tech3.dat'))
    (ROOT/'upstream').mkdir(exist_ok=True)
    (ROOT/'upstream/START_SOURCES.json').write_text(json.dumps(sources,indent=2),encoding='utf-8')
    print('BOUND_START_SOURCES',len(sources),flush=True)


if __name__=='__main__':main()
