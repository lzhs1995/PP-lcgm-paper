"""由真实终态生成阶段摘要、最终耗时与未执行台账；不运行任何模型。"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics

ROOT = Path('C:/Users/LZHS/pp_lgcm_review/round2D_20261008')
OUT = ROOT/'reports_final'
Z_NAMES = {'SD':'标准差','SEXGAP':'性别差','OLDEST':'老大差','SONGAP':'长子差'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as handle:
        return list(csv.DictReader(handle))


def write_rows(path,data):
    assert data
    with path.open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(data[0]))
        writer.writeheader();writer.writerows(data)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(headers,data):
    def esc(x):
        return str(x).replace('|','\\|').replace('\n','<br>')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |']+
                     ['| '+' | '.join(esc(x) for x in row)+' |' for row in data])


def main():
    terminal=read(ROOT/'runtime/queue_terminal.json')
    assert terminal['reason']=='USER_APPROVED_STAGE_BUDGET_STOP'
    assert read(ROOT/'evidence/independent_verification.json')['status']=='PASS'
    assert read(ROOT/'audit/stage_closeout_20261009/terminal_process_validation.json')['status']=='PASS'
    closure=read(ROOT/'audit/stage_closeout_20261009/closeout_contract.json')
    calls=rows(OUT/'MODEL_EXECUTION.csv')
    assert len(calls)==terminal['call_count']
    real=[c for c in calls if c['category']!='SYNTHETIC']
    assert not any(c['spec'].startswith(('E','H4')) or c['attempt']=='completecase' for c in real)
    states=rows(ROOT/'results/family_status.csv')
    assert len(states)==19 and not any(s['eligible'].upper()=='TRUE' for s in states)
    timings=[]
    for c in calls:
        timings.append(dict(id=c['id'],z=c['z'],spec=c['spec'],member=c['member'],attempt=c['attempt'],
            synthetic=c['category']=='SYNTHETIC',status=c['status'],
            elapsed_seconds=float(c['seconds']),elapsed_hours=float(c['seconds'])/3600,
            kind=c['kind'],integration_dimensions=c['integration_dimensions'],
            directory=c['directory'],input_sha256=c['input_sha256'],output_sha256=c['output_sha256']))
    write_rows(OUT/'PERFORMANCE_FINAL.csv',timings)
    latent=[r for r in timings if not r['synthetic'] and r['spec']=='D1']
    linear=[r for r in timings if not r['synthetic'] and r['spec']=='D0']
    d0_variances=[]
    for model in linear:
        for parameter in rows(ROOT/model['directory']/'parameters_high_precision.csv'):
            if parameter['matrix'].upper()=='PSI' and parameter['row']==parameter['column']:
                d0_variances.append(dict(id=model['id'],z=model['z'],member=model['member'],attempt=model['attempt'],
                    model_status=model['status'],factor=parameter['row'],estimate=parameter['estimate'],se=parameter['se'],
                    negative=float(parameter['estimate'])<0,role='Diagnostic variance, not a reportable interaction effect',
                    output_sha256=model['output_sha256']))
    assert len(d0_variances)==6*len(linear)
    write_rows(ROOT/'audit/stage_closeout_20261009/D0_VARIANCE_DIAGNOSTICS.csv',d0_variances)
    all_seconds=sum(r['elapsed_seconds'] for r in timings)
    latent_seconds=sum(r['elapsed_seconds'] for r in latent)
    disposition=[]
    for s in states:
        related=[r for r in real if r['z']==s['z'] and r['spec']==s['spec']]
        for k in range(1,11):
            tried=[r for r in related if int(r['member'])==k]
            state=('ATTEMPTED_NOT_POOLABLE' if tried else 'NOT_STARTED_AFTER_FAMILY_STOP' if related else 'NOT_STARTED_STAGE_DEFERRED')
            disposition.append(dict(z=s['z'],spec=s['spec'],member=k,execution_status=state,
                actual_calls=len(tried),attempts=';'.join(r['id'] for r in tried),
                terminal_statuses=';'.join(r['status'] for r in tried),family_status=s['status'],
                family_reportable=False,reason=s['reason'],
                scientific_interpretation='No hypothesis test from this incomplete or inadmissible family'))
    write_rows(OUT/'TARGET_DISPOSITIONS.csv',disposition)
    task_deferred=[dict(target='SD complete observed covariates latent diagnostic',status='NOT_STARTED_STAGE_DEFERRED',
                       reason='User-approved phase closure; no additional latent fit'),
                   dict(target='six 1/2/4 processor timing probes',status='DEFERRED_BEFORE_FIRST_PROBE',
                       reason='Waiting job cancelled before a probe; no measured speedup'),
                   dict(target='window / scale / Y-shape sensitivity',status='NOT_EXECUTED',
                       reason='Previously deferred and not reopened'),
                   dict(target='interaction-compatible MI / household bootstrap',status='NOT_EXECUTED',
                       reason='Separate method question; previous data-layer checks remain valid')]
    write_rows(OUT/'DEFERRED_ADDITIONAL_WORK.csv',task_deferred)
    details=rows(OUT/'FAMILY_EXECUTION_DETAILS.csv')
    d1=[next(r for r in details if r['z']==z and r['spec']=='D1') for z in Z_NAMES]
    sw=[r for r in rows(ROOT/'provenance_SW/conditional_MI_paths.csv') if r['spec']=='SW']
    sw_names={'bii':'亲近度基期→抑郁基期','bis':'亲近度基期→抑郁变化','bss':'亲近度变化→抑郁变化','bsyiy':'抑郁基期→抑郁变化'}
    sw_table=table(['路径','估计','95%条件MI区间','P'],[
        [sw_names[r['label']],f"{float(r['estimate']):.4f}",f"[{float(r['lower']):.4f}, {float(r['upper']):.4f}]",f"{float(r['p']):.4f}"] for r in sw])
    finish=read(ROOT/closure['current_attempt_directory']/'receipt.json')
    final_hours=float(finish['seconds'])/3600
    last=[r for r in real if r['id']==closure['current_attempt']][0]
    audit=read(ROOT/'evidence/independent_verification.json')
    completed_at=dt.datetime.now(dt.timezone.utc).isoformat()
    summary=f'''# Round2D阶段结论与网页端评议重点

本次完成的是**证据收口与阶段交付**。论文七个问题未全部解决；四项潜调节尚无完整、可采用的MI推断，不能据此说四种调节均不存在。观测2012年替代、H4.2b资源比较和六次短性能探针均未执行，现提请ChatGPT网页端与Claude网页端共同评议下一步。

## 已经可以保留的成果

CES-D共同八题计分与实际入口、基期来源、家庭共享变量插补一致性、修正得分SE导出缺口均已有对应修复证据。SW可作为平均亲近度—抑郁的主要父工作模型，C1保留为强约束敏感性，XLIN不采用。这些事实不需要因潜交互失败再从头清洗或重跑父模型。

以下复用Round2C全部十份的条件MI结果，本轮没有重新拟合父模型：

{sw_table}

基期负向关联可在该工作模型下报告；变化关联的区间很宽，尚不能确定方向和幅度。SW合法不证明新增第三轨迹或交互也合法。

## 本轮实际运行到哪里

本轮共{len(calls)}次实际调用，含{len(calls)-len(real)}次合成接口检查和{len(real)}次CFPS调用；后者包括{len(linear)}次三过程无交互和{len(latent)}次潜交互。调用、科学规格和不同MI成员是不同计数单位。全部登记调用已有终态回执，未删除失败成员。

{table(['潜交互Z','实际MI成员数','最终分支证据'],[[Z_NAMES[r['z']],r['distinct_members_attempted'],r['detail']] for r in d1])}

最后的长子差起点核查耗时{float(finish['seconds']):.3f}秒（{final_hours:.3f}小时），终态为`{finish['status']}`：{last['diagnostic_detail']}。

老大差D0前五份可用，随后第六份及其修复未通过；不能删除第六份后合并前五份。四个D0家族与四个D1家族均未形成完整可采用MI结果。**三过程D0尚未加入交互，已经出现不合法解；因此，科学识别问题不能全部归因于LMS数值积分。** [D0方差诊断表](audit/stage_closeout_20261009/D0_VARIANCE_DIAGNOSTICS.csv)将{len(d0_variances)}个增长因子方差绑定至对应输出，其中{sum(r['negative'] for r in d0_variances)}项为负，仅作定位，不作有效研究效应。潜交互的积分精度、起点和完整十份成员验收链没有完成，不能将模板或合成测试当成这些条件已经通过。

[模型索引](MODEL_INDEX.md)链接逐次INP/OUT、终态与高精度保存文件；[家族说明](FAMILY_EXECUTION_DETAILS.csv)区分单份与完整家族；[逐目标台账](TARGET_DISPOSITIONS.csv)包含预定19类规格×10份MI的190个目标位置。该190行不是190次实际估计，也不表示全部位置都应继续运行。

## 为什么停止追加

{len(linear)}次实际无交互调用的中位耗时为{statistics.median(r['elapsed_seconds'] for r in linear):.3f}秒；{len(latent)}次实际潜交互调用合计{latent_seconds/3600:.3f}小时，中位耗时{statistics.median(r['elapsed_seconds'] for r in latent)/3600:.3f}小时。潜交互占全部已结束引擎计时的{100*latent_seconds/all_seconds:.2f}%，不是占全部项目时间的比例，也不是同一模型的受控测速结果。逐次来源见[最终耗时表](PERFORMANCE_FINAL.csv)。

此前Windows采样发现Mplus主要使用一个核，R等待worker同期CPU增量为零。生产代码固定PROCESSORS=1且未及时校准多核，是执行策略可改进之处；现有证据不支持将数小时主要归于R循环、反复读取数据或内存容量不足。采样不排除其他时段竞争或分页。当前两维标准积分每维15点，共225节点；Monte Carlo5000点不保证更快。纯EM修复也出现长步骤且最终不合法，多核或换算法不能自动解决负方差和信息矩阵问题。

历史[性能复核](audit/PERFORMANCE_REVIEW_20261009.md)保留其采样时间、23份终态时的统计及官方资料来源；最新全部终态计数以本页及PERFORMANCE_FINAL.csv为准。六个1/2/4核探针已准备且等待作业曾提交，但在首次探针前取消；**没有实测加速倍数，未改生产核数**。

按用户批准的收口方案，保留最后在途尝试的原六小时时限，在真实终态后停止原worker，并阻止后续自动准入。这是新的阶段计算范围，**不是原168小时总上限已经耗尽**，也不是根据P值选择停止。完整原合同与新增[阶段合同](audit/stage_closeout_20261009/closeout_contract.json)均保留。

## 未竟问题与希望两端回应的内容

1. 在现有失败证据下，继续潜在IZ路线的预期收益是否足以支持一次有界小试？请给出具体假说、最多调用次数、总时限和退出标准，避免无止境增加迭代或积分点。
2. 六个增长因子的识别、共享评分及分母、零值集中和连续高斯近似分别可能造成什么问题？哪些能够用现有参数、残差与控制台日志区分，哪些确需新估计？不要把某个推测写成唯一原因。
3. 下一次是否先做最多12分钟的1/2/4核短校准、再从合法父模型映射公共参数起点？短探针只测计算成本，正式采用仍需完整结果及SE数值一致性；不重启已关闭分支作为测速。
4. 是否优先开展SW加观测2012年Z₀的SD试运行？它改变估计对象，但保留原理论的一个可解释版本。请说明潜在初始状态与实际基期状态的区别，并制定最小验收链；其余三个Z不按SD的P值决定是否检验。
5. MI与潜交互的相容性如何形成可实施的最小敏感性？保留已通过的家庭共同值规则，勿只替换旧插补列。若提议因子得分或Bayes，请列清不确定性、模型分布和研究对象的变化。
6. H4.2b尚未实际检验。恢复时直接检验三阶参数／组间差异，区分“有个人收入”和“高收入”，不能比较两个组的星号。量尺、窗口和Y形状敏感性仍应在可辩护工作设计下有限推进。
7. 正文v49／附录v41阶段稿是否准确区分可报告结果、失败、延期和宽区间？哪些具体问题已经关闭，哪些达到父模型层面，哪些仍不能裁决？请引用包内文件，形成有终点的共同建议。

## 文件与复核边界

先读[完整报告](REPORT.md)、[七项意见](SEVEN_ISSUES.csv)、[网页端说明](FOR_WEB_REVIEWERS.md)，再读[正文文字](manuscripts/main_readable.md)、[附录文字](manuscripts/appendix_readable.md)及同目录DOCX/PDF。文稿是本批同步的阶段稿，原71个保留Zotero引用域与1个明确移除记录可核验；未声称全部论文验收或NotebookLM最终验收完成。

所有ZIP解压到同一目录。包清单给出字节数与SHA-256，每包不超过25,000,000字节；FILE_MANIFEST逐项列出文件，清单自身不递归列入。公开包无微观DAT、真实PID/FID、逐人得分或MI对象。estimates.dat与tech3.dat是聚合参数保存文件。审阅者可复算保存统计量，不能据此声称已在云端重新估计CFPS个人记录。

独立复核入口为`code/09_independent_verify.py --root <解压目录> --require-terminal --evidence-output <另一个目录>`；阶段状态复核为`code/37_verify_stage_release.py --root <解压目录> --evidence-output <另一个目录>`。两者只读取公开源，结果写至另一个目录。公开验证通过不把不合法模型变成可采用结果。

汇编时间（UTC）：{completed_at}。
'''
    (OUT/'STAGE_SUMMARY.md').write_text(summary,encoding='utf-8')
    manifest=dict(status='STAGE_EVIDENCE_BUILT',created_at=completed_at,actual_calls=len(calls),
                  real_calls=len(real),synthetic_calls=len(calls)-len(real),
                  real_linear_calls=len(linear),real_latent_calls=len(latent),
                  real_latent_seconds=latent_seconds,all_engine_seconds=all_seconds,
                  planned_target_positions=len(disposition),latent_MI_families_reportable=0,
                  observed_route_calls=0,H4_calls=0,performance_probe_calls=0,
                  scientific_project_complete=False,queue_terminal_sha256=sha(ROOT/'runtime/queue_terminal.json'),
                  final_receipt_sha256=sha(ROOT/closure['current_attempt_directory']/'receipt.json'),
                  independent_evidence_sha256=sha(ROOT/'evidence/independent_verification.json'))
    (ROOT/'audit/stage_closeout_20261009/stage_evidence.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False))


if __name__=='__main__':
    main()
