"""Small rule diagnostics, not a strategy search or automated player."""

import argparse
from collections import Counter
from fractions import Fraction
from itertools import product
from math import comb

import gametrix as g
import matrix as mx


def usable_codes(A, red_cards):
    """Which operation types have at least one legal play? No move is selected."""
    m, n = mx.shape(A)
    shapes = [mx.shape(mx.matrix(c["matrix"])) for c in red_cards]
    row = any(bn == n for bm, bn in shapes)
    column = any(bm == m for bm, bn in shapes)
    usable = {"transpose", "swap", "shift_plus", "shift_minus", "negate", "double"}
    if 2 <= m <= 4 and 2 <= n <= 4:
        usable.add("combine_vectors")
        if red_cards:
            usable.update(g.RED_FUEL_OPS)
    if (m, n) in shapes:
        usable.update(("add", "subtract"))
    if any(bm == n for bm, bn in shapes):
        usable.add("multiply")
    if row or column:
        usable.update(("add_vector", "replace_vector"))
    if (row and m < 4) or (column and n < 4):
        usable.add("append_vector")
    if m == n and mx.det(A):
        usable.add("inverse")
    if m == n:
        try:
            mx.lu(A)
        except ValueError:
            pass
        else:
            usable.add("lu")
    return usable


def opening_deadlock_probability(deck, A):
    """Exact probability for an invertible 3x3 start, uniformly drawn 3+5 cards.

    Group red cards by whether their rows/columns have length 3. For each
    possible five-card shape composition, count all three-operation hands
    drawn entirely from operation types that are unusable with that hand.
    This sums 216 small composition cases, not game states or move paths.
    """
    if mx.shape(A) != (3, 3) or not mx.det(A):
        raise ValueError("Opening formula requires an invertible 3x3 matrix")
    groups = [[], [], [], []]  # both 3; 3 rows only; 3 columns only; neither
    for card in deck["red"]:
        m, n = mx.shape(mx.matrix(card["matrix"]))
        groups[0 if m == n == 3 else 1 if m == 3 else 2 if n == 3 else 3].append(card)
    counts = [len(group) for group in groups]
    op_counts = Counter(c["code"] for c in deck["operations"])
    unavailable_base = set(op_counts) - usable_codes(A, deck["red"])
    blocked = 0
    for a, b, c in product(range(6), repeat=3):
        d = 5 - a - b - c
        draw_counts = (a, b, c, d)
        if any(k < 0 or k > size for k, size in zip(draw_counts, counts)):
            continue
        ways = 1
        for k, size in zip(draw_counts, counts):
            ways *= comb(size, k)
        illegal = set(unavailable_base)
        if a == 0:
            illegal.update(("add", "subtract"))
        if a + b == 0:
            illegal.add("multiply")
        if a + b + c == 0:
            illegal.update(("add_vector", "replace_vector", "append_vector"))
        blocked += ways * comb(sum(op_counts[code] for code in illegal), 3)
    return Fraction(blocked, comb(len(deck["red"]), 5) * comb(len(deck["operations"]), 3))


def report(deck_path):
    deck = g.read_json(deck_path)
    probabilities = []
    for blue in deck["blue"]:
        A = mx.matrix(blue["matrix"])
        p = opening_deadlock_probability(deck, A)
        probabilities.append({"blue": blue["id"], "lu_legal": "lu" in usable_codes(A, []),
                              "probability": str(p), "percent": 100 * float(p)})
    average = sum((Fraction(row["probability"]) for row in probabilities), Fraction(0)) / len(probabilities)
    example = None
    for seed in range(10000):
        s = g.new_session(deck_path, seed, "C01", "B01", "draw", "diagnostic", 8, 16)
        reds = [g.lookup(deck, "red", cid) for cid in s["red_hand"]]
        usable = usable_codes(mx.matrix(s["current"]), reds)
        if not any(g.lookup(deck, "operations", cid)["code"] in usable for cid in s["operation_hand"]):
            example = g.show(s, deck)
            break
    return {"kind": "gametrix-opening-diagnostic", "deck_sha256": g.deck_hash(deck_path),
            "assumptions": "Uniform independent deck shuffles, 3 operations and 5 red cards, invertible 3x3 starts; legal unchanged results allowed; no rescue draw or free pass.",
            "per_blue": probabilities, "uniform_blue_mean": {"probability": str(average), "percent": 100 * float(average)},
            "blocked_example": example,
            "example_note": "First blocked seed in 0..9999 for B01. Deliberately selected diagnostic; exclude from random-play win statistics.",
            "scope": "Proves a turn cannot legally proceed under the present rules. Does not prove the objective is mathematically unreachable with other cards or rules."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deck", type=g.Path, default=g.ROOT/"generated"/"deck.json")
    parser.add_argument("--out", type=g.Path, default=g.ROOT/"playtests"/"opening_diagnostic.json")
    args = parser.parse_args()
    result = report(args.deck)
    g.write_json(args.out, result)
    print(g.json.dumps(result, indent=2, ensure_ascii=False))
