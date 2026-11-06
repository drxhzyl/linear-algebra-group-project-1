# GameTrix local card lab

Latest experiment: [40 added operations, with separate +1 and −1 cards](expansion_split/REPORT.md). Original cards are preserved; the new operation deck has 80 cards.

The [operation-card gallery](expansion_split/generated/operation_gallery.html) shows all 18 operation types with LaTeX diagrams. The [complete illustrated deck](expansion_split/generated/cards.html) has 137 physical cards, and the [added-card sheet](expansion_split/generated/extra_operations.html) has the 40 added operations. Each card is 63 × 88 mm; print at 100% on A4, with background graphics enabled, for nine cards per page. All SVG formulas are embedded, so the HTML files work offline.

Generate a compact print PDF locally with `export_cards_pdf.py` using Python with ReportLab and svglib; it reuses the current card text and cached vector diagrams. The generated PDF is written to `output/pdf/` and is excluded from Git. It contains all 137 physical cards plus 120 blank blue and 60 blank red cards: 317 cards on 27 A4 pages, at 12 cards per page. This compact edition uses 63 × 67 mm cards. Print at 100% / Actual Size; cut along the borders. Pages 1-12 contain the deck, 13-22 the blank blue cards, and 23-27 the blank red cards. The 120 blue blanks allow one recorded result for each of the 120 operations drawn over five eight-turn games, with 60 red blanks in reserve. The blank sheets can be reprinted separately.

A local Arcade game is available for solo practice, with automatic calculation and student-answer verification. Double-click **Play Automatic.command** or **Play Student.command** on this Mac. See [the digital game guide](DIGITAL_README.md) and [Chinese architecture document](digital/ARCHITECTURE.zh-CN.md).

The command-line tool described below uses the Python standard library. It generates physical cards, deals them reproducibly, does exact matrix calculations, and records agent playtests. Agents supply the strategy. There is no search solver or multiplayer implementation.

Run commands from this directory with Python 3.11 or later. No installation is needed.

To rebuild only the card appearance, run `python3 render_cards.py`. This preserves the deck JSON files and their hashes. Artwork comes from `card_art.py`, layout and descriptions from `card_layout.py`, and styling from `design/cards.css`. The complete generated LaTeX source is `design/illustrations.tex`. Building uncached artwork requires `pdflatex` (with TikZ, AMS math, standalone, and Latin Modern) and Poppler's `pdftocairo`; an alternate Poppler executable can be supplied with `GAMETRIX_PDFTOCAIRO`. Existing artwork is cached in `design/formula_cache.json`.

Current card-face rules allow two blue cards, two red cards, or one of each to operate together. Descriptions contain the mathematical effect and its specific conditions; repeated card-use and discarding instructions are omitted. Diagram colors distinguish A, B, and the result, not physical card types. Matrix cards themselves contain only a title, dimensions, and the matrix.

The command-line play engine and historical deck JSON files still use the earlier first-finish rules, red-operand restrictions, and single-entry material costs described below. They remain reproducible playtest fixtures; the visual update does not implement eight-turn collection scoring or the new operand-color rule in that engine.

The first 18 agent playtests and findings are in [playtests/REPORT.md](playtests/REPORT.md).
The follow-up limited-calculation experiment is in [student_tests/REPORT.md](student_tests/REPORT.md), with its explicit limits and caveats. `student_play.py` enforces candidate and preview budgets and suppresses free mathematical diagnostics for those sessions.

## Generated cards

- generated/cards.html: 97 printable cards (12 blue, 30 red, 40 operation, 15 main objective cards).
- generated/deck.json: the same cards, with unique physical IDs.
- generated/generation_report.json: seed and generation status.
- rules_source.txt: snapshot of the Google Doc, including its revision.

Blue cards pass entry, invertibility, duplicate, and initial-win checks. They are **provisional candidates**: universal reachability, six-operation solutions, and the 10% opening-win target have not been certified.

Generate a new independent deck:

    python3 gametrix.py generate --seed 20261028 --out generated

