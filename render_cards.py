#!/usr/bin/env python3
"""Rebuild artwork and printable HTML without regenerating any physical deck."""

import hashlib
from pathlib import Path

import gametrix as g
import card_art
import card_layout


def main():
    paths = [g.ROOT / p / "deck.json" for p in
             ("generated", "expansion_v1/generated", "expansion_split/generated")]
    paths = [p for p in paths if p.exists()]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    decks = [(p, g.read_json(p)) for p in paths]
    sources = [src for _, deck in decks for src in card_layout.artwork_sources(deck)]
    _, count = card_art.compile_art(sources)
    for path, deck in decks:
        card_layout.write_collection(path.parent, deck, build_art=False)
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p, h in before.items())
    print(f"Compiled {count} new LaTeX diagrams. Updated {len(decks)} printable collections. Deck JSON files unchanged.")


if __name__ == "__main__":
    main()
