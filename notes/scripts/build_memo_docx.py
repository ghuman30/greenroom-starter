"""
Build a professionally-formatted .docx of MEMO_v4.md, with the diagram
embedded inline. Output: notes/Greenroom_Case_Memo.docx

The .docx is designed to upload-and-open cleanly in Google Docs:
  1. Drag the .docx into Google Drive (or File -> Upload in Drive)
  2. Right-click the uploaded file -> Open with -> Google Docs
  3. Drive converts on the fly; formatting (headings, tables, image,
     code spans) survives the conversion.

Run:
  python -X utf8 notes/scripts/build_memo_docx.py
"""
import re
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = Path(__file__).resolve().parents[2]
MEMO = ROOT / "notes" / "MEMO_v4.md"
DIAGRAM = ROOT / "notes" / "memo-diagram.png"
OUT = ROOT / "notes" / "Greenroom_Case_Memo.docx"

# --------- color palette ----------------------------------------------------
INK = RGBColor(0x1F, 0x29, 0x37)       # near-black slate
INK_SOFT = RGBColor(0x6B, 0x72, 0x80)  # subtle gray
BRAND = RGBColor(0x0F, 0x76, 0x6E)     # teal-700 — Greenroom-ish
ROSE = RGBColor(0xBE, 0x12, 0x3C)
AMBER = RGBColor(0xB4, 0x53, 0x09)
CODE_BG = "F3F4F6"  # light gray for shading
TABLE_HEADER_BG = "F0FDF4"  # very light teal for header rows
TABLE_BORDER = "D1D5DB"  # neutral gray-300

# --------- helpers ----------------------------------------------------------
def set_cell_bg(cell, color_hex):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex)
    tcPr.append(shd)

def set_cell_border(cell, color_hex=TABLE_BORDER, size="4"):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{edge}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), size)
        b.set(qn("w:color"), color_hex)
        tcBorders.append(b)
    tcPr.append(tcBorders)

def add_horizontal_rule(doc):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "D1D5DB")
    pBdr.append(bottom)
    pPr.append(pBdr)

# --------- inline parser (bold, italic, code) -------------------------------
# Matches **bold**, *italic*, `code`. Tokens preserve text between them.
INLINE_RE = re.compile(
    r"(\*\*[^*]+?\*\*|\*[^*]+?\*|`[^`]+?`)"
)

def add_inline(paragraph, text, *, base_color=INK, base_size=10.5,
               base_name="Calibri"):
    """Add a text string to a paragraph with **bold**/*italic*/`code` support."""
    parts = INLINE_RE.split(text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
            run.font.size = Pt(base_size)
            run.font.color.rgb = base_color
            run.font.name = base_name
        elif part.startswith("*") and part.endswith("*"):
            run = paragraph.add_run(part[1:-1])
            run.italic = True
            run.font.size = Pt(base_size)
            run.font.color.rgb = base_color
            run.font.name = base_name
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.size = Pt(base_size - 0.5)
            run.font.name = "Consolas"
            run.font.color.rgb = INK
            # Shading
            r = run._r
            rPr = r.get_or_add_rPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), CODE_BG)
            rPr.append(shd)
        else:
            run = paragraph.add_run(part)
            run.font.size = Pt(base_size)
            run.font.color.rgb = base_color
            run.font.name = base_name

# --------- table builder ----------------------------------------------------
def add_table_from_markdown(doc, header_cells, body_rows):
    table = doc.add_table(rows=1 + len(body_rows), cols=len(header_cells))
    table.alignment = WD_ALIGN_PARAGRAPH.LEFT
    # Header
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(header_cells):
        set_cell_bg(hdr_cells[i], TABLE_HEADER_BG)
        set_cell_border(hdr_cells[i])
        para = hdr_cells[i].paragraphs[0]
        run = para.add_run(h)
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = BRAND
        run.font.name = "Calibri"
    # Body
    for r, row in enumerate(body_rows, start=1):
        for c, cell_text in enumerate(row):
            cell = table.rows[r].cells[c]
            set_cell_border(cell)
            para = cell.paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.space_before = Pt(0)
            add_inline(para, cell_text, base_size=9.5)
    return table

