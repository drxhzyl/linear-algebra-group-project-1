"""Append 40 simple operation cards without changing any existing card."""

import argparse
import copy

import gametrix as g


EXTRA_OPERATIONS = [
    ("entry_tweak", "Adjust One Entry ±1", 24,
     "Choose one entry and add 1 or subtract 1. Discard any one red card as fuel; its shape and entries do not matter."),
    ("entry_zero", "Clear One Entry", 8,
     "Set one entry to zero. Discard any one red card as fuel; its shape and entries do not matter."),
    ("combine_vectors", "Add or Subtract an Existing Row / Column", 8,
     "Choose two distinct rows or two distinct columns of your current matrix. Add or subtract the source from the target; keep the source unchanged. No red card."),
]
SPLIT_OPERATIONS = [
    ("entry_plus", "Add 1 to One Entry", 12,
     "Choose one entry and add exactly 1. Discard any one red card as fuel; its shape and entries do not matter. You cannot choose subtraction."),
    ("entry_minus", "Subtract 1 from One Entry", 12,
     "Choose one entry and subtract exactly 1. Discard any one red card as fuel; its shape and entries do not matter. You cannot choose addition."),
    *EXTRA_OPERATIONS[1:],
]


def expanded_deck(base_path, split_signs=False):
    base = g.read_json(base_path)
    if len(base["operations"]) != 40:
        raise ValueError("This expansion requires the original 40-operation deck")
    deck = copy.deepcopy(base)
    additions = SPLIT_OPERATIONS if split_signs else EXTRA_OPERATIONS
    for code, name, copies, rule in additions:
        for _ in range(copies):
            deck["operations"].append({"id": f'O{len(deck["operations"])+1:02d}',
                                       "kind": "operation", "code": code, "name": name, "rule": rule})
    deck["expansion"] = {
        "name": "Simple operations +40" + ("; fixed signs" if split_signs else "; flexible signs"),
        "base_deck_sha256": g.deck_hash(base_path),
        "added_operation_counts": {code: count for code, _, count, _ in additions},
        "unchanged": "All original blue, red, objective and O01–O40 cards; turn draws stay 3 operations + 5 red.",
    }
    deck["status"] = "experimental expansion: original cards unchanged; added 40 operations; reachability and balance not certified"
    return deck


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=g.Path, default=g.ROOT/"generated"/"deck.json")
    parser.add_argument("--split-signs", action="store_true")
    parser.add_argument("--out", type=g.Path)
    args = parser.parse_args()
    args.out = args.out or g.ROOT/("expansion_split" if args.split_signs else "expansion_v1")/"generated"
    if (args.out/"deck.json").exists():
        raise ValueError("Expansion exists; choose another output directory")
    deck = expanded_deck(args.base, args.split_signs)
    g.write_json(args.out/"deck.json", deck)
    from card_layout import write_collection
    write_collection(args.out, deck)
    report = {"kind": "gametrix-expansion-report", "counts": {k: len(deck[k]) for k in ("blue", "red", "operations", "objectives")}, **deck["expansion"]}
    g.write_json(args.out/"generation_report.json", report)
    print(g.json.dumps(report, indent=2, ensure_ascii=False))
