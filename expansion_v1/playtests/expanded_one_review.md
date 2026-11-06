# Bounded-intuition review: expanded01 and expanded04

Both assigned sessions were played once through student_play.py, without resets, source/deck inspection, or prepared routes. Each ended turn had a legal play. No plays were rejected and no arithmetic or shape mistakes were observed.

| Session | Outcome | Legal plays / candidates | Candidates by turn | Previews |
| --- | --- | --- | --- | --- |
| expanded01 | Won on turn 4 | 5 / 5 | 1, 1, 2, 1 | 0 |
| expanded04 | Won on turn 6 | 7 / 7 | 1, 1, 1, 1, 1, 2 | 1 (turn 5) |

expanded01: All five moves had an immediate visible purpose: match reflected entries using zeroing and unit tweaks. Each repaired pair remained repaired. The final edit completed symmetry and the wrapper verified the invertible, non-diagonal goal. No stalls or shape waiting were needed. Ending early turns after a useful edit allowed further draws without disturbing the partial result.

expanded04: Turn 1 was explicitly a stall: transpose while waiting for a way to reach a permitted tall shape. Turns 2–3 reduced then cleared the remaining dot-product contribution between the first two columns. Turn 4 appended a nonzero row with zeros in the other two positions, reaching 4×3 while retaining that local progress. Turn 5 added the first column into the third to cancel two visible minus twos; the one preview confirmed the cancellation. Turn 6 used two unit tweaks to make the top and bottom contributions cancel. The wrapper verified victory. Useful local progress persisted after the initial stall, including through the shape change.

These are two bounded agent sessions, not a measure of real student ability or a general reachability result.
