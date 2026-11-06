# Fixed-horizon, limited-calculation playtest

You are testing whether a game affords understandable local decisions for a linear algebra student. You are not a solver and are not trying to prove reachability. Use basic matrix addition, multiplication, transpose, simple row/column edits and the operation descriptions. Do not use eigenvalue/minimal-polynomial/companion-matrix constructions or a memorized general target template.

Read ONLY this protocol, then use ONLY `student_play.py` for your two assigned sessions. Do not inspect source code, deck files, raw session JSON, previous reports, other agents' games, or future draw order. No search scripts, extra calculators, external references, or unrecorded full-matrix manual calculations. Simple comparison of entries, dimension matching, one row sum or dot product is allowed; do not enumerate every card/vector/combination.

The game starts with a 3×3 blue matrix. Each turn draws 3 operation cards and 5 red matrix cards. Retain all unused cards. Every ended turn must include at least one legal operation; multiple plays are allowed. A verified win ends immediately. Matrix dimensions must remain 2–4; exact fractions are permitted. All indices start at zero. Red cards are discarded whole after use.

## Attention and calculation budget

- At most TWO candidate proposals in each turn, including unused or illegal candidates. Pick one or two plausible actions, not an exhaustive list of hidden alternatives.
- At most ONE complete preview per turn, SIX previews per game. Invalid previews also count. A simple transparent move may be committed without preview. Full matrix/power/rank/determinant computations outside the wrapper are forbidden; the referee calculates a committed result for you.
- Continue until victory or the fixed EIGHT-turn / sixteen-play cap. Do not voluntarily stop because you cannot see a plan. When unclear, choose an obvious legal action with the least apparent disruption, and label it `[stall]`. This is a research requirement, not a claim that a human would persist.
- `stop` is only allowed for an actual no-legal-action hand or when both candidate slots were consumed by rejected plays and no legal action has been performed this turn. A candidate-budget lock is an experimental stop, not a game deadlock.
- Do not reset, reseed, copy a route from elsewhere, or revise the rules. If you win on a play, do not send more actions. On turn8, play then end-turn to trigger the cap; merely arriving at turn8 does not end the experiment.

Prefix every plan note with `[progress]` when you can name a concrete visible aim (clear this entry, match this pair, improve this row sum, get a permitted shape). Use `[stall]` for an exploratory/waiting move with no clear objective improvement. A short rationale is enough; no chain-of-thought. This label records perceived purpose, not proven mathematical progress.

## Operations

Use actual physical IDs from the hand. Some operation types may not be present in a particular deck/hand. Do not infer anything about expected difficulty from which cards appear.

- `entry_tweak`: choose `--i ROW --j COLUMN --delta 1` or `--delta -1`. Adjust just that entry. Supply `--red Rxx`: ANY red card is consumed as fuel, independent of its shape or values.
- `entry_plus`: choose `--i ROW --j COLUMN --red Rxx`. Add exactly1 to that entry; the sign is fixed on the card. Do not pass --delta.
- `entry_minus`: choose `--i ROW --j COLUMN --red Rxx`. Subtract exactly1 from that entry; the sign is fixed on the card. Do not pass --delta.
- `entry_zero`: choose `--i ROW --j COLUMN --red Rxx`. Set just that entry to zero; any red card is fuel.
- `combine_vectors`: choose `--axis row|column --source S --target T --delta 1|-1`. Source and target are DISTINCT existing rows/columns of your current matrix. Add/subtract the source into the target, keep the source. NO red card.
- `add` / `subtract`: `--red Rxx`, whole red matrix must have identical shape.
- `multiply`: `--red Rxx`, multiply on the right; inner dimensions must match. Result dimensions remain2..4.
- `add_vector` / `replace_vector`: `--red Rxx --axis row|column --source S --target T`; source vector comes from the RED card and target from your current matrix. Equal length, same orientation. Red discarded whole.
- `append_vector`: `--red Rxx --axis row|column --source S`; no target. Append red row below or column to the right, up to dimension4.
- `swap`: `--axis row|column --i I --j J`, two distinct indices.
- `transpose`: no red/extra parameters.
- `shift_plus` / `shift_minus`: every entry±1, NOT addition/subtraction of identity.
- `negate` / `double`: every entry×(−1) or×2.
- `inverse`: square and invertible; no red. Keep fractions exact.
- `lu`: square, Doolittle without swapping, first n−1 pivots nonzero. `--factor L` or `--factor U`; no red.

## Commands

Run from the GameTrix directory. Shell use is limited to these commands, reading this protocol, and writing your assigned brief review. The sessions are already created; do not start replacements.

```sh
python3 student_play.py show expansion_v1/playtests/YOUR_CASE.json
python3 student_play.py plan expansion_v1/playtests/YOUR_CASE.json --operation Oxx --red Rxx --i 0 --j 1 --delta -1 --note "[progress] Reduce the mismatch in this reflected pair."
python3 student_play.py preview expansion_v1/playtests/YOUR_CASE.json --plan 1
python3 student_play.py play expansion_v1/playtests/YOUR_CASE.json --plan 1
python3 student_play.py end-turn expansion_v1/playtests/YOUR_CASE.json
python3 student_play.py stop expansion_v1/playtests/YOUR_CASE.json --note "Both candidate plays were rejected; decision budget exhausted this turn."
```

Use the returned plan ID; it is valid only at that turn and current matrix. After committing a play, a further action needs a NEW plan against the new matrix. A second old candidate is stale. The preview is optional and shows only the resulting matrix, not free rank/determinant/partial-goal feedback. A plan is consumed on a play attempt even if rejected.

Finish both sessions. In the review record results, previews/candidates used, which moves had an obvious local purpose, when you stalled or waited for shape-changing cards, any arithmetic/shape error, and whether visible progress persisted. Do not claim a cap means mathematical impossibility or that an agent's result measures real student ability.
