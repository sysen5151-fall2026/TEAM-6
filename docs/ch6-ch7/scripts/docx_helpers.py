"""python-docx helpers for the report build."""
import re
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

NAVY = RGBColor(0x1F, 0x3A, 0x5F)


def new_document():
    d = Document()
    st = d.styles
    st["Normal"].font.name = "Calibri"
    st["Normal"].font.size = Pt(11)
    st["Normal"].element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    st["Normal"].paragraph_format.space_after = Pt(6)
    st["Normal"].paragraph_format.line_spacing = 1.08
    sizes = {1: 16, 2: 13, 3: 11.5, 4: 11, 5: 10.5}
    for lvl, sz in sizes.items():
        h = st[f"Heading {lvl}"]
        h.font.name = "Calibri"
        h.element.rPr.rFonts.set(qn("w:asciiTheme"), "minorHAnsi") if False else None
        h.font.size = Pt(sz)
        h.font.bold = True
        h.font.italic = False
        h.font.color.rgb = NAVY
        h.paragraph_format.space_before = Pt(14 if lvl == 1 else 10)
        h.paragraph_format.space_after = Pt(4)
        h.paragraph_format.keep_with_next = True
        rf = h.element.rPr.rFonts
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if rf.get(qn(a)) is not None:
                del rf.attrib[qn(a)]
        rf.set(qn("w:ascii"), "Calibri")
        rf.set(qn("w:hAnsi"), "Calibri")
    cap = st["Caption"]
    cap.font.name = "Calibri"
    cap.font.size = Pt(9.5)
    cap.font.bold = True
    cap.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    cap.paragraph_format.space_after = Pt(8)
    sec = d.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    for a in ("left_margin", "right_margin"):
        setattr(sec, a, Inches(0.7))
    sec.top_margin = Inches(0.9)
    sec.bottom_margin = Inches(0.8)
    return d


def _runs(p, text, size=None, color=None, bold=None, italic=None):
    """**bold** and _italic_ light markup."""
    parts = re.split(r"(\*\*.+?\*\*)", text)
    for part in parts:
        if not part:
            continue
        b = part.startswith("**") and part.endswith("**")
        r = p.add_run(part[2:-2] if b else part)
        if b or bold:
            r.bold = True
        if italic:
            r.italic = True
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color
    return p


def para(d, text, size=None, align=None, italic=False, after=None, keep=False):
    p = d.add_paragraph()
    _runs(p, text, size=size, italic=italic)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if keep:
        p.paragraph_format.keep_with_next = True
    return p


def bullet(d, text, size=None):
    p = d.add_paragraph(style="List Bullet")
    _runs(p, text, size=size)
    p.paragraph_format.space_after = Pt(3)
    return p


def heading(d, text, level):
    return d.add_heading(text, level=level)


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), fill)
    tcPr.append(sh)


def set_cell(cell, text, size=8.5, bold=False, color=None, align=None):
    cell.text = ""
    lines = str(text).split("\n")
    for k, line in enumerate(lines):
        p = cell.paragraphs[0] if k == 0 else cell.add_paragraph()
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        _runs(p, line, size=size, color=color, bold=bold)
        if align == "center":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def table(d, header, rows, widths, size=8.5, first_bold=False, hdr_fill="1F3A5F", zebra=True):
    t = d.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        set_cell(c, h, size=size, bold=True, color=RGBColor(255, 255, 255))
        shade(c, hdr_fill)
    # repeat header row
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trPr.append(th)
    for r_i, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            set_cell(cells[i], v, size=size, bold=(first_bold and i == 0))
            if zebra and r_i % 2 == 1:
                shade(cells[i], "F3F6FA")
        trPr = t.rows[-1]._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        cs.set(qn("w:val"), "true")
        trPr.append(cs)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Inches(w)
    d.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def caption(d, text, keep_prev=False):
    p = d.add_paragraph(style="Caption")
    _runs(p, text)
    return p


def picture(d, path, width):
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(path, width=Inches(width))
    return p


def new_section(d, landscape):
    sec = d.add_section(WD_SECTION.NEW_PAGE)
    if landscape:
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = Inches(11), Inches(8.5)
        sec.left_margin = sec.right_margin = Inches(0.6)
        sec.top_margin = Inches(0.7)
        sec.bottom_margin = Inches(0.6)
    else:
        sec.orientation = WD_ORIENT.PORTRAIT
        sec.page_width, sec.page_height = Inches(8.5), Inches(11)
        sec.left_margin = sec.right_margin = Inches(0.7)
        sec.top_margin = Inches(0.9)
        sec.bottom_margin = Inches(0.8)
    return sec


def add_field(par, instr, placeholder=""):
    r = par.add_run()
    f1 = OxmlElement("w:fldChar")
    f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    f2 = OxmlElement("w:fldChar")
    f2.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t")
    t.text = placeholder
    f3 = OxmlElement("w:fldChar")
    f3.set(qn("w:fldCharType"), "end")
    for el in (f1, it, f2, t, f3):
        r._r.append(el)


def header_footer(d, header_text):
    for sec in d.sections:
        sec.header.is_linked_to_previous = False
        sec.footer.is_linked_to_previous = False
        hp = sec.header.paragraphs[0]
        hp.text = ""
        r = hp.add_run(header_text)
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        fp = sec.footer.paragraphs[0]
        fp.text = ""
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run("Page ")
        r.font.size = Pt(8.5)
        add_field(fp, "PAGE", "1")
        for run in fp.runs:
            run.font.size = Pt(8.5)
