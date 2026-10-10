"""逐表逐格核对DOCX及原生PDF；保存页面图与可读Markdown，视觉检查另记。"""
from pathlib import Path, PurePosixPath
from collections import Counter
from datetime import datetime, timezone
from lxml import etree as E
import argparse
import hashlib
import json
import posixpath
import re
import unicodedata
import zipfile
import fitz
from PIL import Image, ImageDraw

ROOT = Path("C:/Users/LZHS/pp_lgcm_review/round2D_20261008")
NS = {"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = "{"+NS["w"]+"}"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def norm(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC",str(value or ""))).replace("−","-").replace("–","-").replace("\u200b","")

def text(node):
    return "".join(node.xpath(".//w:t/text()",namespaces=NS))

def citations(tree):
    code = "".join(tree.xpath(".//w:instrText/text()",namespaces=NS))
    items = []
    for m in re.finditer(r"ADDIN\s+ZOTERO_ITEM\s+CSL_CITATION\s*",code):
        value,_ = json.JSONDecoder().raw_decode(code[m.end():].lstrip())
        items.append(json.dumps(value,sort_keys=True,ensure_ascii=False))
    return Counter(items)

def xml_rows(table):
    return [[text(cell) for cell in row.findall("w:tc",NS)] for row in table.findall("w:tr",NS)]

def readable_markdown(tree, preview):
    out = ["排版预览；模型分析尚在进行。" if preview else "阶段稿，与同版DOCX对应；原研究计划尚未全部执行，表格可通过原始结果CSV复核。", ""]
    for node in tree.find("w:body",NS):
        if node.tag == W+"p":
            value = text(node)
            if value:
                style = node.find("w:pPr/w:pStyle",NS)
                sid = style.get(W+"val","") if style is not None else ""
                out.extend([("## " if sid in {"affe","afff0","af3"} else "")+value, ""])
        elif node.tag == W+"tbl":
            rows = xml_rows(node)
            for k,row in enumerate(rows):
                out.append("| "+" | ".join(s.replace("|","\\|").replace("\n","<br>") for s in row)+" |")
                if k == 0:
                    out.append("| "+" | ".join("---" for _ in row)+" |")
            out.append("")
    return "\n".join(out)

def validate_pdf_tables(pdf, expected, label):
    actual, images = [], []
    document = fitz.open(pdf)
    for index,page in enumerate(document):
        found = page.find_tables(strategy="lines_strict")
        for t in found.tables:
            if t.col_count < 2:
                continue
            actual.append(dict(page=index+1,bbox=list(t.bbox),rows=t.extract()))
        images.append(dict(page=index+1,width=page.rect.width,height=page.rect.height,
                           extracted_text_characters=len(page.get_text()),tables=len(found.tables)))
    # 每个PDF行必须按顺序对应同一表的表头或数据行；跨页重复表头单独跳过。
    table_index,row_index = 0,0
    matched,errors = [],[]
    want = [[t["headers"]]+t["rows"] for t in expected]
    for fragment_index,fragment in enumerate(actual):
        for pdf_row_index,row in enumerate(fragment["rows"]):
            nr = [norm(v) for v in row]
            if not any(nr):
                continue
            if table_index >= len(want):
                errors.append(dict(kind="UNEXPECTED_PDF_TABLE_ROW",page=fragment["page"],actual=row))
                continue
            current = want[table_index]
            if row_index and nr == [norm(v) for v in current[0]]:
                continue
            target = current[row_index]
            if nr != [norm(v) for v in target]:
                errors.append(dict(kind="PDF_CELL_ROW_MISMATCH",document=label,title=expected[table_index]["title"],
                    page=fragment["page"],fragment=fragment_index,pdf_row=pdf_row_index,expected_row=row_index,
                    expected=target,actual=row))
                # 保留明确失败位置，不以全文搜索补齐。
                return dict(passed=False,errors=errors,matched_rows=matched,actual_tables=actual,pages=images)
            matched.append(dict(title=expected[table_index]["title"],row=row_index,page=fragment["page"],cells=len(row)))
            row_index += 1
            if row_index == len(current):
                table_index += 1
                row_index = 0
    if table_index != len(want) or row_index:
        errors.append(dict(kind="MISSING_PDF_TABLE_ROWS",completed_tables=table_index,expected_tables=len(want),next_row=row_index))
    return dict(passed=not errors,errors=errors,matched_rows=matched,actual_tables=actual,pages=images)

def render(document, destination, label):
    destination.mkdir(exist_ok=True,parents=True)
    doc = fitz.open(document)
    pages = []
    for i,page in enumerate(doc):
        target = destination/f"{label}_p{i+1:03d}.png"
        page.get_pixmap(matrix=fitz.Matrix(1.15,1.15),alpha=False).save(target)
        pages.append(target)
    sheets = []
    for start in range(0,len(pages),6):
        thumbs = []
        for j,path in enumerate(pages[start:start+6],start=start+1):
            im = Image.open(path).convert("RGB")
            im.thumbnail((420,600))
            canvas = Image.new("RGB",(440,630),"#dddddd")
            canvas.paste(im,((440-im.width)//2,22))
            ImageDraw.Draw(canvas).text((10,4),f"{label}: page {j}",fill="black")
            thumbs.append(canvas)
        sheet = Image.new("RGB",(440*3,630*2),"white")
        for j,im in enumerate(thumbs):
            sheet.paste(im,((j%3)*440,(j//3)*630))
        target = destination/f"{label}_contact_{start+1:03d}.png"
        sheet.save(target)
        sheets.append(target.name)
    return dict(page_images=[p.name for p in pages],contact_sheets=sheets)