Use a different output directory to compare seeds. The --force option replaces generated output, but existing sessions reject a changed deck hash.

## Turns

Every turn starts with **3 operation cards and 5 red cards**. Keep every unused card. You must perform **at least one operation** before ending the turn; you may perform several. The play command does not automatically draw or end the turn. A verified win ends the session immediately.

No free pass or rescue draw is specified when all available operations are unusable. Record such a case with stop; this is a test observation, not a new game action. A legal operation that leaves the matrix unchanged is currently accepted and explicitly logged.

## Deal and play

    python3 gametrix.py start playtests/example.json --seed 101 --objective C11 --blue B01 --mode draw --player human
    python3 gametrix.py show playtests/example.json
    python3 gametrix.py show playtests/example.json --brief

The draw mode uses real draw/discard rules. The open mode puts the entire finite deck in hand, with no reshuffle, for resource-feasibility experiments. Open-mode results are reported separately and are not estimates of normal game length.

Preview a move without consuming cards:

    python3 gametrix.py calc --session playtests/example.json --op append_vector --red R03 --axis row --source 0

Play the physical operation card in your hand; use its actual ID from show:

    python3 gametrix.py play playtests/example.json --operation O21 --red R03 --axis row --source 0 --note "Append the first row of R03."
    python3 gametrix.py end-turn playtests/example.json

All row and column indexes are **zero-based**. Red vectors keep their orientation.

- add, subtract, multiply: supply --red.
- add_vector, replace_vector: supply --red --axis row|column --source N --target N.
- append_vector: supply --red --axis row|column --source N; omit --target.
- swap: supply --axis row|column --i N --j N.
- lu: choose --factor L or --factor U.
- Other operation codes: transpose, inverse, shift_plus, shift_minus, negate, double.

The --turn-cap (default 12) and --move-cap (default 20) are experimental stopping budgets, not game rules. Reaching a cap is **inconclusive**, not proof of impossibility.

    python3 gametrix.py stop playtests/example.json --note "Stopped after unsuccessful planning; no impossibility proof."

## Standalone calculator

Matrices are JSON arrays; fractions are quoted strings such as "1/2".

    python3 gametrix.py calc --matrix '[[1,1,0],[0,0,0],[0,0,1]]' --op check --objective C08
    python3 gametrix.py calc --matrix '[[0,1,0],[0,0,1],[0,0,0]]' --op power --exponent 3
    python3 gametrix.py calc --matrix '[[1,1],[1,-1],[1,0]]' --op facts

Use --other instead of --red for a standalone second matrix.

## Playtest protocol and statistics

Players should inspect only their visible hand in draw mode; do not inspect the session file's hidden draw order. They may inspect all cards in open mode. Prefer deliberate short plans, preview calculations, and record a short rationale with each move.

Each session JSON records every operation, its physical card IDs, parameters, exact before/after matrices, and the goal check. End-turn events record draws. Summary rechecks final winning matrices and separates open-deck experiments from random-deal play.

Summary also replays every seeded draw and operation, checking card consumption and the final inventory. The first experiment's immutable deck is `playtests/deck_used.json`; its sessions reference that snapshot. The current generated deck corrects only the negative-identity example metadata, with identical blue, red and operation cards.

    python3 gametrix.py summary --directory playtests --out playtests/summary.json
    python3 -m unittest discover -s tests -v

Check exact opening deadlock probabilities and a reproducible blocked-hand example:

    python3 diagnostics.py --deck playtests/deck_used.json

This diagnostic counts legal opening hands by shape. It does not choose moves or search for winning paths. Its deliberately selected blocked example is excluded from the agent-play statistics.

Steps mean operation plays. Turns can contain multiple steps. Winning averages exclude unsolved/capped runs and must always be reported with the success count. A small agent-selected sample is exploratory, not a population balance estimate. A wrong shape, an unusable hand, exhausted cards, and a failed attempt are different findings; none alone proves the starting objective globally unreachable.
