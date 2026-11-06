"""Print and screen layouts for the illustrated GameTrix cards."""

from html import escape
from pathlib import Path
import re

import card_art as art

ROOT = Path(__file__).resolve().parent

# Current card-face rules; historical deck JSON files remain playtest fixtures.
OP_COPY = {
    "add": ("Add a Matrix", "Add the corresponding entries of two matrices. Both matrices must have the same number of rows and columns."),
    "subtract": ("Subtract a Matrix", "Subtract each entry of B from the corresponding entry of A. A and B must have the same number of rows and columns."),
    "multiply": ("Right Multiply", "Multiply A by B on the right. The number of columns in A must equal the number of rows in B."),
    "add_vector": ("Add to a Row or Column", "Add a whole row or column from B to a row or column of A with the same length and orientation."),
    "append_vector": ("Append a Row or Column", "Append a whole row from B below A, or a whole column from B to the right of A. Its length must match an existing row or column of A, respectively."),
    "replace_vector": ("Replace a Row or Column", "Replace a row or column of A with a whole row or column from B of the same length and orientation."),
    "transpose": ("Transpose", "Turn every row into a column. An m × n matrix becomes n × m."),
    "swap": ("Interchange", "Exchange two existing rows or two existing columns."),
    "shift_plus": ("+1 to Every Entry", "Add exactly 1 to every entry, including entries outside the diagonal. J is the all-ones matrix."),
    "shift_minus": ("−1 from Every Entry", "Subtract exactly 1 from every entry, including entries outside the diagonal. J is the all-ones matrix."),
    "negate": ("Multiply by −1", "Reverse the sign of every entry."),
    "double": ("Multiply by 2", "Double every entry."),
    "inverse": ("Inverse", "Find the inverse of a square, invertible matrix."),
    "lu": ("LU Factorization", "For a square matrix, use Doolittle LU with unit diagonal in L and no row swaps. The first n − 1 pivots must be nonzero. Record either L or U."),
    "entry_plus": ("+1 to One Entry", "Choose one entry and add exactly 1. Every other entry stays unchanged."),
    "entry_minus": ("−1 from One Entry", "Choose one entry and subtract exactly 1. Every other entry stays unchanged."),
    "entry_zero": ("Clear One Entry", "Choose one entry and set it to 0. Every other entry stays unchanged."),
    "entry_tweak": ("±1 to One Entry", "Choose one entry and either add 1 or subtract 1. Every other entry stays unchanged."),
    "combine_vectors": ("Add or Subtract Rows / Columns", "Choose two distinct rows or two distinct columns of one matrix. Add or subtract the source from the target. Use one sign for the whole vector; keep the source unchanged."),
}

OBJECTIVE_COPY = {
    "C01": "The matrix must be symmetric, invertible, and non-diagonal.",
    "C02+": "Every diagonal entry is 1. Every other entry is 0.",
    "C02-": "Every diagonal entry is −1. Every other entry is 0.",
    "C03": "The matrix must be diagonal. Its diagonal entries must be nonzero, with at least three distinct values.",
    "C04": "Every row and every column sums to 1. Include at least one negative entry.",
    "C05": "Opposite entries have opposite signs. The diagonal is zero, and the matrix is not zero.",
    "C06": "Squaring gives the identity. The matrix must be non-diagonal.",
    "C07": "The determinant must be 1. Every row and column must contain at least two nonzero entries.",
    "C08": "Squaring must leave the matrix unchanged. It must be non-diagonal, with rank exactly 2.",
    "C09": "The third power is zero, but the second power is not zero.",
    "C10": "The third power is the identity. Exclude signed permutation matrices: exactly one nonzero entry per row and column, all ±1.",
    "C11": "The columns must be nonzero and pairwise orthogonal. The matrix must be tall, with no zero rows.",
    "C12": "The rows must be nonzero and pairwise orthogonal. The matrix must be wide, with no zero columns.",
    "C13": "For a non-square m × n matrix: each row sums to n, each column to m. Include a negative entry.",
    "C14": "The rows must be nonzero and pairwise orthogonal, each summing to 0. The matrix must be wide, with no zero columns.",
}


