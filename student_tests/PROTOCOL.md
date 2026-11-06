# Limited-calculation playtest protocol

This is an experimental decision budget, not a change to the game rules. The player represents a student who knows matrix addition/multiplication, transpose, simple row operations, basic determinant/rank concepts and the stated LU rule. This agent experiment cannot validate real human difficulty.

Read this file and use only `student_play.py` while playing. Do not read previous reports, sessions, source, generated deck, future cards, or other players' games. You receive only your assigned two session filenames. Do not use scripts, a solver, external references, symbolic algebra, or repeated manual matrix calculations. Do not use companion matrices, spectral/minimal-polynomial arguments, or a memorized general construction of a winning target.

Every turn draws 3 operation cards and 5 red cards; unused cards remain in hand. At least one operation must be played before ending the turn. Several operations are allowed, but the experiment permits at most two proposed candidate actions in that turn. A rejected/unused candidate still counts. Maximum 8 turns and 16 operation plays are experimental stopping limits.

Per turn, inspect the visible matrix/hand once and select no more than two plausible actions. Give a short concrete reason such as clearing a visible entry, making two entries equal, improving row sums, or arranging a useful shape. Do not enumerate card/vector combinations. If neither action looks useful, prefer one obvious legal move that preserves something useful, or choose one bounded exploratory candidate and use the permitted preview to learn its effect. Do not continue a long futile calculation just to win.

At most one complete matrix preview per turn, and six previews per game. The wrapper enforces this and records previews, including invalid ones. Any full matrix operation computed manually would count as a preview too; avoid doing this outside the wrapper. Simple inspection, matching dimensions, comparing entries, a single dot product or row sum are allowed mental checks, but do not sweep all cards, all vectors or all combinations. Multiplication/powers/rank/determinant of full candidates must not be computed outside the wrapper. Automated checking after a committed play acts as the referee and is not a preview; only the resulting matrix and win status are exposed to you.

Minimum engagement: attempt at least three complete turns unless you win, have no legal operation, or both candidate slots were spent on illegal attempts. When uncertain, use the permitted preview rather than stopping immediately. Before a voluntary no-clear-progress stop, use at least one preview and make at least three legal plays across three turns. If you can still name a visible next improvement, continue up to the eight-turn cap. After three turns, you may stop honestly when no simple useful direction remains. This minimum avoids treating instant refusal to engage as game difficulty.

Do not pretend a planning stop proves impossibility. Record the specific observable obstacle: no clear next move, too many possible corrections, preview budget spent, invalid shape, or key operation unavailable. If you hit the two-candidate limit without making a legal play, stop; do not bypass the mandatory-operation rule. If the current turn has a legal play and you continue, use end-turn. The turn-8 cap is enforced after playing in turn 8 and ending it; reaching the start of turn 8 alone is not exhaustion.

All matrix indexes start at zero. A red row stays a row, a red column stays a column. Red cards are discarded whole after any use; you cannot borrow two rows from one physical card in separate plays unless legitimately redrawn. Shifts add ±1 to EVERY entry, not only the diagonal. LU requires square shape and nonzero first n−1 elimination pivots, with no swaps inside the operation. Choose L or U. Interchange needs two distinct indices. Append only extends the bottom/right, maximum dimension 4.

## Commands

Run from the GameTrix directory. Use the shell only for these commands and to write your final short review in your assigned path; do not use the shell as another calculator.

```sh
python3 student_play.py start student_tests/NEW_CASE.json --seed 101 --objective C01 --blue B01
python3 student_play.py show student_tests/YOUR_CASE.json
python3 student_play.py plan student_tests/YOUR_CASE.json --operation O27 --note "Transpose to the required wide shape."
python3 student_play.py preview student_tests/YOUR_CASE.json --plan 1
python3 student_play.py play student_tests/YOUR_CASE.json --plan 1
python3 student_play.py end-turn student_tests/YOUR_CASE.json
python3 student_play.py stop student_tests/YOUR_CASE.json --note "No clear correction within the candidate budget."
```

Plan returns a plan ID. Use the actual operation ID in hand, not the example O27. Plans are valid only for the matrix/turn in which they were recorded. A preview is optional; a clearly understood move can be committed directly. Each new candidate needs a new plan. One may preview candidate 1 and then commit candidate 2 without preview. Do not try to preview every branch.

For operations requiring arguments, put them on `plan`:

- Whole matrix add/subtract/multiply: `--red Rxx`.
- Add/replace vector: `--red Rxx --axis row|column --source N --target N`.
- Append: `--red Rxx --axis row|column --source N`; no target.
- Interchange: `--axis row|column --i N --j N`.
- LU: `--factor L` or `--factor U`.
- Transpose, inverse and printed constants need no red card.

At the end, write a brief review listing results, whether each decision had an obvious visual aim, where you became stuck, and any uncertainty about this protocol. Do not supply hidden chain-of-thought or a long reconstructed proof. Do not revise the budget, change a seed, restart a failed case, or replace a hard case.
