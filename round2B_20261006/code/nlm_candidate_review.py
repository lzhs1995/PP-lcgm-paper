"""仅复核已上传的同版候选PDF；记录确切来源ID和文件哈希。"""
from pathlib import Path
import subprocess,json,hashlib,os
root=Path('C:/Users/LZHS/pp_lgcm_review/round2B_20261006')
query='''请只依据所选两份PDF，审查这轮PP-LGCM审计候选稿的文字与表格一致性。它们不是正式实证定稿，分层MI及目标队列主模型尚待验收，不要因文件可读就宣布七项全部解决。
请检查：1 年龄是否统一为61—75与76岁及以上，wave是否仍误称基期控制或控制失访；2 正文修正CESD8的聚类数值是否自洽（p=.290、截距SE=.101、方差SE=.657、校正比较p=.038），附录前两表明确保留前轮未聚类版本，勿将有标签的不同版本当成同一次模型；3 98张历史表及正文旧结果是否有明确状态标记；4 连续得分/给定切点二分交互是否仍混称一般线性/非线性机制，是否还有完全不显著的绝对判断；5 附录排行差和A系列列名是否与表内增长因子/交互项对应；6 收入有无与收入高低是否混淆；7 组内星号是否仍被当成H4.2b组间差异检验；8 引文功能、缺失处理、版本叙述还存在哪些实质矛盾。不要假装已读取CFPS微观数据、运行Mplus或核实引用原文。请列具体原句、PDF物理页和修改建议，区分已修与仍待处理；另指出版面/乱码问题。保留旧系数供审计不表示这些系数有效。'''
(root/'runtime/nlm_candidate_question.txt').write_text(query,encoding='utf8')
bindings=[]
for name,sid in [('PP_LGCM_review_v47_round2B_build02_NOT_RELEASED.pdf','a275d308-2fe6-4257-8bf5-b7e507cde74e'),('PP_LGCM_appendix_review_v39_round2B_build02_NOT_RELEASED.pdf','9b1d44bc-a637-4731-8332-9cfb3eab7e20')]:
 p=root/'manuscript'/name;bindings.append({'file':name,'source_id':sid,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
env=os.environ.copy();env['PYTHONIOENCODING']='utf-8'
args=['C:/Users/LZHS/.local/bin/nlm.exe','notebook','query','f32d4889-aa8d-43f9-b784-874925f946eb',query,'--source-ids',','.join(b['source_id'] for b in bindings),'--json']
print('NLM candidate review started',flush=True)
r=subprocess.run(args,capture_output=True,env=env)
(root/'runtime/nlm_candidate_review_raw.json').write_bytes(r.stdout)
(root/'runtime/nlm_candidate_review_stderr.txt').write_bytes(r.stderr)
for b in bindings:assert hashlib.sha256((root/'manuscript'/b['file']).read_bytes()).hexdigest()==b['sha256']
(root/'runtime/nlm_candidate_binding.json').write_text(json.dumps({'returncode':r.returncode,'notebook_id':args[3],'bindings':bindings,'scope':'editorial candidate review; no final scientific adoption'},ensure_ascii=False,indent=2),encoding='utf8')
print('NLM returncode',r.returncode,flush=True)