KEY_TERMS = [
    "same number of rows and columns", "same length and orientation", "one entry", "exactly 1",
    "set it to 0", "every entry", "two distinct rows", "two distinct columns", "keep the source unchanged",
    "below A", "on the right", "to the right of A", "square, invertible", "no row swaps", "unit diagonal", "first n − 1 pivots",
    "either L or U", "non-diagonal", "symmetric", "skew-symmetric", "invertible",
    "nonzero", "at least three distinct values", "at least two nonzero entries", "negative entry",
    "rank exactly 2", "unchanged", "signed permutation matrices", "pairwise orthogonal", "no zero rows",
    "diagonal entry is 1", "diagonal entry is −1", "other entry is 0", "determinant must be 1",
    "no zero columns", "summing to 0", "third power", "second power", "tall", "wide",
]


def highlighted(text):
    pattern = re.compile("|".join(re.escape(k) for k in sorted(KEY_TERMS, key=len, reverse=True)), re.IGNORECASE)
    result, end = [], 0
    for match in pattern.finditer(text):
        result.append(escape(text[end:match.start()]))
        value = match.group()
        result.append(f'<strong class="term">{escape(value)}</strong>')
        end = match.end()
    result.append(escape(text[end:]))
    return "".join(result)


def artwork_sources(deck):
    result = [art.operation_art(c["code"]) for c in deck["operations"]]
    result += [art.matrix_art(c["matrix"]) for k in ("blue", "red") for c in deck[k]]
    for c in deck["objectives"]:
        result.extend((art.objective_art(c), art.matrix_art(c["A"])))
    return result


def header(kind, card_id, title):
    names = {"operation": "OPERATION", "blue": "BLUE MATRIX", "red": "RED MATRIX", "objective": "OBJECTIVE"}
    return (f'<header class="card-head"><div class="identity"><span class="kind">'
            f'<span class="kind-mark" aria-hidden="true"></span>{names[kind]}</span>'
            f'<span class="card-id">{escape(card_id)}</span></div>'
            f'<h2>{escape(title)}</h2></header>')


def operation_card(card, cache):
    code = card["code"]
    title, rule = OP_COPY[code]
    body = header("operation", card["id"], title)
    body += '<div class="diagram">' + art.svg_image(art.operation_art(code), rule, cache) + '</div>'
    body += f'<div class="instruction"><p>{highlighted(rule)}</p>'
    body += '</div>'
    return f'<article id="{escape(card["id"])}" class="card operation" data-code="{escape(code)}" data-card-id="{escape(card["id"])}">{body}</article>'


def matrix_card(card, kind, cache):
    A = card["matrix"]
    size = f'{len(A)} × {len(A[0])}'
    title = "Starting Matrix" if kind == "blue" else "Matrix Card"
    body = header(kind, card["id"], title)
    body += f'<div class="dimension"><strong>{size}</strong><span>ROWS × COLUMNS</span></div>'
    body += '<div class="matrix-window">' + art.svg_image(art.matrix_art(A), str(A), cache) + '</div>'
    return f'<article id="{escape(card["id"])}" class="card {kind}" data-card-id="{escape(card["id"])}">{body}</article>'


def objective_card(card, cache):
    oid = card["id"]
    body = header("objective", oid, card["name"])
    body += f'<div class="shape-tag">{escape(card["shape"])}</div>'
    body += '<div class="objective-formula">' + art.svg_image(art.objective_art(card), card["goal"], cache) + '</div>'
    body += '<div class="objective-example"><span>Example</span>'
    body += art.svg_image(art.matrix_art(card["A"]), card["check"], cache) + '</div>'
    body += f'<div class="instruction"><p>{highlighted(OBJECTIVE_COPY[oid])}</p></div>'
    return f'<article id="{escape(oid)}" class="card objective" data-card-id="{escape(oid)}">{body}</article>'


