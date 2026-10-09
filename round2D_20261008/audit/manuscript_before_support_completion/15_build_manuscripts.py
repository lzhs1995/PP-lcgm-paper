"""从已保存结果构建正文v49、附录v41；预览与正式交付使用不同目录。

正式模式必须已有队列终态、条件合并和独立核验PASS。不运行统计模型。
"""
from pathlib import Path
from copy import deepcopy
from lxml import etree as E
import argparse
import csv
import importlib.util
import json
import math
import re
import zipfile

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
OLD = ROOT.parent/"round2C_20261007"
loader = importlib.util.spec_from_file_location("document_support", ROOT/"code/14_manuscript_support.py")
d = importlib.util.module_from_spec(loader)
loader.loader.exec_module(d)
p, fmt, pv, ci = d.paragraph, d.number, d.pvalue, d.interval
NS, W = d.NS, d.W
ZN = {"SD":"标准差","SEXGAP":"性别差","OLDEST":"老大差","SONGAP":"长子差"}
GN = {"EDU":"教育","URBAN":"城乡","INC":"有无个人收入"}
PATH = {"bii":"亲近度基期→抑郁基期","bis":"亲近度基期→抑郁变化",
        "bss":"亲近度变化→抑郁变化","bsyiy":"抑郁基期→抑郁变化",
        "gii":"差异基期→抑郁基期","gis":"差异基期→抑郁变化","gss":"差异变化→抑郁变化",
        "gi0":"观测基期差异→抑郁基期","gs0":"观测基期差异→抑郁变化",
        "gizg":"Z₀×G→抑郁基期","gszg":"Z₀×G→抑郁变化","bxg":"SX×G→SY",
        "dc":"SX×IZ（或Z₀）→SY","dcg":"SX×Z₀×G→SY"}
JUDGMENT = {"MORE_SENSITIVE_IN_RESOURCE_ONE":"资源1组的同向调节幅度较大",
    "LESS_SENSITIVE_IN_RESOURCE_ONE":"资源1组的同向调节幅度较小",
    "MAGNITUDE_DIRECTION_UNDETERMINED":"方向或幅度差异尚不能确定",
    "NOT_ESTIMABLE":"未取得可合并对比"}

def boolean(value):
    return value is True or str(value).upper() == "TRUE"

def state_label(status):
    if status == "CONDITIONAL_MI_REPORTABLE":
        return "可报告条件MI估计"
    if status == "NOT_POOLABLE":
        return "未通过模型或数值核查，未合并"
    if status == "NOT_RUN_NOT_TRIGGERED":
        return "潜交互通过，备用未触发"
    if "BUDGET" in status or "RESOURCE_LIMIT" in status:
        why = "执行预算到限" if "BUDGET" in status else "资源等待到限"
        return ("已部分执行，未合并；" if status.startswith("INCOMPLETE_") else "未执行；")+why
    if status == "IN_PROGRESS":
        return "分析进行中，尚无采用结论"
    return status

def get_state(preview=False):
    state, pooled, slopes, contrasts, decisions = {}, [], [], [], []
    if (ROOT/"results/family_status.csv").exists():
        state = {(r["z"],r["spec"]):r for r in d.readcsv(ROOT/"results/family_status.csv")}
        pooled = d.readcsv(ROOT/"results/pooled_paths.csv")
        slopes = d.readcsv(ROOT/"results/conditional_slopes.csv")
        contrasts = d.readcsv(ROOT/"results/H4_contrasts.csv")
        decisions = d.readcsv(ROOT/"results/H4_direction_decisions.csv")
    else:
        assert preview
        for z in ZN:
            for spec in ("D0","D1","E0","E1"):
                state[(z,spec)] = dict(z=z,spec=spec,eligible=False,status="IN_PROGRESS")
        for g in GN:
            state[("SD","H4_"+g)] = dict(z="SD",spec="H4_"+g,eligible=False,status="IN_PROGRESS")
        for file in (ROOT/"results").glob("*_family.json"):
            f = d.readjson(file)
            state[(f["z"],f["spec"])] = dict(z=f["z"],spec=f["spec"],eligible=f["eligible"],
                status="CONDITIONAL_MI_REPORTABLE" if f["eligible"] else "NOT_POOLABLE",reason=f.get("reason",""))
        decisions = [dict(resource=g,judgment="NOT_ESTIMABLE") for g in GN]
    return state, pooled, slopes, contrasts, decisions

def make_flow():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    from matplotlib.font_manager import FontProperties
    font = FontProperties(fname="C:/Windows/Fonts/msyh.ttc",size=9)
    out = ROOT/"figures"
    out.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.2,6.0))
    ax.set(xlim=(0,1),ylim=(0,1))
    ax.axis("off")
    def box(x,y,w,h,label,fill="#F2F5F8"):
        ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle="round,pad=0.008,rounding_size=0.006",
            facecolor=fill,edgecolor="#334B61",linewidth=.8))
        ax.text(x,y,label,ha="center",va="center",fontproperties=font,color="#172633",linespacing=1.4)
    def arrow(x1,y1,x2,y2):
        ax.annotate("",xy=(x2,y2),xytext=(x1,y1),
            arrowprops=dict(arrowstyle="->",lw=.9,color="#61778A",shrinkA=2,shrinkB=2))
    box(.5,.94,.64,.075,"2012年年龄严格大于60岁：6,600人")
    box(.5,.82,.64,.075,"至少记录两个有效子女编号：5,460人")
    box(.5,.70,.64,.075,"至少有两份子女亲近度回答：5,296人")
    arrow(.5,.899,.5,.863);arrow(.5,.779,.5,.743)
    box(.255,.515,.45,.15,"亲近度样本\n有后续观测：3,868人\n按原子女计数筛选后：3,351人")
    box(.745,.515,.45,.15,"CES-D 8样本\n基期完整且至少一次后续观测\n3,832人")
    arrow(.5,.659,.255,.60);arrow(.5,.659,.745,.60)
    box(.5,.335,.64,.09,"两样本交集：3,274人／2,410个家庭",fill="#DBE8F2")
    arrow(.255,.43,.5,.385);arrow(.745,.43,.5,.385)
    labs = ["标准差\n3,274人","性别差\n2,339人","老大差\n3,159人","长子差\n2,894人"]
    for x,label in zip((.125,.375,.625,.875),labs):
        arrow(.5,.285,x,.195)
        box(x,.14,.225,.09,label)
    ax.text(.5,.04,"各分支均要求2012年对应差异实际可计算；不取四分支交集",
        ha="center",va="center",fontproperties=FontProperties(fname="C:/Windows/Fonts/msyh.ttc",size=8))
    fig.subplots_adjust(left=.015,right=.985,top=.995,bottom=.01)
    for suffix in ("png","pdf","svg"):
        fig.savefig(out/f"figure1_sample_flow.{suffix}",dpi=220,facecolor="white")
    plt.close(fig)
    return out/"figure1_sample_flow.png"

