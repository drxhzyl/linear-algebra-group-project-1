#!/usr/bin/env python3
"""Export the current illustrated deck as compact A4 sheets, with writing cards."""

from collections import Counter
from io import BytesIO
import json
from pathlib import Path
import re
import sys
from xml.sax.saxutils import escape

from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

# Optional local dependency installation; bundled ReportLab remains in use.
sys.path.insert(0, str(Path.home() / ".cache/gametrix-pdf-deps"))
from svglib.svglib import svg2rlg

import card_art as art
from card_layout import OP_COPY, OBJECTIVE_COPY, KEY_TERMS

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output/pdf"
AUDIT = ROOT / "tmp/pdfs"
DECK = ROOT / "expansion_split/generated/deck.json"
BLANK_COUNTS = {"blue": 120, "red": 60}
W, H = A4
CW, CH, GAP = 63 * mm, 67 * mm, 2 * mm
LEFT, BOTTOM = (W - 3 * CW - 2 * GAP) / 2, (H - 4 * CH - 3 * GAP) / 2
INK, MUTED = HexColor("#182332"), HexColor("#637085")
COLORS = {"blue": "#245cff", "red": "#ef493c", "operation": "#edb600", "objective": "#009c73"}
NAMES = {"blue": "BLUE MATRIX", "red": "RED MATRIX", "operation": "OPERATION", "objective": "OBJECTIVE"}
FONTS = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pdfjs-dist/standard_fonts"
pdfmetrics.registerFont(TTFont("Card", str(FONTS / "LiberationSans-Regular.ttf")))
pdfmetrics.registerFont(TTFont("CardBold", str(FONTS / "LiberationSans-Bold.ttf")))
pdfmetrics.registerFontFamily("Card", normal="Card", bold="CardBold")
CACHE = art.load_cache()
DRAWINGS = {}
LAYOUT = []


def highlighted(text, kind):
    pattern = re.compile("|".join(re.escape(k) for k in sorted(KEY_TERMS, key=len, reverse=True)), re.I)
    result, end = [], 0
    color = "#087969" if kind == "objective" else "#6834a5"
    for match in pattern.finditer(text):
        result.append(escape(text[end:match.start()]))
        result.append(f'<b><font color="{color}">{escape(match.group())}</font></b>')
        end = match.end()
    result.append(escape(text[end:]))
    return "".join(result)


def paragraph(c, text, x, top, width, size=7.6, leading=9.4, bold=False, color=INK, limit=None):
    style = ParagraphStyle("card", fontName="CardBold" if bold else "Card", fontSize=size,
                           leading=leading, textColor=color, spaceBefore=0, spaceAfter=0)
    p = Paragraph(text, style)
    _, height = p.wrap(width, 1000)
    if limit is not None and height > limit + .01:
        raise ValueError(f"Text exceeds its box: {text!r}: {height:.2f} > {limit:.2f}")
    p.drawOn(c, x, top - height)
    return height


def drawing(c, source, x, y, width, height):
    key = art.source_key(source)
    if key not in DRAWINGS:
        d = svg2rlg(BytesIO(CACHE[key].encode()))
        if d is None or not d.width or not d.height:
            raise ValueError(f"Invalid diagram: {key}")
        DRAWINGS[key] = d
    d = DRAWINGS[key]
    scale = min(width / d.width, height / d.height)
    c.saveState()
    c.translate(x + (width - d.width * scale) / 2, y + (height - d.height * scale) / 2)
    c.scale(scale, scale)
    renderPDF.draw(d, c, 0, 0)
    c.restoreState()


