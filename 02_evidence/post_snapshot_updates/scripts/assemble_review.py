"""组装已直接编辑的XML；只转移指定w:t，保留引文域/公式/图表/ZIP其他部件。"""
from review_workspace import OUT, MAIN, APP, NS, sha, readj, writej, csvout
from lxml import etree as E
from pathlib import Path
from copy import deepcopy, copy
import csv, zipfile

ROOT=OUT/'manuscript';EDIT=ROOT/'xml_edits';W='{'+NS['w']+'}'
def readcsv(name):
    return list(csv.DictReader((OUT/'summaries'/name).open(encoding='utf-8-sig')))
def canon(el): return E.tostring(el,method='c14n')
def text(el):return ''.join(el.xpath('.//w:t/text()',namespaces=NS))
def paragraph(s,bold=False):
    p=E.Element(W+'p');r=E.SubElement(p,W+'r');rp=E.SubElement(r,W+'rPr')
    E.SubElement(rp,W+'sz',{W+'val':'20'})
    if bold:E.SubElement(rp,W+'b')
    E.SubElement(r,W+'t').text=s
    return p
def table(headers,rows):
    tbl=E.Element(W+'tbl');pr=E.SubElement(tbl,W+'tblPr')
    E.SubElement(pr,W+'tblW',{W+'w':'8800',W+'type':'dxa'})
    E.SubElement(pr,W+'tblLayout',{W+'type':'fixed'})
    borders=E.SubElement(pr,W+'tblBorders')
    for name in ['top','left','bottom','right','insideH','insideV']:E.SubElement(borders,W+name,{W+'val':'single',W+'sz':'4',W+'color':'B0B0B0'})
    widths=[8800//len(headers)]*len(headers);widths[-1]+=8800-sum(widths)
    grid=E.SubElement(tbl,W+'tblGrid')
    for width in widths:E.SubElement(grid,W+'gridCol',{W+'w':str(width)})
    for i,row in enumerate([headers]+rows):
        tr=E.SubElement(tbl,W+'tr')
        if i==0:E.SubElement(E.SubElement(tr,W+'trPr'),W+'tblHeader')
        for value,width in zip(row,widths):
            tc=E.SubElement(tr,W+'tc');tp=E.SubElement(tc,W+'tcPr');E.SubElement(tp,W+'tcW',{W+'w':str(width),W+'type':'dxa'});tc.append(paragraph(str(value),i==0))
    return tbl
def num(x):
    try:return f'{float(x):.3f}'
    except (ValueError,TypeError):return 'NA'

sources=[];changes=[]
for label,src,dst in [('main',MAIN,ROOT/'PP_LGCM_review_v43_NOT_RELEASED.docx'),('appendix',APP,ROOT/'PP_LGCM_appendix_review_v37_NOT_RELEASED.docx')]:
    assert not dst.exists(),dst
    with zipfile.ZipFile(src) as z:
        xml=z.read('word/document.xml');tree=E.fromstring(xml);before=deepcopy(tree)
        paras=tree.xpath('//w:p',namespaces=NS)
        for fragment in sorted(EDIT.glob(f'{label}_p*.xml')):
            idx=int(fragment.stem.split('_p')[1]);orig=paras[idx]
            edited=E.parse(str(fragment)).getroot()
            aa=orig.xpath('.//w:t',namespaces=NS);bb=edited.xpath('.//w:t',namespaces=NS)
            assert len(aa)==len(bb)
            for a,b in zip(aa,bb):
                assert a.attrib==b.attrib
                if a.text!=b.text:
                    changes.append({'document':label,'paragraph_index':idx,'old':a.text or '', 'new':b.text or ''})
                    a.text=b.text
        if label=='main':
            # 回退全部获准文字后必须与原文结构完全一致。
            reverted=deepcopy(tree)
            for idx in [65,1016,1186,2734,2745]:
                pa=reverted.xpath('//w:p',namespaces=NS)[idx];pb=before.xpath('//w:p',namespaces=NS)[idx]
                for a,b in zip(pa.xpath('.//w:t',namespaces=NS),pb.xpath('.//w:t',namespaces=NS)):a.text=b.text
            assert canon(reverted)==canon(before)
        else:
            body=tree.find(W+'body');addition=E.parse(str(EDIT/'appendix_supplement.xml')).getroot()
            contents=[deepcopy(p) for p in addition]
            t1=[r for r in readcsv('T1_wave_scale_sample.csv') if r['sample']=='analysis_all']
            contents += [paragraph('补表R1　原3274人队列各期有效观测的抑郁得分',True),table(['年份','口径','有效N','均值','标准差'],[[r['year'],'CESD8' if 'CESD8' in r['scale'] else 'CESD20',r['n'],num(r['mean']),num(r['sd'])] for r in t1])]
            status=readcsv('sensitivity_current_status.csv');states={'REVIEWABLE':'正常终止；审阅','INADMISSIBLE':'不可接受解','NONCONVERGED':'未收敛'}
            contents += [paragraph('补表R2　八项敏感性模型的终态',True),table(['模型','量尺','窗口','N','终态'],[['单变量' if r['family']=='univariate' else '直接关联',r['scale'],'五期' if r['window']=='five' else '四期',r['N'],states[r['status']]] for r in status])]
            params=[r for r in readcsv('sensitivity_parameters.csv') if r['batch']=='sensitivity_input_repair' and r['paramHeader'] in ['IY.ON','SY.ON'] and r['param'] in ['IX','SX']]
            rows=[]
            for r in params:
                short=r['model_id'].removeprefix('direct_').replace('_five','五期').replace('_four','四期')
                path={'IY.ON':'抑郁I←','SY.ON':'抑郁S←'}[r['paramHeader']]+{'IX':'亲近I','SX':'亲近S'}[r['param']]
                rows.append([short,path,num(r['est']),num(r['se']),f"[{num(r['ci_low_diagnostic'])}, {num(r['ci_high_diagnostic'])}]",'<.001' if float(r['pval'])==0 else num(r['pval'])])
            contents += [paragraph('补表R3　四项直接关联模型的关键路径（N=1981）',True),table(['模型','路径','系数','SE','95%近似区间','p'],rows),paragraph('注：I/S表示潜截距/变化因子。CESD8五期为不可接受解，其打印参数仅供诊断留痕，不作推断；其余模型的拟合仍有分歧。区间按打印系数±1.96×稳健SE计算；打印为0.000的p记为<.001。五期与四期潜截距的参考年不同。')]
            for content in contents:
                sect=body.find(W+'sectPr')
                body.insert(body.index(sect) if sect is not None else len(body),content)
            # 原附录内容逐节点保留，新增内容只在最终节属性之前。
            orig_children=list(before.find(W+'body'));old_nonsect=[p for p in orig_children if p.tag!=W+'sectPr']
            assert all(canon(a)==canon(b) for a,b in zip(old_nonsect,list(body)[:len(old_nonsect)]))
        assert tree.xpath('//w:instrText/text()',namespaces=NS)==before.xpath('//w:instrText/text()',namespaces=NS)
        assert [canon(x) for x in tree.xpath('//w:fldSimple',namespaces=NS)]==[canon(x) for x in before.xpath('//w:fldSimple',namespaces=NS)]
        tables_before=before.xpath('//w:tbl',namespaces=NS);tables_after=tree.xpath('//w:tbl',namespaces=NS)
        assert all(canon(a)==canon(b) for a,b in zip(tables_before,tables_after))
        payload=E.tostring(tree,encoding='UTF-8',xml_declaration=True,standalone=True)
        with zipfile.ZipFile(dst,'x') as target:
            for m in z.infolist():target.writestr(copy(m),payload if m.filename=='word/document.xml' else z.read(m.filename))
        with zipfile.ZipFile(dst) as new:
            assert new.testzip() is None
            assert all(z.read(n)==new.read(n) for n in z.namelist() if n!='word/document.xml')
    sources.append({'source':str(src),'source_sha256':sha(src),'output':str(dst),'output_sha256':sha(dst),'original_tables_preserved':len(tables_before),'total_tables':len(tables_after),'field_codes_identical':True,'other_zip_parts_byte_identical':True})
csvout(ROOT/'change_log.csv',changes)
writej(ROOT/'assembly_receipt.json',{'status':'PASS','records':sources,'changed_text_nodes':len(changes),'scientific_release':False})
print({'status':'PASS','changed_text_nodes':len(changes),'files':[x['output'] for x in sources]})