def drawing(rid, width_inches=6.15, height_inches=5.95):
    xml = f'''<w:p xmlns:w="{NS['w']}" xmlns:r="{NS['r']}"
      xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
      xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
      xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
      <w:pPr><w:jc w:val="center"/><w:keepNext/></w:pPr><w:r><w:drawing>
      <wp:inline distT="0" distB="0" distL="0" distR="0">
      <wp:extent cx="{int(width_inches*914400)}" cy="{int(height_inches*914400)}"/>
      <wp:docPr id="9201" name="Figure 1 current baseline sample flow"
        descr="样本筛选流程与四类基期差异可计算样本"/>
      <a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
      <pic:pic><pic:nvPicPr><pic:cNvPr id="9202" name="figure1_sample_flow.png"/><pic:cNvPicPr/></pic:nvPicPr>
      <pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
      <pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{int(width_inches*914400)}" cy="{int(height_inches*914400)}"/></a:xfrm>
      <a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>
      </a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'''
    return E.fromstring(xml.encode())

def hypothesis_rows(state, decisions):
    latent_ok = sum(boolean(state[(z,"D1")]["eligible"]) for z in ZN)
    direct_ok = sum(boolean(state[(z,"D0")]["eligible"]) for z in ZN)
    rows = [
        ["H1.1","总体亲近度与抑郁的负向关联","基期关联与预测一致；基期—变化及变化—变化关联尚不明确"],
        ["H1.2","家内标准差与抑郁的正向关联","仅能结合对应三过程可接受模型判断；不以历史结果作结论"],
        ["H1.3","儿子—女儿相对评价差与抑郁","仅能结合性别差分支的可接受估计判断；不同于绝对关系质量"],
        ["H1.4","老大／长子相对评价差与抑郁","两种操作化分别报告；不互相替代"],
        ["H2.1","家内差异削弱亲近度的负向关联",f"已安排四项SX×IZ检验；{latent_ok}/4形成条件MI估计，具体方向见表4"],
        ["H2.2","亲近度缓冲家内差异的关联","仅考察SX变化与IZ基期差异的动态操作化；较高IX水平的缓冲未检验。同一交互不重复计为独立发现"],
        ["H3.1","直接关联的父母性别差异","本轮未检验"],
        ["H3.2","调节关联的父母性别差异","本轮未检验"],
        ["H4.1a","资源较好者的直接关联较弱","本轮未检验"],
        ["H4.1b","资源较好者的直接关联较强","本轮未检验"],
        ["H4.2a","资源较好者的同向调节幅度较小","仅检验基期观测SD的三项资源对比；见表6及附表A12"],
        ["H4.2b","资源较好者的同向调节幅度较大","仅检验基期观测SD的三项资源对比；见表6及附表A12"],
        ["H5.1","基期、跨期与变化之间的直接关联","部分检验；目前仅基期负向关联明确，不能判为三类关系同时成立"],
        ["H5.2","不同时间组合的调节关联","部分操作化；只考察SX×IZ→SY，其余组合未检验"],
    ]
    for i,z in ((1,"SD"),(2,"SEXGAP")):
        rows[i][2] = "三过程无交互模型："+state_label(state[(z,"D0")]["status"])+"。交互模型的主路径是给定另一变量参考值时的关联。"
    rows[3][2] = "老大差："+state_label(state[("OLDEST","D0")]["status"])+"；长子差："+state_label(state[("SONGAP","D0")]["status"])
    return rows