# --------- markdown parser (just enough) ------------------------------------
def parse_markdown(md_path):
    """
    Returns a list of (kind, payload) tuples:
      ('h1', 'Settlement at The Crescent')
      ('h2', 'What's actually broken')
      ('h3', '...')
      ('para', 'Mariana, lead booker...')
      ('bullet', 'Pulling expenses...')
      ('numbered', '1. ...')
      ('table', {'header': [...], 'rows': [[...], [...]]})
      ('hr',)
      ('image_placeholder',)
      ('subtitle', '...')   - paragraph immediately after H1
    """
    text = md_path.read_text(encoding="utf-8")
    lines = text.split("\n")
    out = []
    i = 0
    saw_h1 = False
    while i < len(lines):
        line = lines[i].rstrip()

        # Horizontal rule
        if line == "---":
            out.append(("hr",))
            i += 1
            continue

        # Headings
        if line.startswith("# "):
            out.append(("h1", line[2:].strip()))
            saw_h1 = True
            i += 1
            continue
        if line.startswith("## "):
            out.append(("h2", line[3:].strip()))
            i += 1
            continue
        if line.startswith("### "):
            out.append(("h3", line[4:].strip()))
            i += 1
            continue

        # Subtitle: bold lines right after H1 (the **Slice 1 ... + ...** line)
        if saw_h1 and line.startswith("**") and not out[-1][0] == "subtitle":
            # treat first 2 bold-only lines as subtitle
            if "**Slice 1" in line or "**Slice 2" in line or "Arshdeep" in line:
                out.append(("subtitle", line.strip("*").strip()))
                i += 1
                continue

        # Tables (markdown table with header line + separator)
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1].strip()):
            header = [c.strip() for c in line.strip("|").split("|")]
            i += 2  # skip separator
            rows = []
            while i < len(lines) and lines[i].rstrip().startswith("|"):
                row = [c.strip() for c in lines[i].rstrip().strip("|").split("|")]
                rows.append(row)
                i += 1
            out.append(("table", {"header": header, "rows": rows}))
            continue

        # Bullets
        if re.match(r"^-\s+", line):
            out.append(("bullet", re.sub(r"^-\s+", "", line)))
            i += 1
            continue

        # Numbered list
        m = re.match(r"^(\d+)\.\s+(.*)", line)
        if m:
            out.append(("numbered", m.group(2)))
            i += 1
            continue

        # Image reference placeholder
        if "memo-diagram.excalidraw" in line:
            # The "See diagram:" line — replace inline with our PNG image
            out.append(("image_placeholder",))
            i += 1
            continue

        # Blank line
        if not line.strip():
            i += 1
            continue

        # Default: paragraph (collect contiguous non-empty non-special lines)
        para_lines = [line]
        i += 1
        while i < len(lines):
            nxt = lines[i].rstrip()
            if (not nxt.strip()
                or nxt.startswith("#")
                or nxt.startswith("|")
                or nxt.startswith("---")
                or re.match(r"^-\s+", nxt)
                or re.match(r"^\d+\.\s+", nxt)):
                break
            para_lines.append(nxt)
            i += 1
        out.append(("para", " ".join(para_lines)))

    return out

# --------- document writer --------------------------------------------------
def build_doc():
    doc = Document()

    # Page setup: tight margins so 2-3 pages look right
    for section in doc.sections:
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)

    # Default body style
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)
    style.font.color.rgb = INK

    tokens = parse_markdown(MEMO)
    for kind, *payload in tokens:
        if kind == "h1":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(payload[0])
            r.bold = True
            r.font.size = Pt(22)
            r.font.color.rgb = INK
            r.font.name = "Calibri"

        elif kind == "subtitle":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            add_inline(p, payload[0], base_color=INK_SOFT, base_size=11)

        elif kind == "h2":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(4)
            r = p.add_run(payload[0])
            r.bold = True
            r.font.size = Pt(14)
            r.font.color.rgb = BRAND
            r.font.name = "Calibri"

        elif kind == "h3":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(payload[0])
            r.bold = True
            r.font.size = Pt(11.5)
            r.font.color.rgb = INK
            r.font.name = "Calibri"

        elif kind == "para":
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(6)
            add_inline(p, payload[0])

        elif kind == "bullet":
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(2)
            add_inline(p, payload[0])

        elif kind == "numbered":
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.space_after = Pt(2)
            add_inline(p, payload[0])

        elif kind == "table":
            t = payload[0]
            add_table_from_markdown(doc, t["header"], t["rows"])
            # spacing after table
            doc.add_paragraph().paragraph_format.space_after = Pt(2)

        elif kind == "hr":
            add_horizontal_rule(doc)

        elif kind == "image_placeholder":
            # Insert the diagram inline, centered, sized to page width
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run()
            run.add_picture(str(DIAGRAM), width=Inches(6.5))
            # Caption below
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap_run = cap.add_run(
                "Figure 1 · The deal flow today (top) vs. with the slice (bottom). "
                "Source: notes/memo-diagram.excalidraw"
            )
            cap_run.italic = True
            cap_run.font.size = Pt(9)
            cap_run.font.color.rgb = INK_SOFT

    doc.save(OUT)
    return OUT

if __name__ == "__main__":
    out = build_doc()
    print(f"Wrote {out}")
    print(f"Size: {out.stat().st_size:,} bytes")
