"""
Convert notes/Greenroom_Case_Memo.docx -> notes/memo_final.md.

User edited the .docx after I generated it from MEMO_v4.md. This pulls
the edits back into markdown so we have a canonical source again.

Walks doc.element.body in document order (preserves paragraph/table
interleaving), maps font-size + style → markdown heading levels, and
recovers run-level bold / italic / code formatting.

Run:
  python -X utf8 notes/scripts/docx_to_md.py
"""
import re
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[2]
IN = ROOT / "notes" / "Greenroom_Case_Memo.docx"
OUT = ROOT / "notes" / "memo_final.md"

doc = Document(str(IN))


def classify_para(p) -> str:
    """Return 'h1' | 'h2' | 'h3' | 'bullet' | 'numbered' | 'body' | 'blank'."""
    # Empty paragraph
    txt = p.text.strip()
    if not txt:
        return "blank"
    style_name = (p.style.name or "").lower() if p.style else ""
    if "bullet" in style_name:
        return "bullet"
    if "number" in style_name:
        return "numbered"
    # Heading detection via leading run font size (we built docx with
    # explicit Pt sizes per heading level: 22 / 14 / 11.5)
    runs = [r for r in p.runs if r.text]
    if not runs:
        return "body"
    first = runs[0]
    size = first.font.size.pt if first.font.size else None
    if size and size >= 18:
        return "h1"
    if size and 13 <= size <= 16:
        return "h2"
    if size and 11 <= size <= 12.5 and first.bold:
        return "h3"
    return "body"


def render_runs(p) -> str:
    """Render paragraph runs back to markdown with **bold** / *italic* / `code`."""
    out = []
    for r in p.runs:
        text = r.text
        if not text:
            continue
        # Code detection: we used Consolas + gray shading
        is_code = r.font.name == "Consolas"
        if is_code:
            out.append(f"`{text}`")
        elif r.bold and r.italic:
            out.append(f"***{text}***")
        elif r.bold:
            out.append(f"**{text}**")
        elif r.italic:
            out.append(f"*{text}*")
        else:
            out.append(text)
    return "".join(out)


def render_paragraph(p, kind: str) -> str | None:
    body = render_runs(p)
    if not body.strip():
        return ""
    if kind == "h1":
        return f"# {body.strip()}"
    if kind == "h2":
        return f"## {body.strip()}"
    if kind == "h3":
        return f"### {body.strip()}"
    if kind == "bullet":
        return f"- {body.strip()}"
    if kind == "numbered":
        return f"1. {body.strip()}"
    # body paragraph
    return body.strip()


def render_table(tbl) -> str:
    """Render a python-docx Table as a markdown table."""
    rows = tbl.rows
    if not rows:
        return ""
    headers = [render_runs_in_cell(c) for c in rows[0].cells]
    md_lines = ["| " + " | ".join(headers) + " |"]
    md_lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows[1:]:
        cells = [render_runs_in_cell(c) for c in row.cells]
        md_lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(md_lines)


def render_runs_in_cell(cell) -> str:
    """Cell may have multiple paragraphs; concat with <br>."""
    parts = []
    for p in cell.paragraphs:
        line = render_runs(p)
        if line.strip():
            parts.append(line.strip())
    # Collapse pipes (would break the markdown table); they're rare here
    text = " <br> ".join(parts).replace("|", "\\|")
    return text or " "


# --------- Walk body in order ----------
body = doc.element.body
md_chunks: list[str] = []
last_kind: str | None = None
for child in body.iterchildren():
    tag = child.tag
    if tag == qn("w:p"):
        # Build a Paragraph from the XML element. python-docx makes this clunky;
        # find the matching paragraph by index.
        # Easier: use the iter_paragraphs approach via doc.paragraphs and a
        # parallel counter — but that loses interleaving. Workaround: use
        # `paragraph._p is child` matching.
        # Cheapest: import Paragraph constructor.
        from docx.text.paragraph import Paragraph
        p = Paragraph(child, doc)
        kind = classify_para(p)
        if kind == "blank":
            if last_kind not in (None, "blank"):
                md_chunks.append("")  # one blank line separator
                last_kind = "blank"
            continue
        rendered = render_paragraph(p, kind)
        if rendered is None:
            continue
        # Add a blank line before block-level things
        if md_chunks and last_kind != "blank" and kind in ("h1", "h2", "h3"):
            md_chunks.append("")
        md_chunks.append(rendered)
        last_kind = kind
    elif tag == qn("w:tbl"):
        from docx.table import Table
        tbl = Table(child, doc)
        if last_kind not in (None, "blank"):
            md_chunks.append("")
        md_chunks.append(render_table(tbl))
        md_chunks.append("")
        last_kind = "table"
    # ignore section properties etc.

# --------- Detect image placeholders ----------
# When we hit an inline image in a paragraph, render_runs() drops it
# (no .text). We surface a placeholder so the reader knows to look at
# the PNG. Detection: find paragraphs that contain a <w:drawing>.
def paragraph_has_image(p_xml) -> bool:
    return p_xml.find(".//" + qn("w:drawing")) is not None

# Post-process: walk again, find image paragraphs, insert placeholder
final_md = "\n".join(md_chunks)

# Crude: look for the image position by recognizing the surrounding
# captioning. The original docx places the image between "See diagram:"
# and "Figure 1 ·" caption. Insert a markdown image reference there.
final_md = re.sub(
    r"(See diagram: `notes/memo-diagram\.excalidraw`.*?\n)",
    r"\1\n![Before vs After deal flow](memo-diagram.png)\n",
    final_md,
    flags=re.DOTALL,
)

# Fallback: if "Figure 1" caption exists but no image ref above it, insert
if "memo-diagram.png" not in final_md and "Figure 1" in final_md:
    final_md = final_md.replace(
        "Figure 1",
        "![Before vs After deal flow](memo-diagram.png)\n\n*Figure 1",
        1,
    )

# --------- Cosmetic cleanup pass ----------
# Headings come out as "## **Title**" because we bolded the run; ## already
# conveys heading weight in markdown so strip the inner **.
final_md = re.sub(r"^(#{1,6})\s*\*\*(.+?)\*\*\s*$", r"\1 \2", final_md, flags=re.MULTILINE)

# Image placeholder artifact: "*![alt](png)" → "![alt](png)" (regex above left a
# leading star from the surrounding *Figure 1* italic split)
final_md = re.sub(r"\n\*(!\[)", r"\n\1", final_md)

# Fragmented bold runs from Word style boundaries: ****X**** → **X**,
# ***X*** → ***X*** (preserve bold-italic), but collapse degenerate ****
final_md = re.sub(r"\*{4,}", "**", final_md)

# Sometimes paragraphs ended with "**word ****" (Word splits bold + space).
# Collapse "** **" inside the same line.
final_md = re.sub(r"\*\* \*\*", " ", final_md)

# Figure caption trailing asterisk: "*Figure 1 · ... *" → "*Figure 1 · ...*"
final_md = re.sub(r"\*(Figure[^*]+) \*", r"*\1*", final_md)

# Collapse 3+ blank lines to 2
final_md = re.sub(r"\n{3,}", "\n\n", final_md)
final_md = final_md.strip() + "\n"

OUT.write_text(final_md, encoding="utf-8")
print(f"Wrote {OUT}  ({len(final_md):,} chars, {final_md.count(chr(10)):,} lines)")
