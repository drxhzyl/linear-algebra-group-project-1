# Bounded-intuition review: expanded02 and expanded05

| Session | Outcome | Turns reached | Plays / candidates | Candidates by turn | Previews |
|---|---|---:|---:|---|---:|
| expanded02 | won | 4 | 5 / 5 | 1, 1, 2, 1 | 0 |
| expanded05 | turn_limit | 8 | 11 / 11 | 2, 2, 1, 1, 2, 1, 1, 1 | 0 |

Both were played once without resets. Every ended turn had a legal operation. There were no rejected candidates, shape errors, or observed arithmetic errors. No outside calculations or full-matrix previews were used.

expanded02: All five moves had concrete local purposes. A tweak raised the low bottom row; replacing that row with a visible unit row gave an immediate understandable improvement. Two middle-row tweaks reduced the first-column excess and restored that row sum. Adding the visible red row [-1, 0, 1] to the bottom row preserved its sum and produced the verified win. The initial bottom-entry tweak was overwritten by replacement, so that first small improvement did not persist individually. The later row and column improvements did persist. No stall moves or shape waiting occurred.

expanded05: Multiplication immediately obtained the required non-square shape. Negative-entry tweaks and adding an existing positive row made the deficient rows easier to understand. The all-one top row was especially legible: adding it to the middle row brought that row to the required sum. Later paired tweaks redistributed one unit between middle-row columns. These improvements mostly persisted, but raising the bottom second entry on turn 6 improved a column while breaking the previously completed bottom-row sum. Column balance still required work. Turns 7 and 8 used explicitly marked [stall] swaps, preserving the existing sum information while waiting without a clear improvement. There was no waiting for shape cards because the first play already gave a permitted shape. The session reached the fixed cap after a legal turn-8 play and end-turn.

The cap is an observation about this bounded run, not evidence of mathematical impossibility or a measure of real student ability. Large retained hands made selective local actions easier to justify than broad comparisons, but they did not guarantee a clear next move.
