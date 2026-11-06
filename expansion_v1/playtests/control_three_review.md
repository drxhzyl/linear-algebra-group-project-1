# Bounded-intuition control03 and control06 review

Only PROTOCOL.md and student_play.py output were read. Both assigned sessions were played once without reset, source/deck inspection, scripts, full-matrix calculations, or supplied routes. Candidates were committed directly; no previews were used.

| Session | Result | Turns reached | Legal plays / candidates | Previews | Rejected |
|---|---|---:|---:|---:|---:|
| control03 | won | 7 | 7 / 7 | 0 / 6 | 0 |
| control06 | turn_limit after ending turn 8 | 8 | 9 / 9 | 0 / 6 | 0 |

All turns used one candidate except control06 turn 2, which used two. Every ended turn included a legal play. Neither session used stop.

## control03: Projection

The first two moves were stalls: a simple square multiplier, followed by identity multiplication. The first multiplier introduced a minus-three entry, so this exploration did not visibly improve the objective. Turns 3–7 had concrete local aims: clear the last top-row entry, reduce both minus-three entries, cancel the first entry of row one, clear the minus-one entry of row two, then restore an independent nonzero top row. The wrapper verified victory at turn 7 with rows [1,0,0], [0,1,-2], [0,0,0]. Five moves were labeled progress and two stall.

The local zeroing and small-entry aims became understandable before the whole projection condition did. Clearing row two temporarily left just one nonzero row, so fewer nonzero entries alone was not sufficient. A later unit-row addition restored the required independence. No arithmetic or shape rejection occurred; there was no need to change shape.

## control06: Zero-sum Orthogonal Rows

Five moves had local progress labels: raise the negative top-row sum, make the reoriented top row sum zero, append a unit column to reach 3x4 and repair row one, repair the remaining row sum with a unit-column addition, and reduce the first-entry pair mismatch of row zero while retaining its zero sum. Four moves were stalls: transpose while waiting for a shape card, identity multiplication, column swap, and final identity multiplication.

The wide shape arrived on turn 3. All row sums reached zero on turn 4 and remained zero through the cap, with no zero columns or zero rows. Orthogonality still failed; for example, the final top and bottom rows have dot product 2. The final rows were [0,-2,1,1], [-1,-1,1,1], [1,-1,0,0]. The last local edit preserved the visible achievements but did not finish the objective. No arithmetic or shape errors were rejected.

Shape compatibility narrowed obvious choices: after reaching 3x4, many retained square red cards could no longer be added, while available append cards could not add a fifth column. Identity and column swaps made legal waiting moves possible but provided no objective improvement. The cap records this bounded attempt, not mathematical impossibility or real student ability.
