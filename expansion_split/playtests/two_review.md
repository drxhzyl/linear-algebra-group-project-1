# Bounded-intuition sessions: split02 and split05

Only PROTOCOL.md and the student_play.py interface were consulted. Sessions were continued once without resets or reseeding.

| Session | Outcome | Legal plays | Candidates per turn | Previews |
|---|---|---:|---|---:|
| split02 | Won on turn 4 | 5 | 1, 1, 2, 1 | 0/6 |
| split05 | Turn-8 cap | 9 | 1, 2, 1, 1, 1, 1, 1, 1 | 1/6 (turn 1) |

Both stayed within two candidates per turn and one preview per turn. No rejected plays, shape errors, or noticed arithmetic errors occurred. Every ended turn included a legal play. Every committed plan had a concrete local aim and was marked [progress]; no purely exploratory [stall] move was used.

split02: An initial +1 reduced a negative entry. Replacing the bottom row made its sum one, although that replacement superseded the first move's entry improvement. A minus/plus pair then moved one unit toward the empty middle column while restoring the second row sum. A red row addition transferred one unit from the first column to the third without changing the bottom row sum. The final matrix was [[0,0,1],[1,1,-1],[0,0,1]], and the referee verified victory. These later local improvements persisted. The first turn offered plus but no minus; the second offered minus but no plus, and the chosen row replacement avoided relying on the unavailable sign. Having both signs on turn 3 enabled the paired adjustment.

split05: A previewed right multiplication reached 3x4 immediately, so there was no wait for a shape-changing card. Adding the bottom row to the top and then using +1 made the top row all ones. Further additions raised the deficient second row. However, reducing the oversized first column with minus cards repeatedly worsened that row's sum. On turns 5, 7, and 8, plus was absent while minus was present; I chose the visible column correction instead of a positive entry correction. These were progress toward one local condition, but functioned as waiting with respect to the missing positive correction. The top row and permitted shape persisted; simultaneous row/column balance did not emerge. Final matrix: [[1,1,1,1],[1,0,-1,1],[1,0,2,1]]. It retained a negative entry and achieved the first-column target, while the second row remained deficient.

The split fixed signs affected the available local choices, particularly late in split05. This observation does not establish that a different sign would have produced a win. The cap is not evidence of mathematical impossibility, and these agent sessions do not measure real student ability.
