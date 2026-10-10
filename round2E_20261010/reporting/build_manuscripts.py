"""从终态聚合结果生成v50/v42评议阶段稿；保留原稿引文字段与非修改部件。"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json
import math
import re
import zipfile
from lxml import etree as E
import document_support as d

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'reporting/context_evidence/round2D/manuscript/delivery'
NS,W=d.NS,d.W
ZN={'SD':'标准差','SEXGAP':'性别差','OLDEST':'老大差','SONGAP':'长子差'}
N={'SD':3274,'SEXGAP':2339,'OLDEST':3159,'SONGAP':2894}
PATH={'bii':'IX→IY','bis':'IX→SY','bss':'SX→SY','bsyiy':'IY→SY','gi0':'Z₀→IY','gs0':'Z₀→SY','dc':'SX×Z₀→SY'}


def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def load_nodes(path):
    with zipfile.ZipFile(path) as z:tree=E.fromstring(z.read('word/document.xml'))
    return list(tree.find('w:body',NS))[:-1]


def change_span(node,old,new):
    """从末尾替换可见文本，跨run但不触及引文域指令或其他run格式。"""
    before=d.text(node);instr=node.xpath('.//w:instrText/text()',namespaces=NS)
    starts=[m.start() for m in re.finditer(re.escape(old),before)]
    for start in reversed(starts):
        end=start+len(old);cursor=0;inserted=False
        for el in node.findall('.//w:t',NS):
            s=el.text or '';a,b=cursor,cursor+len(s);cursor=b
            if b<=start or a>=end:continue
            lo,hi=max(start-a,0),min(end-a,len(s))
            el.text=s[:lo]+(new if not inserted else '')+s[hi:];inserted=True
    assert d.text(node)==before.replace(old,new)
    assert node.xpath('.//w:instrText/text()',namespaces=NS)==instr
    return len(starts)


def plain(nodes,index,value,changes):
    assert not nodes[index].findall('.//w:instrText',NS),index
    before=d.text(nodes[index]);new=d.paragraph(value)
    prop=nodes[index].find(W+'pPr')
    if prop is not None:
        new.remove(new.find(W+'pPr'));new.insert(0,deepcopy(prop))
    nodes[index]=new;changes.append(dict(index=index,before=before,after=value,method='plain_paragraph'))


def span(nodes,index,old,new,changes):
    before=d.text(nodes[index]);assert old in before,(index,old)
    count=change_span(nodes[index],old,new)
    changes.append(dict(index=index,before=before,after=d.text(nodes[index]),method='visible_span_fields_retained',occurrences=count))


def tab(title,headers,values,appendix=False,widths=None):
    total=14400 if appendix else 9000
    return d.table(title,headers,values,'appendix' if appendix else 'main',widths=widths,total_width=total,size=19)[1]


def make_status(f):
    if f['status']=='ADOPT':return '10/10可采用'
    labels={'PILOT_NOT_USABLE':'首份交互未通过','NOT_POOLABLE':'含不合法成员，未合并',
      'NUMERIC_CHECK_FAILED':'数值核查未通过','INCOMPLETE':'成员不完整',
      'NOT_ESTIMATED_WITHIN_BUDGET':'预算内未完成'}
    return labels.get(f['status'],f['status'])


def member_states(value):
    labels={'USABLE':'可用','INADMISSIBLE_SY_ONLY':'SY负残差','INADMISSIBLE':'不合法',
      'TIMEOUT':'超时','ESTIMATION_FAILED':'估计失败','NOT_RUN':'未执行'}
    items=value.split(';');parts=[];start=0
    for end in range(1,len(items)+1):
        if end==len(items) or items[end]!=items[start]:
            span=f'{start+1:02d}' if end==start+1 else f'{start+1:02d}—{end:02d}'
            parts.append(span+' '+labels.get(items[start],items[start]));start=end
    return '；'.join(parts)


class Results:
    def __init__(self,preview=False):
        self.preview=preview
        self.selection=read(ROOT/'runtime/selection.json')
        if not preview:
            assert self.selection.get('terminal')
            assert read(ROOT/'audit/independent/independent_verification.json')['status']=='PASS'
        self.f=rows(ROOT/'results/FAMILY_STATUS.csv') if (ROOT/'results/FAMILY_STATUS.csv').exists() else [
          dict(z=z,spec=sp,status='INCOMPLETE',n_usable='0') for z in ZN for sp in ['E0','E1']]
        self.p=rows(ROOT/'results/POOLED_KEY_PATHS.csv') if (ROOT/'results/POOLED_KEY_PATHS.csv').exists() else []
        self.mult=rows(ROOT/'results/MULTIPLICITY.csv') if (ROOT/'results/MULTIPLICITY.csv').exists() else []
        self.slopes=rows(ROOT/'results/CONDITIONAL_SLOPES.csv') if (ROOT/'results/CONDITIONAL_SLOPES.csv').exists() else []
        self.support=rows(ROOT/'contracts/SUPPORT_POINTS.csv')
        self.execution=[]
        for p in sorted((ROOT/'models').glob('*/receipt.json')):self.execution.append(read(p))
    def family(self,z,sp):return next(f for f in self.f if f['z']==z and f['spec']==sp)
    def path(self,z,sp,label):return next((p for p in self.p if p.get('z')==z and p.get('spec')==sp and p.get('label')==label),None)
    def holm(self,z,sp,label):return next((p.get('holm') for p in self.mult if p['z']==z and p['spec']==sp and p['label']==label),None)
    def count(self,sp):return sum(f['spec']==sp and f['status']=='ADOPT' for f in self.f)
    def statement(self):
        if self.preview:return '观测基期路线正在执行，本预览不作为最终采用结论。'
        direct='、'.join(ZN[z] for z in ZN if self.family(z,'E0')['status']=='ADOPT') or '无分支'
        interact='、'.join(ZN[z] for z in ZN if self.family(z,'E1')['status']=='ADOPT') or '无分支'
        return f'观测2012年差异的无交互E0中，{direct}取得完整十份可采用估计；交互E1中，{interact}通过完整家族与预定数值验收。'


def core_rows(r,sp):
    out=[]
    for z in ZN:
        for label in (['gi0','gs0'] if sp=='E0' else ['dc']):
            p=r.path(z,sp,label)
            estimate=d.number(p['estimate'])+' ('+d.number(p['se'])+')' if p else '—'
            pv=d.pvalue(p['p'])+' / '+d.pvalue(r.holm(z,sp,label)) if p else '—'
            if sp=='E0':out.append([f'{ZN[z]}\nN={N[z]}',PATH[label],estimate,d.interval(p) if p else '—',pv,make_status(r.family(z,sp))])
            else:out.append([ZN[z],str(N[z]),estimate,d.interval(p) if p else '—',pv,make_status(r.family(z,sp))])
    return out


def hypothesis_rows(r):
    def e0(z):return make_status(r.family(z,'E0'))+'；只覆盖观测Z₀，不等同于潜IZ或SZ。'
    return [
      ['H1.1','总体亲近度越高，抑郁越低','SW基期负向关联相容；变化关联尚不明确。'],
      ['H1.2','家内标准差越大，抑郁越高',e0('SD')+'路径与区间见表4。'],
      ['H1.3','原始儿子−女儿差越小，抑郁越高',e0('SEXGAP')],
      ['H1.4','原始老大／长子差越小，抑郁越高','两分支分别见表4；不互相替代。'],
      ['H2.1','不利家内差异削弱亲近度的负向关联',f'{r.count("E1")}/4观测Z₀交互家族可采用；潜IZ路线未形成推断。'],
      ['H2.2','较高亲近度缓冲不利家内差异的关联','当前乘积只含SX变化；较高IX水平的缓冲未检验。同一乘积不重复计为独立结果。'],
      ['H3.1','直接关联的父母性别差异','未检验。'],['H3.2','调节关联的父母性别差异','未检验。'],
      ['H4.1a','资源较好者较少受到家内差异影响','未检验。'],['H4.1b','资源较好者较易受到家内差异影响','未检验。'],
      ['H4.2a','资源较好者：积极关系缓解与消极关系弱化两个成分更弱','原文保留，成分解释见表6；本批未检验。'],
      ['H4.2b','资源较好者：积极关系缓解与消极关系弱化两个成分更强','不等同于任意同向交互的绝对幅度更大；本批未检验。'],
      ['H5.1','基期、跨期和变化之间的直接关联','部分操作化；不判为三类关系同时成立。'],
      ['H5.2','不同时间组合的调节关联','本批只执行SX×Z₀→SY；其他组合未检验。'],
    ]


def seven_rows(r):
    return [
      ['1 趋势、时间、窗口','部分解决','错误计分下的旧下降结论撤回；当前时间单位明确。量尺、窗口和SW的Y形状敏感性未执行。'],
      ['2 CES-D计分与范围','计分及入口关闭','共同八题、反向题、完整作答与固定基期标准化已绑定；测量不变性另列。'],
      ['3 增长方差与识别','SW层面关闭；新增模型分别判断',f'E0采用{r.count("E0")}/4，E1采用{r.count("E1")}/4；负方差不因不显著而放行。'],
      ['4 拟合不足','SW可采用；新增模型有条件', 'E0拟合与E1数值/矩阵逐项检查；父模型通过不推定交互模型通过。'],
      ['5 过度表述','具体修订已应用；全文仍为阶段稿','当前与历史分开；H4成分、参考点和三篇文献对应已纠正。'],
      ['6 得分、调节与MI','部分解决',f'实际观测E0/E1已执行；E1完整家族{r.count("E1")}/4。保留现有MI相容性和Z₀测量误差限制。'],
      ['7 H4.2b','未执行','原理论方向保留；本批先交付，资源三阶检验留待另议。'],
    ]


def citation_style(nodes,changes):
    pairs=[
      ('Chen et al., 2021b, 2021a, 2024','Chen et al., 2021b; Chen & Zhou, 2021a; Chen & Chen, 2024'),
      ('Zhang et al., 2024, 2025a, 2025b','Zhang & Liu, 2024; Zhang et al., 2025a, 2025b'),
      ('Chen et al., 2021a, 2024','Chen & Zhou, 2021a; Chen & Chen, 2024'),
      ('Li et al., 2023','Li & Zhang, 2023'),('Li et al.（2023）','Li & Zhang（2023）'),
      ('Zhang et al., 2024','Zhang & Liu, 2024'),('Zhang et al.（2024）','Zhang & Liu（2024）'),
      ('Chen et al., 2024','Chen & Chen, 2024'),('Chen et al., 2021a','Chen & Zhou, 2021a')]
    for i,n in enumerate(nodes):
        if i>=131:continue
        before=d.text(n)
        for a,b in pairs:change_span(n,a,b)
        if d.text(n)!=before:changes.append(dict(index=i,before=before,after=d.text(n),method='citation_visible_text_only'))


def main_nodes(r):
    nodes=load_nodes(SOURCE/'PP_LGCM_review_v49_round2D.docx');changes=[]
    P=lambda i,s:plain(nodes,i,s,changes)
    S=lambda i,a,b:span(nodes,i,a,b,changes)
    P(0,'多子女家庭代际亲近度、家内差异与老年抑郁症状的纵向关联〔v50阶段稿：观测基期调节〕')
    P(2,'摘要：本文使用中国家庭追踪调查2012—2022年五期资料，考察多子女家庭代际亲近度、家内相对差异与老年抑郁症状轨迹的关联。共同队列含3274名基期年龄大于60岁的受访者；各差异分支限定于2012年对应指标可计算者，复用10份家庭—个人分层协变量插补。主要父工作模型SW允许每期亲近度与抑郁的测量残差相关，亲近度采用自由形状，抑郁采用十年日历线性近似。SW基期亲近度与基期抑郁的关联为−0.350（95%区间[−0.639, −0.061]）；变化关联为−0.246（[−1.442, 0.949]），方向和幅度尚不明确。本轮实际执行四种观测2012年差异Z₀的无交互与连续调节模型。'+r.statement()+'H4资源差异未在本批执行。推断条件于当前工作模型和插补假设；观测Z₀不等同于潜在初始差异IZ，不能将失败或宽区间解释为效应不存在。')
    P(18,'4. 相应条件关联是否因父母性别或社会经济资源而不同？这仍是原研究问题；本批先交付观测基期分析，资源差异另行审议，不自动接续估计。')
    S(24,'亲子关系中的亲密上限水平正向预测，疏远下限水平负向预测父母抑郁症状。此外，亲子关系之间存在互动效应，消极关系的存在会削弱积极亲子关系对抑郁的益处',
      '最亲近关系为紧密型者的父母抑郁症状较低，最疏远关系为疏离型者较高；该研究还检验了有无疏离关系与最近关系类型的交互，发现部分类型比较中的紧密关系优势被削弱')
    S(25,'该文将积极与消极关系的交互机制列为未来研究问题，','该文的“互动策略”以关系类型的标准差与极差表示异质性，并非本文SX×Z的乘积交互；其将积极与消极关系的交互机制列为未来研究问题，')
    S(49,'例如：疏离型（紧密型）亲子关系与最低（最高）认知功能水平和最快（最慢）认知功能下降相关','例如：最远关系为疏离型（紧密型）者具有最低（最高）的认知功能水平和最快（最慢）的认知功能下降')
    S(68,'本研究优先联合估计潜变量交互，避免把外部因子得分作为无误差变量。','先前潜IZ路线未取得可采用的调节估计，本轮实际采用“SW＋观测2012年连续Z₀”的工作设计；X/Y仍为联合潜增长过程，未使用外部因子得分。')
    S(76,'使用潜在增长曲线模型（LGCM）估计代际亲近度家内差异、老年抑郁状况变化轨迹','使用潜在增长曲线模型（LGCM）估计总体亲近度与老年抑郁的变化轨迹，并以基期家内差异考察条件关联')
    P(80,'纵向亲近度和CES-D不作单值补齐，其观测和缺失掩码保持原样；模型通过观测数据似然使用非平衡测量。当前调节变量Z₀仅取2012年实际有效观测，结构性无定义的子女构成差值不填零或插补。插补利用已观测后期X/Y、应答及死亡等辅助信息；这不同于将后期变量作为结构方程的基期混杂。该方案仍依赖缺失机制与模型假设，不证明死亡后结局有定义，也不宣称解决了非随机流失。')
    P(83,'观测基期连续调节与资源差异的操作化')
    P(84,'四个分支分别采用本身的基期资格样本，不取交集。E0在SW结构中增加ix、sx、iy、sy对Z₀的回归，并允许基期x1和y1条件于Z₀，保持五期X—Y同波残差协方差及家庭聚类。所有增长因子仍条件于原基期控制。仅按零方差或精确线性依赖规则移除子样本中的控制列，十份保持一致，不按P值删控制或残差。')
    P(85,'E1在E0上仅增加sxz | sx XWITH z0及sy ON sxz。抑郁变化方程为：SY＝α＋βIX·IX＋βSX·SX＋βIY·IY＋γZ·Z₀＋ηᵀC＋δ(SX×Z₀)＋u。δ是核心调节参数，βSX是Z₀＝0时的条件变化关联。该设计询问实际2012年关系配置是否改变后续变化关联，不估计IZ、SZ，也不替代较高初始亲近度IX的缓冲检验。父模型主路径不显著不禁止检验δ；不合法E0不充当合法起点或似然比较基准。')
    P(86,'E1使用XWITH与一维数值积分。采用要求包括正常结束、自由方差非负、基础潜变量与测量残差矩阵及参数协方差合法，并在实际Z₀支持端点检查条件观测协方差；不把乘积虚构为独立正态潜因子。首份候选需通过15→20点积分及另一套完整起点的一致性核查；目标路径差分别受高精度SE的5%或max(0.001, 0.01×SE)约束，SE相对差≤5%，同积分起点的LL差≤0.01。只有实际通过的检查才记通过，失败或较低似然的替代起点不自动算稳定。数值复核仅针对MI01，不外推为十份均多起点验证。')
    P(87,'原三过程D0/D1路线保留为历史未完成分析，不在本批重新启动。其无交互规格已经多次出现负方差，潜交互又出现求逆失败、鞍点或超时，因此不能仅归因于数值积分慢，也不能据此证明形式上不可识别。新增观测Z₀设计不要求Z形成高斯潜增长过程，但保留Z₀测量误差与条件线性近似的限制；不使用不合法D0计算的所谓信度作正式证据，也不预设误差一定使调节衰减。')
    P(88,'本批在实际估计前冻结规格和预算：含6次合成接口在内最多101次调用，累计引擎8小时、墙钟10小时；线性单次5分钟，观测LMS单次30分钟。先让四分支各有首份E0/E1试验，再完成合法家族；有限修复共最多4次。单一外部作业槽，实际SD E1合法后才允许同起点1核与4核配对。负方差不因不显著而放行；最多两次SD单成员sy@0诊断只说明约束敏感性，不替代自由残差MI家族。')
    if not r.preview:
        P(88,d.text(nodes[88])+'实际一次性别差修复作业跨越系统待机，恢复后终止，墙钟为2002秒、超出名义上限202秒；该作业记录的CPU时间约331秒。全部墙钟照实计入预算，未因此补跑。')
    P(89,'资源分组仍预定为小学及以下／初中及以上、乡村／城市、无／有个人收入，G取0/1。有个人收入指金额大于零，并非高收入。若另批实施H4，模型应含SX×Z₀、SX×G、Z₀×G及相应主项，以三阶δG检验两组调节之差：δ0＝δ，δ1＝δ＋δG。当前按本批先交付的范围选择，没有运行三项H4，不能从核心调节或某一组的星号代替资源差异检验。')
    P(92,'条件斜率b(z)＝βSX＋δz在每份MI使用完整参数协方差计算，包括2z·Cov(βSX,δ)，再合并同一固定对比。参考点在本轮估计前由实际支持范围冻结：SD使用原始零、正值中位数及全样本P90；有符号指标使用原始零及P10/P90，重合零点按预定规则换为对应非零一侧中位数。每个点报告±0.1标准化单位内的人数与家庭数（附表A11）。E1的δ、E0的gi0及gs0分别按固定4项Holm校正，缺项保持缺失且不缩小家族。')
    P(93,'原H4.2a/b的“缓解”和“弱化”是需分别绑定的理论成分，不能简化为任意方向交互的绝对幅度较小或较大。当相关X—Y条件斜率为负、Z₀越大越不利时，δ＞0表示负向关联随Z₀增大而减弱；δ＜0表示该负向关联增强，亦只在另一边际关系有相应方向时才可讨论SX变化的缓解成分。同一乘积不重复计为两个独立发现。组间统计差异与原理论方向必须分列，不能用δG显著或两组同向幅度变化直接宣布整个H4.2b成立。本批没有计算三阶系数或九项同时区间。')
    P(94,'所有结果条件于当前模型和复用插补。实际插补仅以2012年十个控制变量为目标，预测矩阵含基期Z特征和后期X/Y及缺失辅助信息，但没有按本研究SX×Z₀交互建立实质模型相容的联合插补。因此，本轮不将“缺少乘积”认定为唯一相容性问题，也不从Z₀已入预测矩阵推断相容性已成立。非线性分析与插补的相容性需另行评价（Bartlett等，2015）。增强插补、家庭重抽样、完整协变量、缩尾、增长形状、量尺及窗口敏感性均不在本批执行。')
    P(107,'观测基期家内差异的直接关联与调节')
    P(108,r.statement()+'各分支完整处置见表4、表5及附表A9；不合并失败成员，也不把未采用结果解释为无关联。')
    P(109,'表4 观测2012年差异的E0直接关联（条件MI）')
    nodes[110]=tab(d.text(nodes[109]),['差异 / N','路径','估计 (SE)','95%区间','P / Holm P','采用状态'],core_rows(r,'E0'),widths=[1100,1000,1400,1900,1300,2300])
    P(111,'E0中的gi0和gs0分别是观测Z₀与潜在抑郁基期、变化的条件路径；同时保留x1、y1对Z₀的基期指标层关系。表内只列完整十份可采用的家族，不把单份或不合法输出当作可报告MI估计。所有系数均是条件关联，不是Z₀的干预效应。')
    P(113,'连续调节的当前估计范围')
    P(114,'表5 观测2012年差异的E1核心交互（条件MI）')
    nodes[115]=tab(d.text(nodes[114]),['差异Z₀','基期N','δ (SE)','95%区间','P / Holm P','采用状态'],core_rows(r,'E1'),widths=[1000,800,1400,1900,1300,2600])
    P(116,'δ及条件斜率只有在该交互家族通过全部采用条件后才报告。SD原始零对应Z₀＝−0.475926，z＝−1反算为负的原始SD，故不作为实际家庭的主展示点。附表A11保留真实支持点及附近样本量；若交互家族不能采用，参考点本身不是已估计的斜率。单成员边界诊断另见附表A20。')
    P(118,'表6 H4原预测与本轮操作化的对应（未执行检验）')
    h4=[['消极关系的弱化成分','SX×不利Z₀→SY','当b(z)<0时，δ>0使该负向关联减弱','H4未执行'],
        ['积极关系的缓解成分','同一乘积的另一边际解读','δ<0仅在Z₀边际不利关联与SX含义相符时可讨论变化缓解；不等同于IX缓冲','H4未执行'],
        ['资源组间差异','δG＝δ1−δ0','直接检验差异，再判断其是否对应原预测成分','H4未执行']]
    nodes[119]=tab(d.text(nodes[118]),['原预测成分','对应参数','解释边界','状态'],h4,widths=[1450,1550,4700,1300])
    P(120,'G＝1分别是初中及以上、城市、有个人收入。原假设4.2a/b全文保留在理论部分；后续方向判定不得把“两组均为负、资源1更负”称为弱化更强，也不得将任何一个成分的方向自动升级为整个原假设获支持。具体检验及多重性规则应在后续独立批次冻结。')
    nodes[123]=tab('表7 原假设与当前证据范围',['假设','原预测','当前证据及未检验范围'],hypothesis_rows(r),widths=[750,2900,5350])
    P(126,'新增家内差异路径的采用与不确定性见表4—5；原潜IZ调节及三项资源差异的开放范围见附表A9、A12。即使无交互E0获得可报告估计，也不能替代核心调节E1或H4的推断。')
    P(129,'本研究有几项具体限制。样本要求基期年龄大于60岁、多子女亲近度回答及后续观测，死亡、代答、未追访和结构性资格变化可能影响代表性。四类家内差异在各自2012年基期资格样本中有74.4%—76.4%的有效记录在标准化前取原始零值（附表A4），亲近度本身为有界等级评分；条件线性关系与LMS分布近似仍需谨慎。零值集中不能单独确定负方差来源，也不是无调节的证据。Z₀测量误差、交互与现有插补的相容性、跨期测量不变性及形状/量尺/窗口敏感性均有未决范围；当前区间也不包含模型选择不确定性。')
    citation_style(nodes,changes)
    return nodes,changes


def historical_rows():
    return [
      ['标准差','D0','MI01及起点修复仍为SY负残差（约−0.132；SE约0.322）'],
      ['性别差','D0','MI01的SX、SY残差均为负；有限修复未解决'],
      ['老大差','D0','MI01—05可用；MI06及修复SY为负（修复约−0.000687），故不合并前五份'],
      ['长子差','D0','MI01及修复SY负残差（约−0.285；SE约0.546）'],
      ['标准差','D1','MI01在第523次迭代报告estimated covariance matrix could not be inverted；未正常结束'],
      ['性别差','D1','首试不合法；修复第711次迭代出现estimated covariance matrix could not be inverted'],
      ['老大差','D1','首次超时；纯EM修复正常结束但有鞍点、SY负残差及参数协方差问题'],
      ['长子差','D1','首次不合法；最后一次起点修复达到六小时时限'],
    ]


def appendix_nodes(r):
    nodes=load_nodes(SOURCE/'PP_LGCM_appendix_review_v41_round2D.docx');changes=[]
    P=lambda i,s:plain(nodes,i,s,changes)
    P(0,'当前分析附录（v42评议阶段稿）')
    P(1,'本附录与正文v50使用同一Round2E终态批次；既有SW和历史三过程证据均标明来源。当前观测基期模型的原始聚合输出、高精度参数、完整起点映射、执行预算及独立复核另附。逐人数据、真实PID/FID、得分和插补对象不进入公开材料。历史98张表不作为本轮新估计结果。')
    P(4,'X/Y沿用共同3274人队列的固定基期参照；Z先计算100×原始SD或差值/同波均值，再用各自基期资格样本的均值、SD标准化，三个有符号差值乘−1。本轮只使用实际2012年Z₀；表中Z增长形式仅描述历史D0/D1规格，不表示本轮又估计了Z轨迹。')
    P(25,'附表A9 本轮观测家内差异家族的执行与采用')
    fr=[[ZN[f['z']],f['spec'],f['n_usable']+'/10',make_status(f),member_states(f.get('member_statuses','执行中'))] for f in r.f]
    nodes[26]=tab(d.text(nodes[25]),['差异','规格','可用成员','家族状态','MI01—10逐份状态'],fr,True,widths=[1300,900,1200,2600,8400])
    P(27,'E0/E1分别为SW加观测2012年Z₀的无/有交互模型；USABLE只表示单成员通过，ADOPT才表示完整家族可作条件MI推断。首份15点失败时不把未执行20点写为失败精度检查。H4按本批范围延期。Round2D历史D0/D1逐分支原因另见附表A21。')
    P(28,'附表A10 新增家内差异模型（E0/E1）的可报告路径')
    pathrows=[]
    for x in r.p:
        if 'label' not in x:continue
        pathrows.append([ZN[x['z']],x['spec'],PATH.get(x['label'],x['label']),d.number(x['estimate']),d.number(x['se']),d.interval(x),d.pvalue(x['p']),d.number(x.get('FMI'),5),d.number(x.get('MCSE_over_SE'),5)])
    if pathrows:
        nodes[29]=tab(d.text(nodes[28]),['差异','规格','路径','估计','SE','95%区间','P','FMI','MCSE/SE'],pathrows,True,widths=[1400,900,1900,1300,1300,3000,1000,1800,1800])
    else:P(29,'当前新增模型没有完整可采用家族；不列伪造合并系数。既有SW仍按附表A6/A7报告。')
    P(30,'参数名：bii＝IX→IY；bis＝IX→SY；bss＝SX→SY；bsyiy＝IY→SY；gi0＝观测Z₀→IY；gs0＝观测Z₀→SY；dc＝SX×Z₀→SY。I/S分别表示初始和变化因子。多重性限定为dc、gi0、gs0各固定四分支；未执行/不可用检验保持缺失。MCSE/SE只反映有限MI模拟误差，不表示总区间精确。')
    P(31,'附表A11 事前冻结的实际支持点与条件斜率范围')
    sr=[]
    labels={'raw_zero':'原始零','positive_median':'正值中位数','p90':'P90','p10':'P10','negative_median':'负值中位数'}
    for x in r.support:
        slope=next((s for s in r.slopes if s.get('z')==x['z'] and s.get('point')==x['point']),None)
        sr.append([ZN[x['z']],labels.get(x['point'],x['point']),d.number(x['value'],6),d.number(x['original_relative_value'],4),x['n_near'],x['households_near'],d.number(slope['estimate'])+' '+d.interval(slope) if slope else '无可采用交互家族'])
    nodes[32]=tab(d.text(nodes[31]),['差异','参考点','标准化Z₀','原比值尺度','附近人数','附近家庭','b(z)及95%区间'],sr,True,widths=[1200,1900,1700,1700,1500,1600,4800])
    P(33,'参考点在首次CFPS估计前冻结；附近指±0.1标准化单位。有符号差值方向已反向，零为原始差值零，不是标准化Z₀＝0。P10/P90与原始零重合时按合同使用对应非零一侧中位数。SD的−1不对应实际允许的原始SD。仅完整E1家族才计算斜率及其差，方差包括完整系数协方差。')
    P(34,'附表A12 H4待检验的成分与范围')
    nodes[35]=tab(d.text(nodes[34]),['量','定义','统计问题','当前状态'],[
      ['δ0','δ','资源0组的SX×Z₀调节','未执行'],['δ1','δ＋δG','资源1组的SX×Z₀调节','未执行'],
      ['δG','δ1−δ0','资源组间调节差异；不能比较两组星号代替','未执行'],
      ['弱化／缓解成分','方向还须结合b(z)、Z₀边际关系和SX含义','分别绑定原理论；不能任意方向幅度更大就支持整个H4.2b','原文保留，后续批次']
    ],True,widths=[1800,2300,7400,2900])
    P(36,'三项资源变量的1编码已核对为初中及以上、城市、有个人收入（金额>0，非高收入）。H4本批不自动接续，不以核心δ显著与否决定其理论资格。没有三阶估计或九项同时区间，亦没有实际H4方向判定。')
    P(38,'完整协变量诊断不在本批批准范围，未启动；原预定样本2830人、2105个家庭仅为后续设计信息。本批也未作缩尾、潜IZ小试、量尺、窗口或Y形状扩展。')
    nodes[41]=tab(d.text(nodes[40]),['原问题','当前状态','已经达到和仍未完成的范围'],seven_rows(r),True,widths=[2400,3300,8700])
    # 新增附表保留A1—A18原编号，避免旧引用失效。
    more=[]
    more.extend(d.table('附表A19 本轮逐次调用与负方差诊断',['调用','状态','引擎秒','SY残差','负方差','积分点/核数'],[
      [x['id'].removeprefix('CFPS_').replace('_',' '),member_states(x['status']).removeprefix('01 '),d.number(x.get('seconds'),2),d.number(x.get('sy'),6),';'.join(x.get('negative',[])) if isinstance(x.get('negative'),list) else x.get('negative','') or '—',f'{x["points"]}/{x["processors"]}' if x['spec'] in ['E1','E1B'] else f'—/{x["processors"]}']
      for x in r.execution if x['sample']=='CFPS'],'appendix',total_width=14400,widths=[4800,3400,1400,1600,1800,1400],size=18))
    more.append(d.paragraph('E0/E0B不需数值积分，积分点列以“—”表示。表内单份失败参数只用于诊断，不是可合并的研究效应。完整调用ID、OUT、独立引擎回执和参数协方差公开；求逆失败不改写为已证明最终Hessian奇异。性别差修复2002.49秒包含系统待机：04:02:09进入、04:28:58恢复，监督器随后终止；记录CPU约331.09秒。超出1800秒的202.49秒照实计入预算，不裁剪为1800秒，不据此声称全程都在计算。'))
    more.append(d.paragraph('附表A20 SD单成员固定SY＝0诊断',style='af3',keep=True))
    br=[x for x in r.execution if x['sample']=='CFPS' and x['spec'] in ['E0B','E1B']]
    if br:
        brow=[]
        for x in br:
            k=rows(ROOT/'models'/x['id']/'key_paths.csv') if (ROOT/'models'/x['id']/'key_paths.csv').exists() else []
            dc=next((t for t in k if t['label']=='dc'),None)
            brow.append([x['spec'],'MI'+str(x['member']).zfill(2),x['status'],d.number(x.get('seconds'),2),d.number(dc['estimate'])+' ('+d.number(dc['se'])+')' if dc else '—','仅约束诊断，无MI推断'])
        more.append(tab('附表A20 SD单成员固定SY＝0诊断',['规格','成员','状态','引擎秒','单份δ (SE)','适用范围'],brow,True,widths=[1200,1100,3300,1500,2700,4600]))
    else:more.append(d.paragraph('未触发或预算内未执行；不能当作边界规格失败。'))
    more.append(d.paragraph('本表仅列CFPS的两次边界诊断，合成接口检查另见调用台账。该诊断保留SW同波残差，只固定SY的条件残差为0。它改变模型假设，不代替全部十份自由残差家族；单份系数、显著性和合法性不构成核心调节正式结果，也不证明真实方差等于0。'))
    more.extend(d.table('附表A21 历史Round2D三过程失败的具体位置',['差异','规格','实际证据'],historical_rows(),'appendix',total_width=14400,widths=[1700,1100,11600],size=19))
    more.append(d.paragraph('该表来自Round2D保存输出及其原独立复核，不计入本轮新调用。负残差不显著不能证明人口方差0；微小负值不是打印舍入而自动放行，亦不等于已证明调节不存在。原始estimated covariance求逆错误不统一改写为最终Hessian奇异。'))
    nodes.extend(more)
    return nodes,changes


def save_doc(src,dst,nodes,changes):
    with zipfile.ZipFile(src) as z:parts={n:z.read(n) for n in z.namelist()}
    original=E.fromstring(parts['word/document.xml']);old_instr=original.xpath('.//w:instrText/text()',namespaces=NS)
    body=original.find('w:body',NS);section=deepcopy(body.find(W+'sectPr'))
    for x in list(body):body.remove(x)
    body.extend(nodes);body.append(section)
    assert old_instr==original.xpath('.//w:instrText/text()',namespaces=NS),'Citation instruction fields changed'
    parts['word/document.xml']=E.tostring(original,xml_declaration=True,encoding='UTF-8',standalone=True)
    if 'docProps/core.xml' in parts:
        core=E.fromstring(parts['docProps/core.xml']);el=core.find('{http://purl.org/dc/terms/}modified')
        if el is not None:el.text=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        parts['docProps/core.xml']=E.tostring(core,xml_declaration=True,encoding='UTF-8',standalone=True)
    with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in parts.items():z.writestr(n,b)
    with zipfile.ZipFile(dst) as z:assert z.testzip() is None
    return dict(source=src.name,source_sha256=sha(src),document=dst.name,docx_sha256=sha(dst),
      citation_instruction_fragments=len(old_instr),all_citation_instructions_preserved=True,
      changed_parts=['word/document.xml','docProps/core.xml'],changes=changes,Zotero_native_refresh='NOT_PERFORMED')


def readable_and_tables(nodes,document):
    lines=[];tables=[];previous=''
    for n in nodes:
        if n.tag==W+'tbl':
            rr=[[''.join(c.xpath('.//w:t/text()',namespaces=NS)) for c in row.findall('w:tc',NS)] for row in n.findall('w:tr',NS)]
            tables.append(dict(document=document,title=previous,headers=rr[0],rows=rr[1:]))
            esc=lambda s:s.replace('|','\\|').replace('\n','<br>')
            lines+=['','| '+' | '.join(map(esc,rr[0]))+' |','| '+' | '.join(['---']*len(rr[0]))+' |']
            lines+=['| '+' | '.join(map(esc,row))+' |' for row in rr[1:]];lines.append('')
        else:
            t=d.text(n)
            if t:lines += [t,''];previous=t
            elif n.findall('.//w:drawing',NS):lines+=['〔保留原有样本流程图；见同版PDF〕','']
    return '\n'.join(lines),tables


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preview',action='store_true');a=ap.parse_args()
    r=Results(a.preview);out=ROOT/'manuscript'/('preview_in_progress' if a.preview else 'delivery');out.mkdir(parents=True,exist_ok=True)
    rec=[];tabs=[]
    for kind,source,target,build in [
      ('main','PP_LGCM_review_v49_round2D.docx','PP_LGCM_review_v50_round2E.docx',main_nodes),
      ('appendix','PP_LGCM_appendix_review_v41_round2D.docx','PP_LGCM_appendix_review_v42_round2E.docx',appendix_nodes)]:
        nodes,changes=build(r);rec.append(save_doc(SOURCE/source,out/target,nodes,changes))
        md,tt=readable_and_tables(nodes,kind);(out/(kind+'_readable.md')).write_text(md,encoding='utf-8');tabs+=tt
    dump(out/'revision_receipts.json',rec);dump(out/'expected_tables.json',tabs)
    dump(out/'build_status.json',dict(preview=a.preview,release_type='PARTIAL_RESEARCH_STAGE_FOR_EXTERNAL_REVIEW',
      scientific_project_complete=False,documents=2,tables=len(tabs),source_results_sha256=sha(ROOT/'results/FAMILY_STATUS.csv') if (ROOT/'results/FAMILY_STATUS.csv').exists() else None,
      NLM_three_pass='NOT_PERFORMED_THIS_STAGE; not a final manuscript scientific release',
      result_statement=r.statement(),created_utc=datetime.now(timezone.utc).isoformat()))
    with (out/'hypothesis_status.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['hypothesis','original_prediction','current_status']);w.writerows(hypothesis_rows(r))
    print('MANUSCRIPTS_BUILT',str(out),'tables',len(tabs),'preview',a.preview,flush=True)


if __name__=='__main__':main()
