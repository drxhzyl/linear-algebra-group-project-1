# Limited-calculation formal-core review

Both cases were attempted once through student_play.py and stopped after three legal plays in three turns. Neither won. These are bounded agent observations, not evidence of human difficulty or impossibility.

| Case | Result | Candidates by turn | Previews by turn | Legal plays |
| --- | --- | --- | --- | --- |
| student07, Mirror Match | Stopped in turn 3 | 1, 1, 1 (3 total) | 1, 0, 1 (2/6 total) | 3 |
| student08, Two-way Balance | Stopped in turn 3 | 2, 1, 1 (4 total) | 1, 1, 0 (2/6 total) | 3 |

student07: Subtracting R11 made the opposite corner entries match. Adding a column then moved one reflected entry toward its partner. The third-turn row swap was exploratory and preserved the matched corners, but did not show convincing further progress. Two other reflected pairs still differed, with no simple next correction apparent in the current hand. The main difficulty was making a local match without disrupting another one; invertibility was not separately calculated.

student08: The first proposal mistakenly used a length-4 red row for a length-3 target; the preview rejected it and consumed the preview allowance. The second proposal legally raised the bottom middle entry. Turn 2 subtraction raised two bottom entries but also disturbed the upper rows, so its benefit was mixed. Turn 3 subtraction restored visibly balanced first and second rows. The bottom row remained strongly negative, and no simple correction preserving the upper rows was apparent. Keeping row and column source lengths straight was the concrete point of confusion.

Each candidate had a short recorded visible aim; the exploratory moves were not claimed as guaranteed improvements. The wrapper outputs showed no turn exceeding two candidates or one preview, and both games used only two of six previews. No source, hidden draws, other sessions, solver, external calculations, reseeding, reset, or advanced construction was used. No known protocol deviations; the rejected length mismatch was an ordinary budgeted gameplay error. Stops were voluntary planning limits after the required participation, not claims that the goals were impossible.