def main():
    args = argparse.ArgumentParser()
    args.add_argument("--preview",action="store_true")
    opts = args.parse_args()
    if not opts.preview:
        assert d.readjson(ROOT/"runtime/queue_terminal.json")["status"] == "QUEUE_TERMINAL"
        assert d.readjson(ROOT/"results/SUMMARY.json")["status"] == "SUMMARIZED"
        assert d.readjson(ROOT/"evidence/independent_verification.json")["status"] == "PASS"
    out = ROOT/"manuscript"/("preview_in_progress" if opts.preview else "delivery")
    out.mkdir(exist_ok=True,parents=True)
    source_info = d.readjson(ROOT/"manuscript/source_template/source.json")
    source = Path(source_info["path"])
    assert d.sha(source) == source_info["sha256"]
    original = list(E.fromstring((ROOT/"manuscript/source_template/document.xml").read_bytes()).find("w:body",NS))
    nodes = [deepcopy(n) for n in original[:75]]
    state, pooled, slopes, h4, decisions = get_state(opts.preview)
    old_paths = d.readcsv(ROOT/"provenance_SW/conditional_MI_paths.csv")
    sw = {r["label"]:r for r in old_paths if r["spec"]=="SW"}
    changes = []
    def replace(i,value):
        d.replace_plain(nodes,i,value,changes)
    def tab(title, headers, rows, widths=None):
        return d.table(title,headers,rows,"main",widths=widths)
    latent_n = sum(boolean(state[(z,"D1")]["eligible"]) for z in ZN)
    observed_n = sum(boolean(state[(z,"E1")]["eligible"]) for z in ZN)
    h4_n = sum(boolean(state[("SD","H4_"+g)]["eligible"]) for g in GN)
    current = ("核心调节分析正在进行，以下排版预览不作最终采用判断。" if opts.preview else
        f"四项潜调节中{latent_n}项形成满足数值核查条件的十份插补合并估计；另有{observed_n}项观测基期差异调节和{h4_n}项资源组间差异形成相应条件估计。各项方向、区间与未完成原因分别报告。")
    replace(0,"多子女家庭代际亲近度、家内差异与老年抑郁症状的纵向关联"+("〔排版预览：分析尚在进行〕" if opts.preview else ""))
    replace(2,"摘要：本文使用中国家庭追踪调查2012—2022年五期资料，考察多子女家庭代际亲近度、家内相对差异与老年抑郁症状轨迹的关联。共同分析队列含3274名基期年龄大于60岁的受访者；四类差异的调节分析分别限定于基期相应指标可计算者。协变量缺失采用10份家庭—个人分层多重插补。主要平行过程工作模型允许每期亲近度与抑郁的测量残差相关，亲近度采用自由形状，抑郁采用十年线性变化近似。基期亲近度较高者的基期抑郁较低（估计"+fmt(sw["bii"]["estimate"])+"，95%区间"+ci(sw["bii"])+"）；变化之间的关联为"+fmt(sw["bss"]["estimate"])+"（"+ci(sw["bss"])+"），现有估计尚不明确。"+current+"本文报告固定模型与现有插补假设下的关联，不将未能估计或区间包含零解释为效应不存在，也不将其解释为干预效果。")
    replace(3,"关键词：代际亲近度；家庭内部差异；抑郁症状；平行过程潜增长模型；中国家庭追踪调查")
    replace(8,"引言")
    replace(12,"低生育率并不意味着家内关系差异失去研究意义。当前老年人的子女结构形成于更早的生育时期，多子女家庭仍是理解其亲情联系和养老经验的重要场景。不同出生队列、地区和社会群体的家庭结构也存在差别。本文据此考察多子女家庭中的关系差异，不用当前预期寿命推算某种家庭结构必然延续多少年。")
    replace(14,"本文利用CFPS五期追踪资料，将总体亲近度、家内相对差异与抑郁的基期水平和后续变化区分开来，围绕以下研究问题开展分析：")
    replace(16,"2. 不同亲近度家内差异的基期水平及变化与老年人抑郁轨迹有何关联？")
    replace(17,"3. 家内差异的基期状态是否改变总体亲近度变化与抑郁变化之间的关联？")
    replace(18,"4. 相应条件关联是否因父母性别或社会经济资源而不同？本文优先检验预先限定的三项资源差异，未执行的部分单独列明。")
    replace(19,"理论框架与研究假设")
    replace(26,"本文聚焦代际亲近度维度，以加法关联与交互关联分别考察家内差异、整体亲近度和抑郁轨迹的关系。")
    replace(35,"假设2.1：较大的家内标准差，以及相对偏向女儿或其他子女的较小有符号差值，将削弱总体亲近度与较低抑郁之间的负向关联。")
    replace(36,"假设2.2：较高的总体亲近度将缓冲上述家内差异与较高抑郁之间的关联。这里的差异指标是相对评价，不能直接等同于父母与特定子女的绝对疏远。")
    replace(39,"假设3.1：代际亲近度与抑郁之间的基期关联及变化关联，在老年女性中更强。")
    replace(40,"假设3.2：相应调节关联在老年女性中更强。")
    for i in (43,44,45,46):
        replace(i,d.text(nodes[i]).replace("有无个人收入","个人收入"))
    replace(51,"假设5.1：亲近度与抑郁之间同时存在基期关联、基期状态与后续变化的关联，以及变化之间的共变。")
    replace(52,"假设5.2：亲近度家内差异的调节关联同时涉及基期状态、基期状态与后续变化，以及变化之间的不同组合。")
    for i,value in {54:"研究设计",55:"数据与样本",63:"变量测量",64:"抑郁症状",66:"代际亲近度与家内差异",71:"基期控制变量"}.items():
        replace(i,value)
    replace(60,"两组样本取交集后得到3274人的非平衡面板，共2410个家庭。该样本按后续观测和跨期子女计数条件筛选，不能直接代表全部基线老年人。调节分析进一步要求2012年相应家内差异实际可计算：标准差3274人、性别差2339人、老大差3159人、长子差2894人，各自分析而不取交集；无相应子女构成的差值不填零。原队列中328人有死亡报告（326人年份已知、2人年份未知），其余2946人没有死亡报告，不等于均已核实存活至2022年。五波同时具有亲近度均值和CESD观测者为476人。")
    flow = make_flow()
    nodes[61] = drawing("rIdRound2DFlow")
    replace(62,"图1 样本筛选与四类家内差异的基期资格。子女计数一致不保证跨期对应完全相同的子女集合；所有分支均保留后期不平衡观测。")
    replace(65,"因变量为CES-D共同8题抑郁症状得分。2012年从20题中选取共同八题，2016年使用长短版中的共同八题，2018—2022年使用八题版本。内容为情绪低落、做事费劲、睡眠不好、感到愉快、孤独、生活快乐、悲伤难过、觉得生活无法继续。每题询问过去一周的出现频率：1＝几乎没有（不到一天），2＝有些时候（1—2天），3＝经常有（3—4天），4＝大多数时候有（5—7天）。“感到愉快”和“生活快乐”以5减原回答反向计分；特殊缺失码不参与求和，仅在八题均有有效回答时计分，总分8—32，分数越高症状越重。各期有效人数与修正计分信度见附表A2。所有时期以2012年均值13.5754428833和标准差4.2592386459作同一标准化变换。早期处理中的2012年计分错误已修正，2593人的总分随之改变；这项修正不等于跨期测量不变性已经成立。")
    replace(69,"表1 代际亲近度及家内差异的定义")
    formula_rows = [
        ["总体均值","每位老年人与各有效子女的亲近度平均分","Mean"],
        ["标准差","各有效子女评分的标准差","100 × SD / Mean"],
        ["性别差","儿子均值−女儿均值；两类均需有有效评分","100 × (儿子均值−女儿均值) / Mean"],
        ["老大差","最年长子女评分−其余子女均值","100 × (老大评分−其余均值) / Mean"],
        ["长子差","最年长儿子评分−其余子女均值","100 × (长子评分−其余均值) / Mean"],
    ]
    generated = tab("表1 代际亲近度及家内差异的定义",["指标","定义","模型前的比值尺度"],formula_rows,[1400,3700,3900])
    nodes[70] = generated[1]
    replace(72,"主调整集包含24项基期编码列，完整定义、参照组、单位与缺失数见附表A3。父母特征包括年龄（61—75岁与76岁及以上）、性别、户口、民族、教育（小学及以下／初中及以上）、自评相对收入（1—5级）、个人收入金额（万元）、健康、婚姻与ADL。健康以一般为参照；个人收入金额与自评相对收入是不同指标。")
    replace(73,"子女特征包括人数、性别构成、年龄极差、是否同住以及经济和工具性支持。家庭特征包括家庭收入（万元）、城乡与地区。子女性别构成以儿女双全为参照，经济和工具性支持分别区分无帮助、所有子女帮助、部分子女帮助。生活满意度和追访总次数不在主调整集内。资源差异中的个人收入预先操作化为2012年金额是否大于零，衡量有无个人收入而非高低收入；这限定了原资源理论的可检验含义。")
    # 段内定点改写保留所有引文域，记录真实修改。
    edits = {
        10:[("代际关系并非铁板一块！","家庭内部代际关系可能存在差异。")],
        13:[("代际关系并非一成不变！","代际关系也会随时间变化。")],
        22:[("代际经济支持呈","代际工具性支持呈")],
        28:[("亲近度标准差视为消极关系","亲近度标准差作为差异程度的指标")],
        49:[("家内差异仅有的纵向研究证实","已有少数家内差异纵向研究提示"),
            ("存在明确的时间效应","可能具有时间差异"),
            ("成功推断了老年心理健康的长期发展轨迹","估计了不同年龄段的健康轨迹"),
            ("捕捉的是年龄而非真实个体内部时间的变异","同时利用个体内追踪和不同年龄队列的信息"),
            ("是基于无队列差异的强假设将年龄效应等同于时间效应","其跨队列拼接解释依赖可比性等假设"),
            ("要知道代际关系并非一成不变！","代际关系本身也会变化。")],
        67:[("测量公式见表3.2","定义见表1")],
        68:[("当前尺度与参数单位见附表A1—A3","当前尺度与参数单位见附表A1"),
            ("对于使用连续外部因子得分的调节模型，还需区分Mplus DEFINE中对指定得分执行的再次标准化；这与纵向指标的基期标准化不是同一步变换。简单斜率的取值及绘图范围必须与模型中调节变量的实际尺度一致，并逐份插补数据核对有效样本及标准化后的得分。",
             "本研究优先联合估计潜变量交互，避免把外部因子得分作为无误差变量。三个有符号差值在基期标准化后反向，使较大的值对应原理论预定的不利方向；SD保持正向。参考值及其实际支持范围随结果表说明。")],
    }
    for i,pairs in edits.items():
        for before,after in pairs:
            if d.replace_text_span(nodes[i],before,after):
                changes.append(dict(source_body_index=i,before=before,after=after,method="visible_text_only_fields_preserved"))
    before = "同时利用个体内追踪和不同年龄队列的信息"
    if d.replace_text_span(nodes[49],before,before+"（Raudenbush与Chan，1992）"):
        changes.append(dict(source_body_index=49,before=before,after=before+"（Raudenbush与Chan，1992）",method="visible_text_only_fields_preserved"))
    # 移除历史整段加粗，保留段落标题的样式。
    for i in range(9,75):
        if i in (19,20,27,37,47,54,55,63,64,66,69,71):
            continue
        for prop in nodes[i].findall(".//w:rPr",NS):
            for tag in ("b","bCs"):
                for el in prop.findall(W+tag):
                    prop.remove(el)
    # 这些旧方法长脚注已由当前测量与方法段替代；保留脚注1的来源和7的讲义链接。
    for node in nodes:
        for ref in list(node.findall(".//w:footnoteReference",NS)):
            if ref.get(W+"id") in {"3","5","6"}:
                old_id = ref.get(W+"id")
                run = ref.getparent()
                run.remove(ref)
                if not run.findall(W+"t") and run.getparent() is not None:
                    run.getparent().remove(run)
                changes.append(dict(method="remove_redundant_historical_method_footnote",footnote_id=old_id,
                    reason="Current methods state the scale and inference limitations; source citation retained in body bibliography"))
    strategy = deepcopy(original[76])
    d.replace_text_span(strategy,"本批按以下限定规格进行","本文的分析步骤如下")
    nodes.extend([p("分析策略","afff0"),strategy])
    nodes.extend(methods_paragraphs())
    nodes.extend(results_nodes(state,pooled,slopes,h4,decisions,sw,current,tab,opts.preview))
    refs,metadata = d.bibliography(nodes,extra_references())
    nodes.extend([p("参考文献","affe")]+[p(x) for x in refs])
    records = [d.save_document(source,out/"PP_LGCM_review_v49_round2D.docx",nodes,changes,
        new_images=[("rIdRound2DFlow","figure1_sample_flow.png",flow.read_bytes())])]
    appendix = appendix_nodes(state,pooled,slopes,h4)
    records.append(d.save_document(OLD/"manuscript/PP_LGCM_appendix_review_v40_round2C_NOT_RELEASED.docx",
        out/"PP_LGCM_appendix_review_v41_round2D.docx",appendix,
        ["Rebuilt current appendix with named tables, current results, scale, source and uncertainty definitions"],appendix=True))
    (out/"revision_receipts.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"expected_tables.json").write_text(json.dumps(d.TABLE_EVIDENCE,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"retained_citations.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
    with (out/"hypothesis_status.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["hypothesis","prediction","current_scope_and_status"])
        writer.writerows(hypothesis_rows(state,decisions))
    (out/"build_status.json").write_text(json.dumps(dict(preview=opts.preview,status="DOCX_BUILT_NATIVE_PDF_PENDING",
        source_sha256=d.sha(source),template_sha256=d.sha(ROOT/"manuscript/source_template/document.xml"),
        contract_sha256=d.sha(ROOT/"RUN_CONTRACT.json"),table_count=len(d.TABLE_EVIDENCE),
        papers_in_retained_fields=len(metadata["items"])),ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(dict(output=str(out),documents=2,tables=len(d.TABLE_EVIDENCE),preview=opts.preview),ensure_ascii=False))

# 方法、结果和附录的内容生成函数在文件后部定义；数值一律从结果CSV读取。

def methods_paragraphs():
    values = [
        ("缺失处理与估计", "afff0"),
        ("2012年控制变量以核实的基期记录为准，恢复曾被其他年份代填的缺失后，完成10份、每份30轮的家庭—个人分层链式插补。家庭收入、城乡和地区在2012年家庭单位内抽取一次共同值；家庭内其他成员已报告一致真实值时，先恢复这一已知共同值。个人层目标使用带家庭随机截距的预测均值匹配，供体数为5。使用mice 3.19.0与miceadds 3.20.10；链式插补的基本框架参见van Buuren与Groothuis-Oudshoorn（2011）。观测保持、家庭共同值、目标完成和派生关系均已逐份核对。现有十份插补在本轮直接复用。", None),
        ("纵向亲近度、家内差异和CES-D不作单值补齐，其观测和缺失掩码保持原样；模型通过观测数据似然使用非平衡测量。结构性无定义的子女构成差值不当作普通可插补目标。插补模型利用已观测的后期X/Y、应答及死亡等辅助信息，这与在结构模型中将后期变量当成基期混杂不同。该方案仍依赖缺失机制与工作模型假设，不能从一致性检查推断死亡后的结局有定义，也不能宣称已解决非随机流失。", None),
        ("采用Mplus 9的稳健最大似然估计，按2012年家庭聚类计算稳健不确定性。亲近度X使用两端载荷为0和1、中间三点自由的增长基底；抑郁Y采用2012、2016、2018、2020、2022年对应的0、0.4、0.6、0.8、1日历线性载荷。因而SY是标准化抑郁得分的十年变化近似，SX是自由基底上的端点变化参数，不能统一解释为恒定年增长率。未使用调查权重外推全国总体。", None),
        ("主要父工作模型SW同时估计X和Y的基期与变化因子，保留SX与IY的条件残差关联，并允许五期X与Y的同波测量残差相关。所有增长因子均条件于基期控制集。同期剩余相关可以来自短期共同变化、访谈条件或其他遗漏因素，不能由该参数单独识别其来源。SY的条件残差自由估计；C1将该残差固定为零且不含五个同波关联，作为强约束敏感性。C1在结构上嵌套于SW，但涉及方差边界，不用普通df=6卡方参照作正式边界检验。", None),
        ("核心调节与资源差异", "afff0"),
        ("每种Z分别增加第三条增长轨迹。SD的Z轨迹采用自由形状，三种有符号差值采用日历线性；各分支的增长形式事先固定。每期X—Z和Y—Z测量残差关联与SW原有X—Y关联一并纳入，六个增长因子均条件于同一有效控制列。仅按常数或精确线性依赖移除子样本中的不可估计列，十份使用相同列集，不按P值删控制或残差关联。", None),
        ("三过程无交互D0与加入一个潜交互的D1分别评价。D1的抑郁变化方程为：SY＝α＋βIX·IX＋βSX·SX＋βIY·IY＋βIZ·IZ＋βSZ·SZ＋γᵀC＋δ(SX×IZ)＋u。核心参数为δ；模型中βSX是IZ＝0时的条件关联。该乘积中的X是变化因子SX，因此不能替代较高初始亲近度IX的缓冲检验；同一交叉导数的两种理论解释也不重复计为独立发现。父模型主路径不显著不禁止检验δ，D0不合法也不自动判定D1不成立；不使用不合法D0进行普通似然比检验。", None),
        ("潜变量乘积使用XWITH联合估计，保留测量和增长因子估计的不确定性。基础残差块和参数估计协方差须合法；乘积涉及的矩按非线性关系计算，不另给乘积虚构独立正态因子的方差。首份插补开展预定的积分精度和不同起点检查，后续使用通过检查的同规格设置；该数值复核只覆盖MI01，不宣称所有成员均做过额外起点检查。", None),
        ("如果某潜交互分支在限定检查内未获得可辩护估计，启用同一基期样本的观测2012年Z₀路线，并明确其估计对象已改变。观测路线保留两个SW增长过程，使增长因子及基期X/Y指标条件于Z₀，以反映同源基期关系信息。SD观测路线已事前指定用于三项资源对比，无论潜交互显著与否均执行。两种路线分表，不把观测Z₀称为潜在IZ的无损替代。", None),
        ("资源组G取0/1，分别表示小学及以下／初中及以上、乡村／城市、无／有个人收入。H4模型包含SX×Z₀、SX×G和Z₀×G及相应主项，核心三阶系数记为δG。G＝0组调节为δ，G＝1组为δ＋δG，组间差异为δG。组别由每份MI的基期取值及固定派生规则形成；有个人收入不等于高收入。H4.2b的当前检验因此仅覆盖三项资源的这一操作化。", None),
        ("合并、比较与推断范围", "afff0"),
        ("同一规格的全部十份插补均通过模型与预定数值检查，才按同名参数及完整协方差进行Rubin合并。总方差为组内方差均值W加上(1＋1/10)倍组间方差B。采用完整数据自由度趋于无穷的大样本近似及MI的t参照；不平均P值，不删除失败成员。报告条件95%区间、FMI及MCSE/SE，后两者不代表纵向信息充分或总区间狭窄。", None),
        ("条件斜率b(z)＝βSX＋δz先在每份MI计算，方差保留2z·Cov(βSX,δ)，再合并同一固定对比。预定z为−1、0、1；观测Z₀中超出实际范围的值明确标为外推，潜在IZ则是模型分布下的参考值。四个潜交互采用固定家族数4的Holm校正；观测路线另成家族数4的比较；三项H4组间差异单独作家族数3的Holm校正。缺少的检验保留缺失。", None),
        ("H4的资源0组、资源1组及差异共九个对比，另给出Bonferroni同时95%区间。只有两组调节方向相同且差异方向支持幅度增加或减少时，才分别作相应方向的理论判断；一组显著而另一组不显著不能代替差异检验。没有实质等效界值，区间包含零不判为无效应。", None),
        ("所有结果条件于固定模型和现有插补假设。实际插补预测矩阵包含基期Z特征，但未纳入完整SX×IZ分布、全部后期Z及相应非线性结构，不能证明与三过程潜交互严格相容。非线性和交互模型下的相容性需要另外评价（Bartlett等，2015）；常见回归的相容插补程序不能直接视为本研究LMS的通用解。预定的SD完整协变量子样本仅作诊断，不能将样本选择与插补影响分离。新的相容插补、家庭重抽样、增长形状、量尺和窗口敏感性未在本轮完成；以下状态表保留这些范围限制。", None),
    ]
    return [p(value,style) for value,style in values]

def result_row(pooled, z, spec, label):
    rows = [r for r in pooled if r["z"] == z and r["spec"] == spec and r["label"] == label]
    assert len(rows) <= 1, (z,spec,label)
    return rows[0] if rows else None

def group_result_text(pooled, z, spec):
    row = result_row(pooled,z,spec,"dc")
    if row is None:
        return None
    # 方向只作为数值方向；不自动把正/负乘积系数翻译为社会机制。
    side = "区间跨零，方向与幅度尚不明确" if float(row["lower"]) <= 0 <= float(row["upper"]) else "区间在零的同一侧；解释仍限于当前模型及多重比较范围"
    return ZN[z]+"的交互系数为"+fmt(row["estimate"])+"（SE＝"+fmt(row["se"])+"，95%区间"+ci(row)+"，P＝"+pv(row["p"])+"，Holm校正P＝"+pv(row.get("p_holm"))+"）。"+side+"。"

def core_table_rows(state,pooled,spec):
    nc = d.readjson(ROOT/"RUN_CONTRACT.json")["samples"]
    rows = []
    for z in ZN:
        q = result_row(pooled,z,spec,"dc")
        cells = [fmt(q["estimate"])+" ("+fmt(q["se"])+")",ci(q),pv(q["p"])+" / "+pv(q.get("p_holm"))] if q else ["—","—","—"]
        rows.append([ZN[z],str(nc[z])]+cells+[state_label(state[(z,spec)]["status"])])
    return rows

def display_spec(spec):
    return "H4 "+GN[spec.removeprefix("H4_")] if spec.startswith("H4_") else spec

def concise_reason(row):
    if row["status"] == "IN_PROGRESS":
        return "尚无该分支终态记录"
    reason = row.get("reason","")
    if "Pilot model inadmissible" in reason:
        return "MI01在限定检查后未通过模型验收；其余成员未执行"
    if "inadmissible after limited starting-value check" in reason:
        return "已执行成员在有限起点核查后仍不合法；后续成员未执行"
    if "Integration comparison failed" in reason:
        return "预定积分精度比较未通过，未合并"
    if "Alternative starting values not stable" in reason:
        return "不同起点比较未通过，未合并"
    if "family not pooled" in reason:
        return "某成员未通过验收，保留失败成员并停止该家族合并"
    if boolean(row["eligible"]):
        return "十份成员均通过；交互家族另通过MI01积分与起点核查"
    return reason or state_label(row["status"])

def parent_model_rows():
    fits = d.readcsv(ROOT/"provenance_SW/model_fit.csv")
    rows = []
    for spec,label in (("SW","主要工作模型"),("C1","强约束敏感性"),("XLIN","未采用")):
        f = [r for r in fits if re.fullmatch(spec+r"_MI\d{2}",r["id"])]
        assert len(f) == 10
        def span(key):
            vals = [float(x[key]) for x in f]
            return fmt(min(vals))+"–"+fmt(max(vals))
        rows.append([spec,"10/10" if spec != "XLIN" else "0/10",span("CFI"),span("TLI"),span("RMSEA_Estimate"),
            "MI01稳定" if spec != "XLIN" else "未执行：MI01不合法",label])
    return rows

def seven_issue_rows(state):
    n = sum(boolean(state[(z,"D1")]["eligible"]) for z in ZN)
    hg = sum(boolean(state[("SD","H4_"+g)]["eligible"]) for g in GN)
    return [
        ["1 趋势、时间、窗口","部分解决","修正后的旧显著下降结论已撤回；时间尺度明确；本轮未做量尺和窗口敏感性。"],
        ["2 CES-D计分与范围","计分及实际入口已解决","共同八题、两项反向、完整作答和固定基期标准化已绑定；测量不变性仍属独立问题。"],
        ["3 增长方差与识别","父模型层面已解决","SW合法；新增三过程及交互逐项评价，不由父模型通过推定全部通过。"],
        ["4 拟合不足","SW工作模型可采用","同波剩余关联改善分解；不是唯一真实结构，Y形状敏感性未完成。"],
        ["5 表述与版本","本轮同步修订","SW置首，限定相对指标和收入含义；历史98表独立归档，不作为当前验证。"],
        ["6 得分、调节与MI","部分解决",f"计分SE与家庭共同值具体问题已关闭；四潜调节中{n}项可合并；插补与潜交互相容性仍未证明。"],
        ["7 H4.2b","按实际对比状态报告",f"三资源差异中{hg}项可合并；方向判定见附表A12，不比较组内星号；其他差异指标未检验。"],
    ]

def results_nodes(state,pooled,slopes,h4,decisions,sw,current,tab,preview):
    out = [p("研究结果","affe"),p("主要父工作模型与轨迹关联","afff0")]
    out += tab("表2 主要父模型与敏感性模型的采用情况",["模型","合法成员","CFI范围","TLI范围","RMSEA范围","起点复核范围","采用位置"],
        parent_model_rows(),[650,850,1150,1150,1250,2450,1500])
    out += [p("注：表内拟合范围是十份成员的描述，不是合并拟合统计量。SW与C1的新增起点复核各仅涉及MI01；XLIN未追加起点核查。采用不依据关系P值。",size=18)]
    out += tab("表3 SW主要父模型的条件MI关系",["路径","估计","SE","95%区间","P"],
        [[PATH[k],fmt(sw[k]["estimate"]),fmt(sw[k]["se"]),ci(sw[k]),pv(sw[k]["p"])] for k in ("bii","bis","bss","bsyiy")],
        [3200,1100,1100,2600,1000])
    out += [p("在SW工作模型下，较高的亲近度基期水平与较低的抑郁基期水平相关。亲近度变化与抑郁变化的点估计为"+fmt(sw["bss"]["estimate"])+"，95%区间为"+ci(sw["bss"])+"，其范围同时包含负向和正向关联。因此，当前结果不能确定这种变化关联的方向和幅度，也不能据此断言关系改善没有作用。"),
        p("X的中间自由载荷及五期同波剩余关联见附表A6。它们体现模型如何将短期同波偏离与长期变化关联分开，而非某个单独心理机制的验证。SY条件残差虽为正，但其估计仍不精确；潜变量几何合法与精度充分是不同问题。"),
        p("先前单变量自由形状诊断中的变化均值0.037，属于原始CES-D尺度及0/10端点锚定；将同一模型改为0/1锚定时为0.370，标准误相应变换而P值不变。它不等于当前标准化SW的均值，也不代表恒定年下降。此前基于错误计分的显著下降结论已撤回。"),
        p("四项家内差异调节","afff0"),p(current)]
    out += tab("表4 四项潜在基期家内差异的核心交互",["差异Z","基期N","δ (SE)","95%区间","P / Holm P","当前状态"],
        core_table_rows(state,pooled,"D1"),[850,650,1550,2100,1150,2700])
    texts = [group_result_text(pooled,z,"D1") for z in ZN]
    out += [p(x) for x in texts if x]
    if not any(texts):
        out += [p("本表没有可报告的潜交互合并系数。各分支的估计与数值核查状态见附表A9；这表示当前执行证据不能支持相应条件MI推断，不是四种调节均等于零的结论。")] if not preview else [p("潜交互仍在计算，空格表示尚无完成并验收的合并结果。")]
    out += [p("三个有符号差值已反向，数值较大表示原假设预定的相对不利方向。交互系数的正负只有结合条件斜率、指标含义和参考范围，才能解释为某种条件关联增强或减弱；不单凭符号给机制命名。"),
        p("观测基期差异的另一定义","afff0")]
    out += tab("表5 观测2012年差异的交互：预定SD路线及触发的备用分支",["差异Z₀","基期N","δ (SE)","95%区间","P / Holm P","当前状态"],
        core_table_rows(state,pooled,"E1"),[850,650,1550,2100,1150,2700])
    out += [p(x) for x in [group_result_text(pooled,z,"E1") for z in ZN] if x]
    out += [p("该表估计的是实际2012年差异Z₀的调节，不是利用多期测量估计的潜在IZ调节。SD的基期标准化最小值约为−0.476，约75.6%的原始SD为零，故预定z＝−1超出观测及非负SD允许的范围。附表A11保留这一参考点并明确标为外推，不能把它称为实际低差异组。"),
        p("社会经济资源的组间调节差异","afff0")]
    rows = []
    for g in GN:
        q = [r for r in h4 if r["resource"] == g and r["contrast"] == "difference"]
        a = q[0] if q else None
        judge = next((r["judgment"] for r in decisions if r["resource"] == g),"NOT_ESTIMABLE")
        rows.append([GN[g],fmt(a["estimate"])+" ("+fmt(a["se"])+")" if a else "—",ci(a) if a else "—",
            pv(a["p"]) if a else "—",pv(a.get("p_holm_difference")) if a else "—",
            JUDGMENT[judge] if a else state_label(state[("SD","H4_"+g)]["status"])])
    out += tab("表6 SD观测路线的资源组间调节差异",["资源G","δG (SE)","95%区间","P","Holm P","方向及幅度判断"],rows,[1300,1700,2100,700,800,2400])
    out += [p("G＝1分别是初中及以上、城市、有个人收入；G＝0是相应参照组。表中δG直接对应两组调节之差，组别自身的简单斜率显著性不作替代。组内δ及δ＋δG、九项对比的同时区间和H4.2b方向判定见附表A12。若两组调节方向尚不能确定，则不因某个差异系数有星号就宣布“更敏感”。")]
    for g in GN:
        qs = [r for r in h4 if r["resource"] == g]
        if len(qs) == 3:
            q = {r["contrast"]:r for r in qs}
            judge = next(r["judgment"] for r in decisions if r["resource"] == g)
            out += [p(GN[g]+"对比中，资源0组调节为"+fmt(q["delta_low"]["estimate"])+"，资源1组为"+fmt(q["delta_high"]["estimate"])+"，差异为"+fmt(q["difference"]["estimate"])+"。同时区间判定为“"+JUDGMENT[judge]+"”；结论仅限于观测SD和该资源操作化。")]
    out += [p("原假设的检验范围","afff0")]
    out += tab("表7 原假设与当前证据范围",["假设","原预测","当前证据及未检验范围"],hypothesis_rows(state,decisions),[1000,2700,5300])
    out += [p("讨论","affe"),p("本研究区分了家庭总体亲近度、对不同子女的相对评价以及这些特征的时间变化。在当前可采用的父工作模型下，基期亲近度与基期抑郁的负向关联与理论预期相容；变化之间的估计则较为宽泛。基期关联不能替代动态变化关联，更不能由观察性轨迹直接推断改善关系的干预效果。"),
        p("家内差异的含义取决于其操作化。本研究的标准差先除以同波均值，衡量相对分散；性别差和排行差也按同波均值相对化。它们与总体亲近度共享评分来源和分母，不能把比值的变化全部归为绝对分散或绝对关系质量的变化，也不直接测量矛盾心理、家庭冲突或资源协商。多期潜在初始状态与实际基期观测状态并不相同。解释结果时应保留这些区别，不能将较小的儿子—女儿差值直接写成父母与儿子绝对疏远。"),
        p("模型分解本身具有实质影响：允许同期剩余关联后，合法的长期变化分解可以得到，但这没有唯一识别先前负方差的来源。C1与SW同时改变零残差限制和同波关联；附表A8的固定残差剖面只在第一份MI和C1结构中计算，是敏感性描述，不是SW残差方差的置信集合，也不用于挑选使P值最小的约束。"),
        p("本研究有几项具体限制。样本要求基期年龄大于60岁、多子女亲近度回答及后续观测，死亡、代答、未追访和结构性资格变化可能影响代表性。SD有明显零值集中，亲近度为有界等级评分；连续潜增长和LMS的分布近似因此需要谨慎。现有协变量插补尚未证明与潜交互相容，且跨期测量不变性、自由Y形状、其他量尺和四期窗口没有在本轮完成。当前区间也不包含模型选择不确定性。"),
        p("上述范围限定允许将可报告关联、估计不精确和暂未取得可辩护估计的研究问题分开。当前证据不支持把全部家内差异假设统一宣布为已验证或已被否定；社会政策讨论应限于识别需要进一步研究的家庭关系维度，不能据这些系数承诺治理或干预收益。")]
    return out

def extra_references():
    return [
        ("bartlett", "2015", "Bartlett J. W.、Seaman S. R.、White I. R.、Carpenter J. R.，for the Alzheimer's Disease Neuroimaging Initiative（2015）。Multiple imputation of covariates by fully conditional specification: Accommodating the substantive model。Statistical Methods in Medical Research，24(4)，462–487。https://doi.org/10.1177/0962280214521348"),
        ("raudenbush", "1992", "Raudenbush S. W.、Chan W.-S.（1992）。Growth Curve Analysis in Accelerated Longitudinal Designs。Journal of Research in Crime and Delinquency，29(4)，387–411。https://doi.org/10.1177/0022427892029004001"),
        ("van buuren", "2011", "van Buuren S.、Groothuis-Oudshoorn K.（2011）。mice: Multivariate Imputation by Chained Equations in R。Journal of Statistical Software，45(3)，1–67。https://doi.org/10.18637/jss.v045.i03"),
    ]

def appendix_nodes(state,pooled,slopes,h4):
    out = [p("当前分析附录（v41）","affe"),p("本附录与正文v49使用同一结果批次。模型代码、原始聚合输出及高精度协方差另行提供；逐人数据和插补对象不在公开附件内。历史98张表保留于旧版审计材料，不作为本轮新估计结果。")]
    def tab(title,headers,rows,widths=None,size=19):
        return d.table(title,headers,rows,"appendix",widths=widths,total_width=14000,size=size)
    zc = d.readjson(ROOT/"audit/Z_CONTRACT.json")
    rows = [["X 均值","3274","4.1089078464","0.7092542690","正向","自由；两端0/1"],
            ["Y CES-D 8","3274","13.5754428833","4.2592386459","高分症状重","线性；0/.4/.6/.8/1"]]
    for z in ZN:
        r = zc["z"][z]
        rows.append([ZN[z],str(zc["samples"][z+"_Z0"]["N"]),fmt(r["ref_mean"],8),fmt(r["ref_sd"],8),"正向" if r["orientation"] == 1 else "反向","自由" if r["shape"] == "free" else "日历线性"])
    out += tab("附表A1 指标标准化与增长参数尺度",["指标","基期N","标准化前基期均值","标准化前基期SD","方向","增长形式"],rows)
    out += [p("X/Y使用共同3274人队列的固定基期参照。Z先计算100×原始SD或差值/同波均值，再使用各自基期资格样本的均值、SD标准化；三个有符号差值乘−1。原始差值方向见正文表1。SD的Z轨迹与X均为自由基底，不能按常数年变化解释。",size=18)]
    desc = d.readcsv(ROOT/"audit/observed_longitudinal_descriptives.csv")
    reliability = {r["year"]:r for r in d.readcsv(ROOT/"audit/CESD_reliability_bound.csv")}
    rows = []
    for year in ("2012","2016","2018","2020","2022"):
        x = next(r for r in desc if r["year"] == year and r["variable"] == "wfd_m")
        y = next(r for r in desc if r["year"] == year and r["variable"] == "ces8")
        a = reliability[year]
        assert a["N"] == y["N"]
        rows.append([year,x["N"],fmt(x["mean"]),fmt(x["sd"]),y["N"],fmt(y["mean"]),fmt(y["sd"]),fmt(a["alpha"])])
    out += tab("附表A2 各期实际观测与共同八题信度",["年份","X人数","X均值","X标准差","Y人数","Y均值","Y标准差","CES-D α"],rows)
    out += [p("均值为当期实际观测者的原始分数，样本构成随期次变化，不能直接解释为个体内趋势。α来自此前修正逐题审计，本轮通过当前队列的总分、缺失掩码及人数精确绑定；本轮未再次读取全部原始条目。CES-D总分8—32，仅八题均有效时求和。",size=18)]
    controls = d.readcsv(ROOT/"audit/baseline_controls_descriptives.csv")
    out += tab("附表A3 二十四项基期控制列：实际编码与插补前缺失",["列","变量","定义与参照","有效N","缺失N","均值","SD"],
        [[r["model_column"],r["variable"],r["definition"],r["observed"],r["missing"],fmt(r["mean"]),fmt(r["sd"])] for r in controls],
        [650,1450,5400,1100,1100,2100,2200])
    out += [p("这里的24项是实际编码列，部分属于同一分类变量的虚拟列。均值以原观测为分母，二分类均值即1的比例；缺失数在恢复真实2012年来源后计算。家庭收入与个人收入为万元，自评相对收入为1—5级。",size=18)]
    zd = d.readcsv(ROOT/"audit/moderator_descriptives.csv")
    out += tab("附表A4 各差异分支的观测覆盖与分布",["Z","年份","基期资格内有效N","基期资格内缺失N","零值比例","标准化最小值","中位数","最大值"],
        [[ZN[r["z"]],r["year"],r["N_in_baseline_sample"],r["N_missing_in_baseline_sample"],fmt(r["share_zero"]),fmt(r["min"]),fmt(r["median"]),fmt(r["max"])] for r in zd])
    out += [p("覆盖列以各分支基期资格样本为分母；零值比例和分位数限于该资格样本中当期有效观测者。结构无定义与其他未观测不混称为同一缺失机制。",size=18)]
    elig = {r["z"]:r for r in d.readcsv(ROOT/"audit/baseline_Z_eligibility.csv")}
    drop = d.readcsv(ROOT/"audit/control_column_decisions.csv")
    rows = []
    for z in ZN:
        r,s = elig[z],zc["samples"][z+"_Z0"]
        removed = "、".join(x["column"]+"("+x["variable"]+")" for x in drop if x["z"] == z and not boolean(x["retained"])) or "无"
        rows.append([ZN[z],str(s["N"]),str(s["households"]),r["known_structure_undefined"],r["other_baseline_unavailable"],str(s["later_only_excluded"]),removed])
    out += tab("附表A5 基期资格、结构性无定义与控制列处理",["Z","分析N","家庭数","已知结构无定义","其他基期不可用","仅后期可用而排除","移除控制列"],rows)
    out += [p("三类缺失/排除计数描述的集合不同，不应全部相加。仅后期可用者不进入当前基期资格样本。性别差分支因子女性别构成恒定移除c8/c9；长子差移除c9；均采用确定性规则且十份一致。",size=18)]
    ss = d.readcsv(ROOT/"results/SW_structure_pooled.csv")
    def sn(label):
        if label.startswith("X_loading_"):
            return "X载荷 "+label[-4:]
        if label.startswith("XY_residual_cov_"):
            return "同波XY残差协方差 "+label[-4:]
        if label.startswith("XY_residual_cor_"):
            return "同波XY残差相关 "+label[-4:]
        return "增长条件残差方差 "+label.split("_")[-1]
    out += tab("附表A6 SW自由载荷、同波残差与增长条件残差",["参数","条件MI估计","SE","95%区间","十份点估计范围"],
        [[sn(r["label"]),fmt(r["estimate"],5),fmt(r["se"],5),ci(r,5),fmt(r["minimum_member_estimate"],5)+"–"+fmt(r["maximum_member_estimate"],5)] for r in ss],
        [4100,2000,1900,3200,2800])
    out += [p("X的2012/2022载荷固定为0/1，Y载荷固定0/.4/.6/.8/1；固定参数没有对应检验P值。残差相关由逐份参数和完整协方差经delta法后合并，不是独立新增发现。方差行的正态近似区间可能跨负值，这是精度描述，不是合法的负人口方差或正式边界检验。",size=18)]
    paths = d.readcsv(ROOT/"provenance_SW/conditional_MI_paths.csv")
    paths.sort(key=lambda r:(0 if r["spec"] == "SW" else 1,list(PATH).index(r["label"])))
    out += tab("附表A7 SW与C1的主要路径及MI精度",["规格","路径","估计","SE","95%区间","P","FMI","MCSE/SE"],
        [[r["spec"],PATH[r["label"]],fmt(r["estimate"]),fmt(r["se"]),ci(r),pv(r["p"]),fmt(r["FMI"],5),fmt(r["MCSE_over_SE"],5)] for r in paths],
        [800,3300,1300,1300,3000,1000,1600,1700])
    profile = d.readcsv(ROOT/"provenance_SW/profile_MI01.csv")
    out += tab("附表A8 C1结构第一份MI的固定SY残差剖面",["固定方差τ","对数似然","SX→SY","SE","单份95%区间","IX→SY","IY→SY"],
        [[fmt(tau,2),fmt(q["bss"]["LL"]),fmt(q["bss"]["estimate"]),fmt(q["bss"]["se"]),ci(q["bss"]),fmt(q["bis"]["estimate"]),fmt(q["bsyiy"]["estimate"])]
         for tau in sorted({float(r["tau"]) for r in profile})
         for q in [{r["label"]:r for r in profile if float(r["tau"]) == tau}]])
    out += [p("每个固定点均重新估计其他自由参数，0点复用C1/MI01。这里的结构不含SW五个同波XY残差协方差；只用MI01。固定点区间和其并集都不是SW的95%置信集合，对数似然仅描述固定假设间拟合变化。",size=18)]
    out += tab("附表A9 四Z及三资源分支的执行与采用状态",["Z","规格","当前状态","详细原因"],
        [[ZN[z],display_spec(spec),state_label(r["status"]),concise_reason(r)] for (z,spec),r in state.items()],
        [1100,1400,3800,7700],size=18)
    out += [p("D0/D1分别是三过程无/有核心潜交互，E0/E1是两过程加观测2012年Z₀的无/有交互。H4包含三阶资源差异。未触发备用、未执行、未完成、不能合并与可报告条件MI估计分别保留；空系数不是零。",size=18)]
    if pooled:
        out += tab("附表A10 本轮所有可报告核心路径及合并精度",["Z","规格","参数","估计","SE","95%区间","P","Holm P","FMI","MCSE/SE"],
            [[ZN[r["z"]],display_spec(r["spec"]),r["label"],fmt(r["estimate"]),fmt(r["se"]),ci(r),pv(r["p"]),pv(r.get("p_holm")),fmt(r["FMI"],4),fmt(r["MCSE_over_SE"],4)] for r in pooled],
            [900,1250,1050,1300,1300,3750,1000,1050,1200,1200],size=18)
    else:
        out += [p("附表A10 本轮可报告核心路径","af3"),p("当前无通过全部合并条件的路径；不列伪造系数或P值。")]
    out += [p("参数名："+"；".join(k+"＝"+v for k,v in PATH.items())+"。只对预定交互家族给Holm值，其余空格为不适用。",size=18)]
    if slopes:
        out += tab("附表A11 条件斜率：固定参考值与支持范围",["Z","规格","z","b(z)","SE","95%区间","P","参考含义与支持"],
            [[ZN[r["z"]],r["spec"],r["reference_z"],fmt(r["estimate"]),fmt(r["se"]),ci(r),pv(r["p"]),
              "潜IZ高斯参考" if r["spec"] == "D1" else "外推：超出实际范围" if "EXTRAPOLATION" in r["support_status"] else "在观测范围内"] for r in slopes],
            [1050,1000,650,1350,1350,2900,1000,4700])
    else:
        out += [p("附表A11 条件斜率","af3"),p("当前无可合并交互路径，未生成条件斜率。")]
    out += [p("三参考值事前固定为−1、0、1。潜IZ与观测Z₀是不同尺度对象；观测SD的−1属于外推。模型支持范围不等于观测在该处密集。完整协方差参与逐份对比方差计算。",size=18)]
    if h4:
        out += tab("附表A12 三资源的组内调节、直接差异及同时区间",["资源","对比","估计","SE","95%区间","同时95%区间","P","差异Holm P"],
            [[GN[r["resource"]],{"delta_low":"G=0调节","delta_high":"G=1调节","difference":"G=1减G=0"}[r["contrast"]],fmt(r["estimate"]),fmt(r["se"]),ci(r),
              "["+fmt(r["simultaneous_lower"])+", "+fmt(r["simultaneous_upper"])+"]",pv(r["p"]),pv(r.get("p_holm_difference"))] for r in h4],
            [1300,1900,1500,1300,2700,2800,1100,1400])
    else:
        out += [p("附表A12 三资源的组间调节对比","af3"),p("当前没有可合并对比；各资源分支的执行状态见附表A9。")]
    out += [p("同时区间按事前九个对比使用Bonferroni参照，即便部分对比不可估也不缩小家族。两组同向且差异显示幅度较大/较小，才分别支持当前操作化下H4.2b/H4.2a方向；方向不明不改写假设。",size=18)]
    ccfile = ROOT/"results/SD_completecase_diagnostic.json"
    out += [p("附表A13 SD完整协变量诊断","af3")]
    if ccfile.exists():
        cc = d.readjson(ccfile)["receipt"]
        kpfile = ROOT/"models/SD/D1_CC_MI01/completecase/key_paths.csv"
        dc = next((r for r in d.readcsv(kpfile) if r["label"] == "dc"),None) if kpfile.exists() else None
        out += tab("附表A13a 诊断执行结果",["样本N","家庭数","模型状态","δ","SE","用途"],
            [[str(cc["N"]),str(cc["households"]),cc["status"],fmt(dc["estimate"]) if dc and boolean(cc["usable"]) else "—",fmt(dc["se"]) if dc and boolean(cc["usable"]) else "—","单样本诊断；未独立核查积分及起点"]])
    else:
        out += [p("本轮执行终点前尚未完成该诊断。预定样本为2830人、2105个家庭；不据此宣布插补相容或不相容。")]
    out += [p("完整协变量分析与MI队列样本构成不同，差异不能唯一归因于插补；本诊断不作正式十份MI推断，也不能修补失败的调节家族。",size=18)]
    out += tab("附表A14 七项意见的当前状态与范围",["原问题","状态","已经达到和仍未完成的范围"],seven_issue_rows(state),[2900,2900,8200])
    out += [p("复核与复现范围","afff0"),p("本轮独立程序检查原始打印参数、高精度参数、TECH1位置、TECH3参数协方差、适用的模型矩阵及固定对比合并。该程序的通过是交付数字一致性的证据，不是另一份独立人群样本，也不证明模型假设真实。实际调用登记、每份采用回执及未执行原因随公开数据包提供。外部网页端本轮是否复核，应以其后续实际回复为准。")]
    return out

if __name__ == "__main__":
    main()
