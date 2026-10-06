from review_workspace import OUT, readj, writej, csvout
import csv,shutil
p=OUT/'opinion_decisions.csv';rows=list(csv.DictReader(p.open(encoding='utf-8-sig')))
archive=OUT/'opinion_decisions_initial.csv'
if not archive.exists():shutil.copy2(p,archive)
updates={
'1a':('IMPLEMENTED_CANDIDATE','正文1016：加入实际载荷和预测均值，保留形状选择分歧'),
'1b':('EXECUTED_WITH_SCIENTIFIC_LIMITS','八规格终态：3 reviewable、3 inadmissible、2 nonconverged；正文与附录补表R2/R3已纳入，未宣称稳健'),
'1c':('IMPLEMENTED_CANDIDATE','附录报告有效波数及死亡/未知边界'),
'1d':('IMPLEMENTED_CANDIDATE','正文65纠正2016长短版；附录明确非官方推断'),
'2a':('VERIFIED_RETAINED','逐记录恒差8，保留8—32主分析'),
'2b':('VERIFIED_IMPLEMENTED','官方20—80减20，5304完整长卷恒等验证；附录补表R1'),
'3a':('VERIFIED_RETAINED','保留v42已修正的方差解释，不用显著性作为选择门槛'),
'3b':('EXECUTED_WITH_SCIENTIFIC_LIMITS','新增CESD8五期直接模型SY残差负方差；保留旧11规格诊断，不做自动交互'),
'4a':('IMPLEMENTED_CANDIDATE','报告CFI/TLI与RMSEA/SRMR分歧及不可接受解'),
'4b':('DIAGNOSTIC_LIMIT_RECORDED','新模型保留RESIDUAL，未生成修正指数或按MI平均'),
'5a':('IMPLEMENTED_CANDIDATE','正文2745撤回天花板必然保守及未经测量的文化归因'),
'5b':('VERIFIED_RETAINED','既有25行107格标签保留，未重改'),
'6a':('EVIDENCE_LIMIT_RECORDED','未确认参考作者原语法，未作同算法或造假推断'),
'6b':('IMPLEMENTED_CANDIDATE','正文1186和附录报告得分SE及方法不等价'),
'6c':('VERIFIED_IMPLEMENTED','逐切点等值人数、高低组人数已写入，历史/修正得分分开'),
'6d':('EVIDENCE_LIMIT_RECORDED','未知三过程失败历史不补造；本轮输入拒绝和估计不收敛分别登记'),
'6e':('SCIENTIFIC_INFERENCE_OPEN','保留25模型比较和MI/协方差边界；未发布正式D2/Wald'),
'7a':('IMPLEMENTED_CANDIDATE','正文2734明确H4.2b未获一致支持，需直接差异检验'),
'7b':('VERIFIED_RETAINED','保留未测量机制的理论解释边界')}
for r in rows:r['execution_status'],r['implemented_or_remaining']=updates[r['issue_id']]
csvout(p,rows)
text='# 七项审阅意见：执行后处置\n\nCFPS复现已完成；本轮为后续修订。以下为本地证据与修订候选状态，NLM和科学放行另行登记。CHARLS暂停。\n\n'
for r in rows:text+=f"## {r['issue_id']} {r['topic']}\n\n状态：{r['execution_status']}。{r['implemented_or_remaining']}。\n\n原审阅裁定：{r['disposition']}。证据：{r['evidence_files']}。\n\n"
(OUT/'OPINION_DECISIONS.md').write_text(text,encoding='utf-8')
for name in ['opinion_decisions.csv','OPINION_DECISIONS.md']:shutil.copy2(OUT/name,OUT/'audit_stage1'/name)
print('19项执行后处置已保存')
