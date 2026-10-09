"""保留Word母版、引文字段和实际引用对象，清除已不被正文引用的历史对象。"""
from pathlib import Path, PurePosixPath
from copy import deepcopy
from datetime import datetime, timezone
from lxml import etree as E
import csv
import hashlib
import json
import math
import posixpath
import re
import zipfile

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
W = "{"+NS["w"]+"}"
R = "{"+NS["r"]+"}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
CT = "{http://schemas.openxmlformats.org/package/2006/content-types}"
TABLE_EVIDENCE = []

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def readcsv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def readjson(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def text(node):
    return "".join(node.xpath(".//w:t/text()", namespaces=NS))

def number(x, digits=3):
    try:
        v = float(x)
        return f"{v:.{digits}f}".replace("-", "−") if math.isfinite(v) else "—"
    except (ValueError, TypeError):
        return "—"

def pvalue(x):
    try:
        v = float(x)
        if not math.isfinite(v) or not 0 <= v <= 1:
            return "—"
        return "<.001" if v < .001 else f"{v:.3f}".removeprefix("0")
    except (ValueError, TypeError):
        return "—"

def interval(row, digits=3):
    return "["+number(row["lower"], digits)+", "+number(row["upper"], digits)+"]"

def paragraph(value, style=None, size=None, center=False, keep=False):
    node = E.Element(W+"p")
    prop = E.SubElement(node, W+"pPr")
    if style:
        E.SubElement(prop, W+"pStyle", {W+"val":style})
    if style or keep:
        E.SubElement(prop, W+"keepNext")
    E.SubElement(prop, W+"widowControl")
    E.SubElement(prop, W+"spacing", {W+"after":"100"})
    if center:
        E.SubElement(prop, W+"jc", {W+"val":"center"})
    run = E.SubElement(node, W+"r")
    if size:
        rp = E.SubElement(run, W+"rPr")
        E.SubElement(rp, W+"sz", {W+"val":str(size)})
        E.SubElement(rp, W+"szCs", {W+"val":str(size)})
    t = E.SubElement(run, W+"t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = str(value)
    return node

def table(title, headers, rows, document, widths=None, total_width=9000, size=19):
    """每格记录期望文本，供最终PDF按实际行列验证，不用全文字符串出现代替。"""
    headers = list(map(str, headers))
    rows = [list(map(str, row)) for row in rows]
    assert all(len(row) == len(headers) for row in rows)
    if widths is None:
        widths = [total_width//len(headers)]*len(headers)
        widths[-1] += total_width-sum(widths)
    assert sum(widths) == total_width and len(widths) == len(headers)
    node = E.Element(W+"tbl")
    prop = E.SubElement(node, W+"tblPr")
    E.SubElement(prop, W+"tblW", {W+"w":str(total_width), W+"type":"dxa"})
    E.SubElement(prop, W+"tblLayout", {W+"type":"fixed"})
    E.SubElement(prop, W+"jc", {W+"val":"center"})
    margins = E.SubElement(prop, W+"tblCellMar")
    for edge in ("top","bottom","left","right"):
        E.SubElement(margins, W+edge, {W+"w":"65", W+"type":"dxa"})
    borders = E.SubElement(prop, W+"tblBorders")
    for edge in ("top","left","bottom","right","insideH","insideV"):
        E.SubElement(borders, W+edge, {W+"val":"single", W+"sz":"4", W+"color":"808080"})
    grid = E.SubElement(node, W+"tblGrid")
    for width in widths:
        E.SubElement(grid, W+"gridCol", {W+"w":str(width)})
    for i, row in enumerate([headers]+rows):
        tr = E.SubElement(node, W+"tr")
        trp = E.SubElement(tr, W+"trPr")
        E.SubElement(trp, W+"cantSplit")
        if i == 0:
            E.SubElement(trp, W+"tblHeader")
        for j, value in enumerate(row):
            tc = E.SubElement(tr, W+"tc")
            tcp = E.SubElement(tc, W+"tcPr")
            E.SubElement(tcp, W+"tcW", {W+"w":str(widths[j]), W+"type":"dxa"})
            E.SubElement(tcp, W+"vAlign", {W+"val":"center"})
            if i == 0:
                E.SubElement(tcp, W+"shd", {W+"val":"clear", W+"fill":"E8EDF2"})
            par = paragraph(value, size=size, keep=(i == 0 or (len(rows) <= 8 and i < len(rows))))
            par.find(W+"pPr").append(E.Element(W+"ind", {W+"firstLine":"0", W+"firstLineChars":"0",
                W+"left":"0",W+"right":"0",W+"leftChars":"0",W+"rightChars":"0"}))
            par.find(W+"pPr").append(E.Element(W+"jc", {W+"val":"left"}))
            # 中文Word默认按字符换行；数值短格用noWrap保护负号与数字。
            if value.startswith("[") or re.fullmatch(r"[−<.\d]+", value):
                E.SubElement(tcp, W+"noWrap")
            tc.append(par)
    TABLE_EVIDENCE.append(dict(document=document, title=title, headers=headers, rows=rows))
    return [paragraph(title, "af3", keep=True), node]

def replace_plain(nodes, index, value, changes):
    old = nodes[index]
    assert not old.findall(".//w:instrText", NS), "Do not flatten a cited paragraph"
    changes.append(dict(source_body_index=index, before=text(old), after=value))
    new = paragraph(value)
    prop = old.find(W+"pPr")
    if prop is not None:
        new.remove(new.find(W+"pPr"))
        new.insert(0, deepcopy(prop))
    nodes[index] = new

def replace_text_span(node, old, new):
    """只编辑可见文字；禁止跨域替换引注，保存所有instrText原字节内容。"""
    elements = node.findall(".//w:t", NS)
    complete = "".join(e.text or "" for e in elements)
    count = complete.count(old)
    if count == 0:
        return 0
    assert count == 1, ("Ambiguous prose replacement", old, count)
    start, end = complete.index(old), complete.index(old)+len(old)
    cursor, inserted = 0, False
    before_fields = node.xpath(".//w:instrText/text()", namespaces=NS)
    for e in elements:
        s = e.text or ""
        a, b = cursor, cursor+len(s)
        cursor = b
        if b <= start or a >= end:
            continue
        lo, hi = max(start-a, 0), min(end-a, len(s))
        e.text = s[:lo]+(new if not inserted else "")+s[hi:]
        inserted = True
    assert text(node) == complete.replace(old, new)
    assert before_fields == node.xpath(".//w:instrText/text()", namespaces=NS)
    return 1

def bibliography(nodes, extra=None):
    codes = "".join("".join(n.xpath(".//w:instrText/text()", namespaces=NS)) for n in nodes)
    items, citations, suffixes = {}, [], {}
    for match in re.finditer(r"ADDIN\s+ZOTERO_ITEM\s+CSL_CITATION\s*", codes):
        obj, _ = json.JSONDecoder().raw_decode(codes[match.end():].lstrip())
        citations.append(obj)
        for item in obj.get("citationItems", []):
            d = item.get("itemData", {})
            items[str(d.get("id", item.get("id")))] = d
    # 只映射原文已经使用的年度后缀，不凭排序为其重新编号。
    known_suffixes = {"10.1080/13607863.2020.1711867":"a",
        "10.1017/S0144686X21000283":"b",
        "10.1017/S0144686X24000795":"a",
        "10.1093/sf/soaf214":"b"}
    rendered = []
    for key, item in items.items():
        d = deepcopy(item)
        doi = d.get("DOI", "")
        suffix = known_suffixes.get(doi, "")
        suffixes[key] = suffix
        authors = "、".join(a.get("literal") or " ".join(filter(None, [a.get("family"),a.get("given")])) for a in d.get("author",[]))
        issued = d.get("issued",{}).get("date-parts",[[]])
        year = str(issued[0][0]) if issued and issued[0] else "年份待核"
        value = f'{authors}（{year}{suffix}）。{d.get("title","")}。{d.get("container-title","")}'
        for field in ("volume","issue","page","publisher"):
            if d.get(field):
                value += "，"+str(d[field])
        if doi:
            value += "。https://doi.org/"+doi
        rendered.append((authors.casefold(), year+suffix, value))
    if extra:
        rendered.extend(extra)
    return [x[2] for x in sorted(rendered)], dict(items=items, citation_count=len(citations), year_suffixes=suffixes)

def resolve_part(rel_path, target):
    if rel_path == "_rels/.rels":
        base = ""
    else:
        base = str(PurePosixPath(rel_path).parent.parent)
    return posixpath.normpath(posixpath.join(base, target))

def save_document(source, destination, nodes, changes, new_images=None, appendix=False):
    source, destination = Path(source), Path(destination)
    with zipfile.ZipFile(source) as z:
        parts = {n:z.read(n) for n in z.namelist()}
    original = dict(parts)
    tree = E.fromstring(parts["word/document.xml"])
    body = tree.find("w:body", NS)
    section = deepcopy(body.find("w:sectPr", NS))
    for child in list(body):
        body.remove(child)
    body.extend(nodes)
    body.append(section)
    # 正文采用A4纵向，附录沿用横向Letter；完整保留母版文字样式。
    for sec in tree.findall(".//w:sectPr", NS):
        size = sec.find(W+"pgSz")
        if size is None:
            size = E.SubElement(sec, W+"pgSz")
        size.attrib.update({W+"w":"15840" if appendix else "11906",
                            W+"h":"12240" if appendix else "16838",
                            W+"orient":"landscape" if appendix else "portrait"})
        margin = sec.find(W+"pgMar")
        if margin is None:
            margin = E.SubElement(sec, W+"pgMar")
        for edge in ("top","bottom","left","right"):
            margin.set(W+edge, "720" if appendix else "1440")
        margin.set(W+"footer","720")
    removed_notes = {}
    for kind in ("footnote","endnote"):
        name = f"word/{kind}s.xml"
        used = {e.get(W+"id") for e in tree.findall(f".//w:{kind}Reference",NS)}
        if name not in parts:
            assert not used
            continue
        note_tree = E.fromstring(parts[name])
        removed = []
        for node in list(note_tree):
            id_ = node.get(W+"id")
            if id_ not in used and int(id_) > 0:
                removed.append(id_)
                note_tree.remove(node)
        assert used <= {e.get(W+"id") for e in note_tree}
        parts[name] = E.tostring(note_tree, xml_declaration=True, encoding="UTF-8", standalone=True)
        removed_notes[kind] = removed
    rels_name = "word/_rels/document.xml.rels"
    rels = E.fromstring(parts[rels_name])
    if new_images:
        for rid, filename, data in new_images:
            assert not any(e.get("Id") == rid for e in rels)
            E.SubElement(rels, REL+"Relationship", Id=rid, Type=NS["r"]+"/image", Target="media/"+filename)
            parts["word/media/"+filename] = data
    referenced = {v for element in tree.iter() for key,v in element.attrib.items() if key in (R+"id",R+"embed",R+"link")}
    removed_relationships = []
    for relation in list(rels):
        if relation.get("Type","").endswith("/image") and relation.get("Id") not in referenced:
            removed_relationships.append(relation.get("Id"))
            rels.remove(relation)
    # 当前稿件加入独立页码；不同节、首页与偶数页均明确绑定。
    if True:
        for sec in tree.findall(".//w:sectPr",NS):
            for el in list(sec):
                if el.tag == W+"footerReference":
                    sec.remove(el)
        rid, part = "rIdRound2DFooter", "word/footer_round2D.xml"
        footer = E.Element(W+"ftr", nsmap={"w":NS["w"]})
        fp = paragraph("附录  " if appendix else "", center=True)
        run = E.SubElement(fp, W+"r")
        E.SubElement(run, W+"fldChar", {W+"fldCharType":"begin"})
        run = E.SubElement(fp, W+"r")
        E.SubElement(run, W+"instrText").text = " PAGE "
        run = E.SubElement(fp, W+"r")
        E.SubElement(run, W+"fldChar", {W+"fldCharType":"end"})
        footer.append(fp)
        parts[part] = E.tostring(footer, xml_declaration=True, encoding="UTF-8", standalone=True)
        E.SubElement(rels, REL+"Relationship", Id=rid, Type=NS["r"]+"/footer", Target="footer_round2D.xml")
        for sec in tree.findall(".//w:sectPr",NS):
            for kind in ("default","even","first"):
                sec.insert(0,E.Element(W+"footerReference", {W+"type":kind,R+"id":rid}))
        content = E.fromstring(parts["[Content_Types].xml"])
        E.SubElement(content, CT+"Override", PartName="/"+part, ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml")
        parts["[Content_Types].xml"] = E.tostring(content, xml_declaration=True, encoding="UTF-8", standalone=True)
    parts[rels_name] = E.tostring(rels, xml_declaration=True, encoding="UTF-8", standalone=True)
    # 去除无人引用的媒体；其他部件的关系也纳入检查，避免误删页眉等使用的图片。
    targeted = set()
    for name, data in parts.items():
        if name.endswith(".rels"):
            for relation in E.fromstring(data):
                if relation.get("TargetMode") != "External":
                    targeted.add(resolve_part(name, relation.get("Target","")))
    removed_media = [name for name in parts if name.startswith("word/media/") and name not in targeted]
    for name in removed_media:
        del parts[name]
    # 历史缩略图可能显示旧显著性图，清除缩略图及其根关系。
    thumbnails = [name for name in parts if name.startswith("docProps/thumbnail")]
    for name in thumbnails:
        del parts[name]
    if thumbnails and "_rels/.rels" in parts:
        rr = E.fromstring(parts["_rels/.rels"])
        for rel in list(rr):
            if resolve_part("_rels/.rels", rel.get("Target","")) in thumbnails:
                rr.remove(rel)
        parts["_rels/.rels"] = E.tostring(rr, xml_declaration=True, encoding="UTF-8", standalone=True)
    content = E.fromstring(parts["[Content_Types].xml"])
    for el in list(content):
        if el.tag == CT+"Override" and el.get("PartName","").lstrip("/") not in parts:
            content.remove(el)
    parts["[Content_Types].xml"] = E.tostring(content, xml_declaration=True, encoding="UTF-8", standalone=True)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    if "docProps/core.xml" in parts:
        core = E.fromstring(parts["docProps/core.xml"])
        for name in ("created","modified"):
            ns = "{http://purl.org/dc/terms/}"
            node = core.find(ns+name)
            if node is not None:
                node.text = now
        parts["docProps/core.xml"] = E.tostring(core, xml_declaration=True, encoding="UTF-8", standalone=True)
    if "docProps/app.xml" in parts:
        app = E.fromstring(parts["docProps/app.xml"])
        for el in list(app):
            if E.QName(el).localname in {"Pages","Words","Characters","CharactersWithSpaces","TotalTime"}:
                app.remove(el)
        parts["docProps/app.xml"] = E.tostring(app, xml_declaration=True, encoding="UTF-8", standalone=True)
    parts["word/document.xml"] = E.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
    depth, begins = 0, 0
    for el in tree.findall(".//w:fldChar",NS):
        kind = el.get(W+"fldCharType")
        if kind == "begin":
            depth += 1
            begins += 1
        elif kind == "end":
            depth -= 1
            assert depth >= 0
        elif kind == "separate":
            assert depth > 0
    assert depth == 0
    for relation in rels:
        if relation.get("TargetMode") != "External":
            assert resolve_part(rels_name,relation.get("Target","")) in parts
    destination.parent.mkdir(exist_ok=True,parents=True)
    with zipfile.ZipFile(destination,"w",zipfile.ZIP_DEFLATED) as z:
        for name,data in parts.items():
            z.writestr(name,data)
    with zipfile.ZipFile(destination) as z:
        assert z.testzip() is None
    changed = sorted(n for n in parts if original.get(n) != parts[n])
    retained_instr = tree.xpath(".//w:instrText/text()",namespaces=NS)
    return dict(source=str(source),source_sha256=sha(source),document=destination.name,docx_sha256=sha(destination),
        changed_parts=changed,removed_parts=sorted(set(original)-set(parts)),removed_orphan_note_ids=removed_notes,
        removed_orphan_media=removed_media,removed_image_relationships=removed_relationships,
        retained_complex_citation_fields=begins,retained_instruction_fragments=len(retained_instr),
        retained_footnotes=len(tree.findall(".//w:footnoteReference",NS)),
        changes=changes,stage="DOCX_BUILT",native_export="PENDING",visual_review="PENDING",
        Zotero_global_library="UNCHANGED",Zotero_native_refresh="NOT_PERFORMED")