def printable(deck, *, title="Complete deck", gallery=False):
    cache = art.load_cache()
    cards = []
    for kind, records in [("blue", deck["blue"]), ("red", deck["red"]),
                          ("operation", deck["operations"]), ("objective", deck["objectives"])]:
        for c in records:
            if kind == "operation":
                cards.append(operation_card(c, cache))
            elif kind == "objective":
                cards.append(objective_card(c, cache))
            else:
                cards.append(matrix_card(c, kind, cache))
    pages = []
    for i in range(0, len(cards), 9):
        pages.append(f'<section class="page" aria-label="Card sheet {i//9+1}">'
                     + "".join(cards[i:i+9]) + '</section>')
    css = (ROOT / "design" / "cards.css").read_text()
    label = "unique operation designs" if gallery else "physical cards"
    extra_link = '<a href="extra_operations.html">40 added cards</a>' if deck.get("expansion") else ''
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GameTrix · {escape(title)}</title><style>{css}</style></head>
<body><div class="toolbar"><div class="masthead"><a class="wordmark" href="operation_gallery.html"><span class="brand-icon">[<b>×</b>]</span>GameTrix</a><button type="button" onclick="window.print()">Print cards <span aria-hidden="true">↗</span></button></div>
<div class="collection-heading"><div><h1>{escape(title)}</h1><p class="intro">{'This page shows one card for each type of operation.' if gallery else 'Print these cards and cut along their borders.'}</p></div><div class="collection-count"><strong>{len(cards):02d}</strong><span>{label}<br>63 × 88 mm · A4</span></div></div>
<nav aria-label="Card collection"><a href="operation_gallery.html" {'aria-current="page"' if gallery else ''}>Operation gallery</a><a href="objective_gallery.html" {'aria-current="page"' if title=='Objective cards' else ''}>Objective cards</a>{extra_link}<a href="cards.html" {'aria-current="page"' if title=='Complete deck' else ''}>Complete deck</a></nav>
<div class="legend"><span><i class="blue-key"></i>Blue outlines identify A.</span><span><i class="operand-key"></i>Violet outlines identify B or a vector from B.</span><span><i class="hot-key"></i>Pink highlights selected entries.</span><span><i class="green-key"></i>Green outlines mark the result.</span><span class="square-key">□ <span>Each square represents an unspecified entry; it does not mean zero.</span></span></div>
<p class="usage">Two blue cards, two red cards, or one of each may be used together. Diagram colors distinguish mathematical roles, not card types. Each matrix has 2–4 rows and 2–4 columns; use exact arithmetic. Print at 100% on A4 with background graphics enabled.</p></div>
<main>{''.join(pages)}</main></body></html>'''


def gallery_deck(deck):
    order = ["add", "entry_plus", "entry_zero", "multiply", "append_vector", "combine_vectors",
             "transpose", "entry_minus", "swap", "subtract", "add_vector", "replace_vector",
             "shift_plus", "shift_minus", "double", "negate", "inverse", "lu", "entry_tweak"]
    unique = {c["code"]: c for c in reversed(deck["operations"])}
    return {**deck, "blue": [], "red": [], "objectives": [],
            "operations": [unique[k] for k in order if k in unique]}


def ensure_art(deck):
    sources = artwork_sources(deck)
    cache = art.load_cache()
    if any(art.source_key(s) not in cache for s in sources):
        art.compile_art(sources)


def write_collection(directory, deck, build_art=True):
    if build_art:
        ensure_art(deck)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "cards.html").write_text(printable(deck), encoding="utf-8")
    (directory / "operation_gallery.html").write_text(
        printable(gallery_deck(deck), title="Operation cards", gallery=True), encoding="utf-8")
    goals = {**deck, "blue": [], "red": [], "operations": []}
    (directory / "objective_gallery.html").write_text(
        printable(goals, title="Objective cards"), encoding="utf-8")
    if deck.get("expansion"):
        extra = {**deck, "blue": [], "red": [], "objectives": [], "operations": deck["operations"][40:]}
        (directory / "extra_operations.html").write_text(
            printable(extra, title="40 added operation cards"), encoding="utf-8")
