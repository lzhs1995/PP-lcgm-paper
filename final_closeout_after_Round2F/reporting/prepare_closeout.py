"""归档只读依据并展开文稿；不调用任何统计估计程序。"""
from pathlib import Path
import hashlib, json, shutil, zipfile
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / 'round2F_20261011'
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    records=[]
    for folder in ['baseline/manuscripts','baseline/reviewer_inputs','working','manuscript/delivery','reports','evidence','runtime']:
        (ROOT/folder).mkdir(parents=True,exist_ok=True)
    for p in (OLD/'manuscript/delivery').iterdir():
        if p.is_file():
            dst=ROOT/'baseline/manuscripts'/p.name
            if not dst.exists(): shutil.copy2(p,dst)
            assert sha(p)==sha(dst)
            records.append(dict(source=str(p),snapshot=str(dst.relative_to(ROOT)),sha256=sha(p)))
    for name in ['Astra_Final_Closeout_Plan..md','给Astra的最终收尾任务书..md','CONVERGENCE_TRACE_2F_by_Claude..csv']:
        p=Path('C:/Users/LZHS/Downloads')/name
        dst=ROOT/'baseline/reviewer_inputs'/name
        if not dst.exists(): shutil.copy2(p,dst)
        assert sha(p)==sha(dst)
        records.append(dict(source=str(p),snapshot=str(dst.relative_to(ROOT)),sha256=sha(p)))
    (ROOT/'reports/FROZEN_INPUTS.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    for kind,name in [('main','PP_LGCM_review_v51_round2F.docx'),('appendix','PP_LGCM_appendix_review_v43_round2F.docx')]:
        dest=ROOT/'working'/kind;dest.mkdir(exist_ok=True)
        with zipfile.ZipFile(ROOT/'baseline/manuscripts'/name) as z:
            tree=E.fromstring(z.read('word/document.xml'))
        nodes=list(tree.find('w:body',NS));rows=[]
        for i,n in enumerate(nodes):
            t=''.join(n.xpath('.//w:t/text()',namespaces=NS))
            rows.append(dict(index=i,tag=E.QName(n).localname,text=t,fields=len(n.findall('.//w:instrText',NS))))
            path=dest/f'{i:03d}.xml'
            if not path.exists(): path.write_bytes(E.tostring(n,encoding='UTF-8',pretty_print=True))
        (dest/'index.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
        (dest/'index.txt').write_text('\n'.join(f"{x['index']:03d} [{x['tag']};fields={x['fields']}] {x['text']}" for x in rows),encoding='utf-8')
        print(kind,len(nodes),'nodes',sum(x['fields'] for x in rows),'fields')
    print('FROZEN_INPUTS',len(records),'NO_NEW_ESTIMATION')
if __name__=='__main__': main()
