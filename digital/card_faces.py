"""Printed-card faces, with local artwork and a raised treatment for Arcade.

Public API:
    draw_card(card, kind, x, y, w, h, *, scale=1, raised=False, selected=False,
              blank=False, highlights=None)
        x/y are bottom-left design coordinates. All geometry is multiplied by
        scale. The face occupies exactly w by h, with the shadow outside it.
        `raised` strengthens and offsets the shadow; the caller controls position.
        Matrix-only `blank` keeps brackets/dimensions but omits all values.
        `highlights` maps zero-based (row, col) to an RGBA tint.
    matrix_cell_rects(rows, cols, x, y, w, h) -> nested row-major rectangles
        Full cell bounds in bottom-left coordinates, with row 0 at the top.
        Pass scaled card bounds when matching a scaled draw_card call.
    matrix_cell_at(rows, cols, card_rect, px, py) -> (row, col) or None
    get_card_texture(card, kind, *, blank=False, highlights=None) -> arcade.Texture
        Transparent, rounded 630 × 880 face without shadow, usable in Sprites.
    render_card_image(card, kind, *, blank=False, highlights=None) -> PIL.Image
        Same face, useful for previews and other rendering contexts.

Kinds are operation, objective, blue, and red. Operations/objectives accept
deck dictionaries. Matrix cards accept MatrixCard objects or dictionaries with
`matrix` / `values` and `id`; entries may be int, Fraction, or fraction strings.
Artwork and fonts are local. No browser, network, LaTeX, or PDF tool is needed
at runtime. Face images, textures, fonts, artwork, and shadows are cached.
The 63:88 aspect ratio matches the full-height printed HTML cards.
Compact matrix faces abbreviate oversized values with an ellipsis after
reducing their font size; a separate inspector can show the complete values.
"""

from fractions import Fraction
from functools import lru_cache
from pathlib import Path
import re

import arcade
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from card_layout import OP_COPY, OBJECTIVE_COPY, KEY_TERMS

ASSETS = Path(__file__).resolve().parent / "assets"
WIDTH, HEIGHT = 630, 880
INK = "#182332"
MUTED = "#637085"
COLORS = {"operation": "#ffc400", "objective": "#009c73", "blue": "#245cff", "red": "#ef493c"}
TINTS = {"operation": (255, 252, 240), "objective": (237, 251, 245), "blue": (240, 244, 255), "red": (255, 241, 239)}
NAMES = {"operation": "OPERATION", "objective": "OBJECTIVE", "blue": "BLUE MATRIX", "red": "RED MATRIX"}
MATRIX_BOX = (57, 295, 516, 520)
_TERM = re.compile("|".join(re.escape(k) for k in sorted(KEY_TERMS, key=len, reverse=True)), re.I)


