"""核对当前DOCX、逐格PDF和原始引用字段；生成逐页视觉审阅图。"""
from pathlib import Path
import json
import zipfile
from lxml import etree as E
import pdf_checks as p

ROOT=Path(__file__).resolve().parents[1]


def main():
    out=ROOT/'manuscript/delivery';expected=json.loads((out/'expected_tables.json').read_text())
    exports=json.loads((out/'native_word_export.json').read_text())
    receipts=json.loads((out/'revision_receipts.json').read_text())
    # 边界表只能来自CFPS调用，不能将合成接口结果写成实证诊断。
    boundary=[json.loads(p.read_text(encoding='utf-8-sig')) for p in (ROOT/'models').glob('*/receipt.json')]
    boundary=[r for r in boundary if r['sample']=='CFPS' and r['spec'] in ('E0B','E1B')]
    table20=next(t for t in expected if t['title'].startswith('附表A20'))
    assert len(table20['rows'])==len(boundary)==2
    assert sorted(r[0] for r in table20['rows'])==sorted(r['spec'] for r in boundary)
    for row in table20['rows']:
        source=next(r for r in boundary if r['spec']==row[0])
        assert abs(float(row[3])-source['seconds'])<=.0051
    results=[]
    for export,receipt in zip(exports,receipts):
        kind='appendix' if 'appendix' in export['document'] else 'main'
        src=out/export['document'];pdf=out/export['pdf']
        assert p.sha(src)==export['docx_sha256']==receipt['docx_sha256']
        assert p.sha(pdf)==export['pdf_sha256']
        with zipfile.ZipFile(src) as z:
            assert z.testzip() is None
            tree=E.fromstring(z.read('word/document.xml'))
        old=ROOT/'reporting/context_evidence/round2D/manuscript/delivery'/receipt['source']
        with zipfile.ZipFile(old) as z:ot=E.fromstring(z.read('word/document.xml'))
        assert tree.xpath('.//w:instrText/text()',namespaces=p.NS)==ot.xpath('.//w:instrText/text()',namespaces=p.NS)
        ts=tree.findall('.//w:body/w:tbl',p.NS);want=[t for t in expected if t['document']==kind]
        assert len(ts)==len(want)==export['tables']
        for actual,e in zip(ts,want):assert p.xml_rows(actual)==[e['headers']]+e['rows'],e['title']
        check=p.validate_pdf_tables(pdf,want,kind)
        (out/(kind+'_pdf_cell_validation.json')).write_text(json.dumps(check,ensure_ascii=False,indent=2),encoding='utf-8')
        rendered=p.render(pdf,out/'visual',kind)
        result=dict(document=export['document'],pdf=export['pdf'],pages=export['pages'],tables=len(ts),
          cells=sum(len(row) for t in want for row in [t['headers']]+t['rows']),
          docx_sha256=p.sha(src),pdf_sha256=p.sha(pdf),docx_tables_match=True,
          pdf_tables_match=check['passed'],citations_preserved=True,rendering=rendered)
        results.append(result)
        print(kind,'pages',export['pages'],'tables',len(ts),'PDF_CELLS',check['passed'],flush=True)
        if check['errors']:print(json.dumps(check['errors'][:1],ensure_ascii=False),flush=True)
    status='PASS' if all(r['pdf_tables_match'] for r in results) else 'FAIL'
    (out/'manuscript_validation.json').write_text(json.dumps(dict(status=status,documents=results,
      stage='PARTIAL_RESEARCH_STAGE_FOR_EXTERNAL_REVIEW',visual_review='PENDING'),ensure_ascii=False,indent=2),encoding='utf-8')
    if status!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
