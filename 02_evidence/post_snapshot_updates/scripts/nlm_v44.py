"""最终PDF对的独立全文三审；不沿用旧稿回执，不重复失败指纹。"""
from review_workspace import OUT, readj, writej, sha
from pathlib import Path
import sys, subprocess
sys.path.insert(0, r'C:\Users\LZHS\.agents\skills\mplusautomation-guide\scripts')
from nlm_reliability import compact_json, run_query

NLM = r'C:\Users\LZHS\.local\bin\nlm.exe'
ROOT = OUT / 'reviews/v44'
ROOT.mkdir(exist_ok=True)
PDF_RECEIPT = OUT / 'manuscript/v44_pdf_receipt.json'
NOTEBOOK_TITLE = 'CFPS 七项意见最终候选 v44-v37 20261005'

def call(name, args):
    r = subprocess.run([NLM, *args, '--profile', 'default'], capture_output=True, timeout=420)
    stdout, stderr = r.stdout.decode('utf-8', 'replace'), r.stderr.decode('utf-8', 'replace')
    writej(ROOT / (name + '.json'), {'returncode': r.returncode, 'stdout': stdout, 'stderr': stderr})
    assert r.returncode == 0, name
    obj = compact_json(stdout)
    assert isinstance(obj, (dict, list)), name
    return obj

def upload():
    receipt = readj(PDF_RECEIPT)
    nbfile = ROOT / 'notebook.json'
    if nbfile.exists():
        nb = readj(nbfile)
    else:
        obj = call('notebook_create_raw', ['notebook', 'create', NOTEBOOK_TITLE, '--json'])
        nb = {'id': obj.get('id') or obj.get('notebook_id')}
        assert nb['id']
        writej(nbfile, nb)
    sources = []
    for row in receipt['records']:
        pdf = Path(row['pdf'])
        assert sha(pdf) == row['pdf_sha256']
        record = ROOT / (pdf.stem + '_source.json')
        if record.exists():
            s = readj(record)
        else:
            obj = call(pdf.stem + '_upload_raw', ['source', 'add', nb['id'], '--file', str(pdf), '--wait', '--wait-timeout', '360', '--json'])
            s = {'id': obj.get('id') or obj.get('source_id'), 'filename': pdf.name, 'path': str(pdf), 'sha256': sha(pdf)}
            assert s['id']
            writej(record, s)
        sources.append(s)
        print('SOURCE_READY', pdf.name, s['id'], flush=True)
    writej(ROOT / 'source_manifest.json', {'notebook_id': nb['id'], 'pdf_only': True, 'sources': sources})
    print('FINAL_PAIR_UPLOADED', nb['id'], flush=True)

def query(n, concise=False):
    man = readj(ROOT / 'source_manifest.json')
    ss = man['sources']
    pdf_records = readj(PDF_RECEIPT)['records']
    page_note = '正文' + str(pdf_records[0]['pages']) + '页、附录' + str(pdf_records[1]['pages']) + '页'
    for s in ss:
        assert sha(s['path']) == s['sha256']
    scope = {1: '结构与数值：审查章节、表图编号和交叉引用、样本口径、参数符号、脚注、正文与附录数值对应。先核对表题中的标准化尺度及分模型范围，再判断数值或索引是否冲突。', 2: '方法与解释：审查量尺、时间基底、缺失/插补、死亡截断、模型诊断、调节/因果语言、讨论与假设的支持边界、引文用途。区别理论假设和实证断言。', 3: '格式与一致性：审查标题、符号、表注标记、表格跨页、引用附录、残留矛盾和无来源断言。PDF文字抽取中的脚注或上标粘连须与实际排版区别；不能据此要求删除正确注号。'}[n]
    prompt = ('对[' + ss[0]['filename'] + ']和[' + ss[1]['filename'] + ']执行全文第' + str(n) + '审，不限于新增补表。' + scope +
              '请分开给出正文审阅和附录审阅，两部分各直接引用对应PDF的原文证据，最后核对两者一致性；必须实际使用并引用两份来源。列真实问题时给文件名、实际PDF页码（' + page_note + '）及短引；未能核查处明确说明。已标明的历史记录、不可接受解及科学开放项不是未标示错误，不要求改成显著结果。不超过1200字。末尾输出NEW_ISSUES_COUNT: N和A5_NO_NEW_ISSUES: YES或NO。')
    suffix = '_full'
    if concise:
        scope = {1: '全文表图编号、交叉引用、样本数、参数、尺度及脚注是否有真实矛盾', 2: '全文的方法、统计解释、量尺、时间单位、插补、死亡缺失、模型诊断、因果措辞和引文用途是否存在未标示问题', 3: '全文标题、符号、表注、跨页表格、附录引用及结论是否存在错漏或无来源断言'}[n]
        prompt = ('请审阅完整的[' + ss[0]['filename'] + ']与[' + ss[1]['filename'] + ']：' + scope + '？不要只检查新增补表。分别引用两份PDF证据，区分已标注科学局限与真正错误；最多600字，问题需给原文定位，无问题明确说明。末尾NEW_ISSUES_COUNT: N；A5_NO_NEW_ISSUES: YES或NO。')
        suffix = '_full_concise'
    result = run_query(NLM, man['notebook_id'], prompt, [s['id'] for s in ss], ROOT / f'pass{n}{suffix}', filename=ss[0]['filename'], profile='default', timeout=180, attempts=1)
    print('V44_REVIEW', n, result['status'], flush=True)
    if result['status'] != 'PASS':
        raise RuntimeError('审阅传输或来源核验未通过；保留回执')

if __name__ == '__main__':
    if sys.argv[1] == 'upload':
        upload()
    else:
        query(int(sys.argv[1]), '--concise' in sys.argv)
