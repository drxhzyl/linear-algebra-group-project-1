# Limited-calculation student playtest

Both assigned cases were tried once, without reset or reseeding. Only PROTOCOL.md and student_play.py gameplay output were consulted. These are bounded agent observations, not evidence of human difficulty or mathematical impossibility.

| Case | Objective | Result | Legal plays / turns | Proposed candidates by turn | Previews by turn |
|---|---|---|---|---|---|
| student09, seed 206 | Projection | Voluntary stop, no win | 3 / 3 | 2, 1, 1 | 1, 0, 0 (1/6 total) |
| student10, seed 301 | Orthogonal Columns | Voluntary stop, no win | 3 / 3 | 1, 1, 1 | 0, 1, 1 (2/6 total) |

The displayed wrapper budgets stayed within two candidates and one preview per turn. No illegal plays occurred. Neither eight-turn nor sixteen-play cap was reached.

## student09

Turn 1 explored a sparse square multiplier with one preview, then used the second candidate to reduce a visible -3 entry to -2 by addition. Turn 2 moved the sparse row containing a 1 into the middle diagonal position. Turn 3 added a visible row to clear the last row's -1 off-diagonal entry and reduce its last entry toward zero. The final displayed matrix was [[2,-2,-1],[0,1,0],[0,0,-1]]. There was apparent local simplification, especially in the last row, but no demonstrated progress on the full projection condition. I could not see a simple useful correction toward A²=A using the remaining operations. The difficult point was relating a local entry improvement to the whole-matrix objective without a large calculation.

## student10

Turn 1 appended a nonzero row to reach 4×3, using opposite signs as a simple balancing cue. Turn 2 cleared one first-column entry to reduce overlap with the third column; a preview confirmed the local effect. Turn 3 previewed and committed a sparse multiplication to reduce the matrix to 4×2. The final displayed matrix was [[2,3],[-1,2],[-2,-2],[-1,1]]. The required tall shape was reached and the number of column pairs was reduced, but the referee did not report a win. With no vector edit remaining in the visible operation hand, I could not name a simple next correction to obtain orthogonal columns. The confusing point was that clearing overlap for one pair could disturb a previously useful balance elsewhere.

## Protocol notes

No known gameplay deviations: no external calculations, source/deck inspection, hidden draws, general target construction, or card/vector enumeration. Each turn had a short observable aim; some aims were exploratory and did not prove objective progress. The wrapper repeats the visible hand after commands; decisions used the initial turn state and resulting play/preview, without extra show calls. Stops occurred after a legal play on turn 3, using the stated minimum of three legal plays across three turns. Neither stop claims impossibility.