@lru_cache(maxsize=90)
def _font(size, bold=False):
    return ImageFont.truetype(str(ASSETS / ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf")), size)


@lru_cache(maxsize=64)
def _art(name):
    with Image.open(ASSETS / (name + ".png")) as source:
        return source.convert("RGBA")


def _paste_art(face, name, box):
    image = _art(name)
    left, top, width, height = box
    factor = min(width / image.width, height / image.height)
    target = image.resize((max(1, round(image.width * factor)), max(1, round(image.height * factor))), Image.Resampling.LANCZOS)
    face.alpha_composite(target, (round(left + (width - target.width) / 2), round(top + (height - target.height) / 2)))


def _text(draw, text, x, y, width, size, *, bold=False, color=INK, leading=None):
    """Wrap text by measured width, returning its lower edge."""
    font = _font(size, bold)
    leading = leading or round(size * 1.15)
    words, lines, line = text.split(), [], ""
    for word in words:
        test = (line + " " + word).strip()
        if line and draw.textlength(test, font=font) > width:
            lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    for line in lines:
        draw.text((x, y), line, font=font, fill=color, anchor="lt")
        y += leading
    return y


def _rule(draw, text, y, kind, bottom=843):
    # Preserve the print design's highlighted mathematical conditions.
    emphasized = [(m.start(), m.end()) for m in _TERM.finditer(text)]
    tokens = [(m.group(), any(a < m.end() and b > m.start() for a, b in emphasized))
              for m in re.finditer(r"\S+", text)]
    for size in range(23, 18, -1):
        lines, line, used = [], [], 0
        for word, bold in tokens:
            width = draw.textlength(word + " ", font=_font(size, bold))
            if line and used + width > 558:
                lines.append(line)
                line, used = [], 0
            line.append((word, bold, width))
            used += width
        if line:
            lines.append(line)
        if y + len(lines) * round(size * 1.35) <= bottom:
            break
    accent = "#087969" if kind == "objective" else "#6834a5"
    for line in lines:
        x = 36
        for word, bold, width in line:
            draw.text((x, y), word, font=_font(size, bold), fill=accent if bold else "#344154", anchor="lt")
            x += width
        y += round(size * 1.35)


def _matrix_key(values, blank):
    # Blank faces depend only on dimensions, never on the hidden entries.
    if blank:
        return tuple(tuple(None for _ in row) for row in values), True
    return tuple(tuple(str(Fraction(v)) for v in row) for row in values), False


def _record_key(card, kind, *, blank=False):
    if kind not in COLORS:
        raise ValueError(f"Unknown card kind: {kind}")
    if isinstance(card, dict):
        cid = str(card.get("id", ""))
        if kind in ("blue", "red"):
            values = card.get("matrix", card.get("values"))
            return kind, cid, *_matrix_key(values, blank)
        if kind == "operation":
            return kind, cid, card["code"]
        return kind, cid, card["name"], card["shape"]
    if kind not in ("blue", "red"):
        raise TypeError("Operation and objective cards must be deck dictionaries")
    return kind, str(card.id), *_matrix_key(card.values, blank)


def _ellipsize(draw, text, font, width):
    """Keep even very large exact values inside their allotted matrix cell."""
    if draw.textlength(text, font=font) <= width:
        return text
    while text and draw.textlength(text + "…", font=font) > width:
        text = text[:-1]
    return text + "…"


def _matrix_geometry(rows, cols, box=MATRIX_BOX):
    """Shared print-space geometry; PIL uses top-left coordinates."""
    if rows < 1 or cols < 1:
        raise ValueError("Matrix dimensions must be positive")
    left, top, width, height = box
    cell_w = min(135, (width - 55) / cols)
    cell_h = min(125, (height - 42) / rows)
    mx = left + width / 2 - cols * cell_w / 2
    my = top + height / 2 - rows * cell_h / 2
    return mx, my, cell_w, cell_h


def matrix_cell_rects(rows, cols, x, y, w, h):
    """Return full cell bounds as row-major (x, y, width, height) tuples.

    Coordinates match the printed values exactly. Entry fields may inset these
    bounds by 2–3 screen pixels; row 0 is visually the uppermost matrix row.
    """
    mx, my, cell_w, cell_h = _matrix_geometry(rows, cols)
    return [[(x + (mx + col * cell_w) * w / WIDTH,
              y + (HEIGHT - my - (row + 1) * cell_h) * h / HEIGHT,
              cell_w * w / WIDTH, cell_h * h / HEIGHT)
             for col in range(cols)] for row in range(rows)]


def matrix_cell_at(rows, cols, card_rect, px, py):
    """Return a cell under a screen point, or None outside the matrix cells."""
    for row, rects in enumerate(matrix_cell_rects(rows, cols, *card_rect)):
        for col, (x, y, w, h) in enumerate(rects):
            if x <= px < x + w and y <= py < y + h:
                return row, col
    return None


def _matrix(draw, values, box, *, blank=False):
    rows, cols = len(values), len(values[0])
    mx, my, cell_w, cell_h = _matrix_geometry(rows, cols, box)
    if blank:
        values = ()
    for i, row in enumerate(values):
        for j, raw in enumerate(row):
            value = Fraction(raw)
            cx, cy = mx + (j + .5) * cell_w, my + (i + .5) * cell_h
            if value.denominator == 1:
                text = str(value.numerator).replace("-", "−")
                size = 58 if max(rows, cols) < 4 else 49
                while size > 16 and draw.textlength(text, font=_font(size)) > cell_w - 14:
                    size -= 2
                text = _ellipsize(draw, text, _font(size), cell_w - 14)
                draw.text((cx, cy), text, font=_font(size), fill=INK, anchor="mm")
            else:
                numerator, denominator = str(value.numerator).replace("-", "−"), str(value.denominator)
                size = 38
                while size > 14 and max(draw.textlength(s, font=_font(size)) for s in (numerator, denominator)) > cell_w - 18:
                    size -= 2
                numerator, denominator = (_ellipsize(draw, s, _font(size), cell_w - 18)
                                          for s in (numerator, denominator))
                line = max(draw.textlength(s, font=_font(size)) for s in (numerator, denominator)) + 10
                draw.text((cx, cy - size * .6), numerator, font=_font(size), fill=INK, anchor="mm")
                draw.line((cx - line / 2, cy, cx + line / 2, cy), fill=INK, width=2)
                draw.text((cx, cy + size * .6), denominator, font=_font(size), fill=INK, anchor="mm")
    bx, by = mx - 16, my + 5
    right, bottom = mx + cols * cell_w + 16, my + rows * cell_h - 5
    draw.line((bx + 12, by, bx, by, bx, bottom, bx + 12, bottom), fill=INK, width=4)
    draw.line((right - 12, by, right, by, right, bottom, right - 12, bottom), fill=INK, width=4)


@lru_cache(maxsize=128)
def _face(key):
    kind, cid, *data = key
    tint = TINTS[kind]
    face = Image.new("RGBA", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(face)
    for y in range(HEIGHT):
        mix = min(1, y / 570)
        draw.line((0, y, WIDTH, y), fill=tuple(round(c + (255 - c) * mix) for c in tint) + (255,))
    draw.rectangle((0, 0, WIDTH, 16), fill=COLORS[kind])
    draw.polygon(((38, 49), (44, 43), (50, 49), (44, 55)), fill=COLORS[kind])
    draw.text((61, 40), NAMES[kind], font=_font(18, True), fill=INK, anchor="lt")
    id_width = max(58, round(draw.textlength(cid, font=_font(17))) + 19)
    draw.rounded_rectangle((594-id_width, 34, 594, 64), radius=7, fill=(255,255,255,210), outline="#d8dde4", width=2)
    draw.text((594-id_width/2, 49), cid, font=_font(17), fill=MUTED, anchor="mm")
    if kind == "operation":
        code = data[0]
        title, rule = OP_COPY[code]
        _text(draw, title, 36, 93, 558, 35, bold=True, leading=38)
        _paste_art(face, "operation_" + code, (28, 208, 574, 340))
        _rule(draw, rule, 590, kind)
    elif kind == "objective":
        title, shape = data
        _text(draw, title, 36, 93, 558, 35, bold=True, leading=38)
        _text(draw, shape, 36, 181, 558, 20, bold=True, color="#007853")
        _paste_art(face, "objective_" + cid, (36, 220, 558, 98))
        draw.rounded_rectangle((36, 343, 594, 601), radius=19, fill="#f1f8f5")
        draw.text((53, 359), "EXAMPLE", font=_font(16, True), fill=MUTED, anchor="lt")
        _paste_art(face, "example_" + cid, (88, 391, 454, 190))
        _rule(draw, OBJECTIVE_COPY[cid], 629, kind)
    else:
        values = data[0]
        title = ("Result Matrix" if cid.startswith("G") else "Starting Matrix") if kind == "blue" else "Matrix Card"
        _text(draw, title, 36, 93, 558, 35, bold=True)
        draw.text((36, 199), f"{len(values)} × {len(values[0])}", font=_font(40, True), fill=COLORS[kind], anchor="lt")
        draw.text((188, 214), "ROWS × COLUMNS", font=_font(17, True), fill=MUTED, anchor="lt")
        draw.rounded_rectangle((36, 270, 594, 840), radius=27, fill="white", outline=COLORS[kind], width=5)
        _matrix(draw, values, MATRIX_BOX, blank=data[1])
    # The alpha mask also clips the top band to the rounded card corners.
    mask = Image.new("L", (WIDTH, HEIGHT))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, WIDTH - 1, HEIGHT - 1), radius=36, fill=255)
    face.putalpha(mask)
    ImageDraw.Draw(face).rounded_rectangle((1, 1, WIDTH - 2, HEIGHT - 2), radius=35, outline="#cbd3de", width=2)
    return face


def _highlight_key(highlights):
    return tuple(sorted((row, col, tuple(color))
                        for (row, col), color in (highlights or {}).items()))


@lru_cache(maxsize=128)
def _highlighted_face(key, highlights):
    face = _face(key)
    if key[0] not in ("blue", "red") or not highlights:
        return face
    face = face.copy()
    values = key[2]
    cells = matrix_cell_rects(len(values), len(values[0]), 0, 0, WIDTH, HEIGHT)
    overlay = Image.new("RGBA", face.size)
    draw = ImageDraw.Draw(overlay)
    for row, col, color in highlights:
        if not (0 <= row < len(cells) and 0 <= col < len(cells[row])):
            continue
        x, y, w, h = cells[row][col]
        # Leave breathing room between adjacent cells and around the brackets.
        box = (x + 5, HEIGHT - y - h + 5, x + w - 5, HEIGHT - y - 5)
        outline = color[:3] + (min(255, color[3] + 100),)
        draw.rounded_rectangle(box, radius=10, fill=color, outline=outline, width=3)
    face.alpha_composite(overlay)
    return face


def render_card_image(card, kind, *, blank=False, highlights=None):
    """Return a rounded RGBA face; optional matrix blanking/tints match draw_card."""
    return _highlighted_face(_record_key(card, kind, blank=blank), _highlight_key(highlights)).copy()


@lru_cache(maxsize=128)
def _texture(key, highlights=()):
    return arcade.Texture(_highlighted_face(key, highlights))


def get_card_texture(card, kind, *, blank=False, highlights=None):
    """Return a cached Arcade texture of the face, excluding its shadow."""
    return _texture(_record_key(card, kind, blank=blank), _highlight_key(highlights))


@lru_cache(maxsize=4)
def _shadow(raised, selected):
    margin = 80
    image = Image.new("RGBA", (WIDTH + 2 * margin, HEIGHT + 2 * margin))
    draw = ImageDraw.Draw(image)
    offset = 25 if raised else 13
    opacity = 125 if raised else 87
    draw.rounded_rectangle((margin + 5, margin + offset, margin + WIDTH - 1 + 5, margin + HEIGHT - 1 + offset), radius=37, fill=(5, 13, 28, opacity))
    image = image.filter(ImageFilter.GaussianBlur(22 if raised else 13))
    return arcade.Texture(image)


@lru_cache(maxsize=1)
def _selection():
    image = Image.new("RGBA", (WIDTH + 20, HEIGHT + 20))
    ImageDraw.Draw(image).rounded_rectangle((3, 3, WIDTH + 16, HEIGHT + 16), radius=43, outline="#f9d968", width=6)
    return arcade.Texture(image)


def draw_card(card, kind, x, y, w, h, *, scale=1.0, raised=False, selected=False,
              blank=False, highlights=None):
    """Draw a card at bottom-left x/y, with visible depth and optional gold ring.

    The caller may move a hovered/dragged card upward. Setting raised=True
    increases its shadow depth without changing the supplied face bounds.
    """
    if w <= 0 or h <= 0 or scale <= 0:
        return
    px, py, pw, ph = x * scale, y * scale, w * scale, h * scale
    mx, my = pw * 80 / WIDTH, ph * 80 / HEIGHT
    arcade.draw_texture_rect(_shadow(bool(raised), bool(selected)), arcade.LBWH(px - mx, py - my, pw + 2*mx, ph + 2*my))
    if selected:
        sx, sy = pw * 10 / WIDTH, ph * 10 / HEIGHT
        arcade.draw_texture_rect(_selection(), arcade.LBWH(px-sx, py-sy, pw+2*sx, ph+2*sy))
    arcade.draw_texture_rect(get_card_texture(card, kind, blank=blank, highlights=highlights), arcade.LBWH(px, py, pw, ph))