def card(c, kind, record, x, y, page):
    blank = record.get("blank", False)
    color = HexColor(COLORS[kind])
    c.setFillColor(white)
    c.setStrokeColor(HexColor("#aeb8c4"))
    c.setLineWidth(.45)
    c.roundRect(x, y, CW, CH, 2.4 * mm, fill=1, stroke=1)
    c.setFillColor(color)
    c.roundRect(x + .15 * mm, y + CH - 1.5 * mm, CW - .3 * mm, 1.35 * mm, .65 * mm, fill=1, stroke=0)
    pad = 3 * mm
    tx, tw = x + pad, CW - 2 * pad
    c.setFillColor(INK)
    c.setFont("CardBold", 6.1)
    c.drawString(tx, y + CH - 5.7 * mm, NAMES[kind])
    c.setFillColor(MUTED)
    c.setFont("Card", 6.1)
    c.drawRightString(x + CW - pad, y + CH - 5.7 * mm, record["id"])
    title_top = y + CH - 8.3 * mm

    if kind == "operation":
        title, rule = OP_COPY[record["code"]]
        th = paragraph(c, escape(title), tx, title_top, tw, size=10.5, leading=11.2, bold=True, limit=8.5 * mm)
        rule_style = ParagraphStyle("measure", fontName="Card", fontSize=7.6, leading=9.4)
        rule_text = highlighted(rule, kind)
        rh = Paragraph(rule_text, rule_style).wrap(tw, 1000)[1]
        paragraph(c, rule_text, tx, y + 3 * mm + rh, tw, limit=21 * mm)
        art_y = y + 3 * mm + rh + 1.2 * mm
        art_top = title_top - th - 1 * mm
        if art_top - art_y < 19 * mm:
            raise ValueError(f"Diagram area too short for {record['id']}")
        drawing(c, art.operation_art(record["code"]), tx, art_y, tw, min(30 * mm, art_top - art_y))
    elif kind in ("blue", "red"):
        title = "Blank Matrix" if blank else "Starting Matrix" if kind == "blue" else "Matrix Card"
        paragraph(c, title, tx, title_top, tw, size=11, leading=12, bold=True)
        c.setFillColor(color)
        if blank:
            c.setFont("Card", 7.4)
            c.drawString(tx, y + CH - 19.6 * mm, "Rows ______   Columns ______")
        else:
            A = record["matrix"]
            c.setFont("CardBold", 11)
            c.drawString(tx, y + CH - 20 * mm, f"{len(A)} × {len(A[0])}")
            c.setFont("Card", 5.8)
            c.setFillColor(MUTED)
            c.drawString(tx + 15 * mm, y + CH - 19.7 * mm, "ROWS × COLUMNS")
        bx, by, bw, bh = tx, y + 3 * mm, tw, 40 * mm
        c.setStrokeColor(color)
        c.setLineWidth(.7)
        c.roundRect(bx, by, bw, bh, 1.8 * mm, fill=0, stroke=1)
        if not blank:
            drawing(c, art.matrix_art(record["matrix"]), bx + 5 * mm, by + 4 * mm, bw - 10 * mm, bh - 8 * mm)
    else:
        th = paragraph(c, escape(record["name"]), tx, title_top, tw, size=10.5, leading=11.2, bold=True, limit=8.5 * mm)
        shape_top = title_top - th - 1 * mm
        paragraph(c, escape(record["shape"].replace("–", "-")), tx, shape_top, tw, size=6.6, leading=7.4, bold=True, color=color)
        formula_top = shape_top - 3.6 * mm
        formula_height = (13 if record["id"] in ("C11", "C12", "C14") else 7.6) * mm
        drawing(c, art.objective_art(record), tx, formula_top - formula_height, tw, formula_height)
        rule_text = highlighted(OBJECTIVE_COPY[record["id"]], kind)
        style = ParagraphStyle("measure", fontName="Card", fontSize=7.4, leading=9.1)
        rh = Paragraph(rule_text, style).wrap(tw, 1000)[1]
        paragraph(c, rule_text, tx, y + 3 * mm + rh, tw, size=7.4, leading=9.1, limit=21 * mm)
        ey = y + 3 * mm + rh + 1.2 * mm
        et = formula_top - formula_height - 1 * mm
        eh = et - ey
        if eh < 13 * mm:
            raise ValueError(f"Example area too short for {record['id']}: {eh / mm:.1f} mm")
        c.setFillColor(HexColor("#f4f9f7"))
        c.roundRect(tx, ey, tw, eh, 1.5 * mm, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.setFont("Card", 5.4)
        c.drawString(tx + 2 * mm, et - 3 * mm, "EXAMPLE")
        drawing(c, art.matrix_art(record["A"]), tx + 7 * mm, ey + 1 * mm, tw - 14 * mm, eh - 4.5 * mm)
    LAYOUT.append({"page": page, "id": record["id"], "kind": kind, "blank": blank,
                   "bounds": [round(v, 3) for v in (x, y, x + CW, y + CH)]})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    AUDIT.mkdir(parents=True, exist_ok=True)
    deck = json.loads(DECK.read_text())
    records = [(kind, record) for kind, key in [("blue", "blue"), ("red", "red"),
                 ("operation", "operations"), ("objective", "objectives")] for record in deck[key]]
    sheets = [("Complete deck", records[i:i + 12]) for i in range(0, len(records), 12)]
    blank_starts = {}
    for color, count in BLANK_COUNTS.items():
        blank_starts[len(sheets) + 1] = f"Blank {color} cards"
        for start in range(1, count + 1, 12):
            sheets.append((f"Blank {color} cards - reprint this sheet as needed", [
                (color, {"id": f"{color[0].upper()}W{i:03}", "blank": True})
                for i in range(start, min(start + 12, count + 1))]))
    path = OUT / "GameTrix-complete-deck-with-blanks.pdf"
    c = canvas.Canvas(str(path), pagesize=A4, pageCompression=1)
    c.setTitle("GameTrix | Complete deck and blank matrix cards")
    c.setAuthor("GameTrix")
    c.setSubject("137 physical cards plus 120 blank blue and 60 blank red cards; 12 cards per A4 page.")
    for page, (section, items) in enumerate(sheets, 1):
        c.setFont("CardBold", 7.3)
        c.setFillColor(INK)
        c.drawString(LEFT, H - 6.1 * mm, "GameTrix")
        c.setFont("Card", 6.6)
        c.drawString(LEFT + 19 * mm, H - 6.1 * mm, section)
        c.drawRightString(W - LEFT, H - 6.1 * mm, f"{page:02} / {len(sheets):02}")
        for slot, (kind, record) in enumerate(items):
            row, col = divmod(slot, 3)
            x = LEFT + col * (CW + GAP)
            y = H - BOTTOM - CH - row * (CH + GAP)
            card(c, kind, record, x, y, page)
        bookmarks = {1: "Matrix cards", 4: "Operation cards", 11: "Objective cards", **blank_starts}
        if page in bookmarks:
            label = bookmarks[page]
            c.bookmarkPage(f"page{page}")
            c.addOutlineEntry(label, f"page{page}")
        c.setFillColor(MUTED)
        c.setFont("Card", 6)
        c.drawString(LEFT, 6.3 * mm, "A4 | Print at 100% / Actual Size | Cards: 63 × 67 mm | Cut along card borders")
        if page <= 12:
            c.drawString(LEFT, 3.4 * mm, "Any color pair may operate. Diagram colors label A, B and the result. Keep exact values; matrix dimensions: 2-4.")
        else:
            c.drawString(LEFT, 3.4 * mm, "Blank cards use the same dimensions as the rest of this compact deck.")
        c.showPage()
    c.save()
    assert len(records) == 137 and len(LAYOUT) == 137 + sum(BLANK_COUNTS.values())
    counts = Counter(x["kind"] for x in LAYOUT if not x["blank"])
    (AUDIT / "card-layout.json").write_text(json.dumps({"pdf": str(path), "pages": len(sheets),
        "cards": dict(counts), "blank_blue": BLANK_COUNTS["blue"], "blank_red": BLANK_COUNTS["red"], "layout": LAYOUT}, indent=2))
    print(json.dumps({"pdf": str(path), "pages": len(sheets), "cards": dict(counts), "blanks": BLANK_COUNTS}))


if __name__ == "__main__":
    main()
