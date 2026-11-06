# Bounded student play review

Both assigned cases were attempted once using only student_play.py after reading PROTOCOL.md. Neither was won. Both stopped voluntarily after three legal plays in turns 1, 2, and 3; this is a planning limit, not evidence of impossibility.

| Case | Result | Candidates by turn | Previews by turn | Legal plays |
| --- | --- | --- | --- | --- |
| student11 / Rectangular Balance | stopped, turn 3 | 1, 1, 1 | 0, 1, 0 (1/6 total) | 3 |
| student12 / Zero-sum Orthogonal Rows | stopped, turn 3 | 1, 1, 1 | 0, 1, 0 (1/6 total) | 3 |

The wrapper outputs showed these budgets. No candidate was rejected, and neither per-turn limit was reached.

For student11, the visible aims were to append a column for a rectangle, raise low entries, then improve the second row using a row of sum two. There was apparent progress: the final shape was 3 by 4, a negative entry remained, and the second row correction was useful. I became stuck because balancing the remaining rows and columns seemed to require several coordinated corrections; I could not name a simple next improvement in the retained hand.

For student12, the aims were to reduce a negative row deficit, explore lowering the positive rows, and append a column to get a wide shape while making the second row sum zero. The preview made clear that the global shift worsened the first row even while helping the positive rows. Progress was mixed: the final shape was 3 by 4 and the second row had zero sum, but the other rows still needed work. I did not see a simple operation that would improve those sums and orthogonality together.

The difficult point was judging useful local corrections when each objective imposed several simultaneous conditions. No source, hidden draws, previous games, external calculations, scripts, full manual matrix previews, or advanced target constructions were used. No known protocol deviations. Gameplay ended via stop after the third turn's legal operation; no new turn was drawn just to stop.
