# Bounded-intuition review: split01 and split04

Both precreated sessions finished once with verified wins. No resets, previews, rejected plays, arithmetic mistakes, or shape errors occurred. Each plan was committed; no exhaustive comparisons or full-matrix calculations were used.

| Session | Outcome | Legal plays / candidates | Candidates by turn | Previews |
|---|---|---:|---|---:|
| split01 — Mirror Match | Won on turn 4 | 5 / 5 | 1, 1, 2, 1 | 0 / 6 |
| split04 — Orthogonal Columns | Won on turn 5 | 6 / 6 | 1, 1, 1, 2, 1 | 0 / 6 |

All moves were marked `[progress]`; there were no `[stall]` moves or experimental stops. Every ended turn contained a legal play. The maximum was two candidates in a turn, within the prescribed limit.

In split01, an entry-zero card matched the top-right/bottom-left pair. A plus card then matched the other top pair. Clearing the negative entry in the remaining pair and raising it once left a 2-versus-1 mismatch; the next turn's minus card lowered the 2 to 1. The referee verified the resulting symmetric matrix as a win. The visible pair matches persisted through the remaining edits. Fixed signs affected the final choice: plus was unavailable on turn 4, so I changed the opposite member of the pair with minus instead of raising the 1.

In split04, two plus cards removed the bottom contribution to the last two columns' dot product. A minus card then made the first two columns cancel in their dot product. The matrix remained square until an append-row card arrived on turn 4; I kept making local entry improvements while waiting. Appending a nonzero row reached 4×3 without disturbing the first two columns. Entry-zero removed one third-column overlap, and adding the negative-two-only row into the remaining overlapping row cleared the other. The first two columns stayed orthogonal after turn 3, and the referee verified the final tall matrix as a win. The intermediate dot-product improvement was local, not a monotone measure of the whole objective. Available plus cards supported raising negative entries early; the later minus supported lowering the positive entry. No turn stalled specifically because one sign was unavailable.

These are two bounded play observations, not evidence about mathematical reachability in general or real student ability.
