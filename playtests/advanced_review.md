# Advanced playtest review

Player: `play_advanced`. All six preassigned cases were started once with the manifest's objective, blue card, seed, mode, and caps. Plans were supplied manually through CLI operations, with intent notes. No search solver, reseeding, hidden draw-order inspection, or failed-case replacement was used. Draw hands were inspected through CLI output. Every end-turn followed at least one operation; unused cards were retained.

| Case | Objective / blue | Mode / seed | Result | Operations | Final turn |
| --- | --- | --- | --- | ---: | ---: |
| advanced01 | C05 / B07 | open / 201 | won | 5 | 1 |
| advanced02 | C06 / B08 | draw / 202 | stopped, unresolved | 7 | 8 |
| advanced03 | C08 / B09 | open / 203 | won | 6 | 1 |
| advanced04 | C09 / B10 | draw / 204 | won | 5 | 5 |
| advanced05 | C10 / B11 | open / 205 | won | 6 | 1 |
| advanced06 | C08 / B12 | draw / 206 | won | 7 | 7 |

Open experiments: 3/3 wins, mean 17/3 operations (5.67), all in turn 1 because the finite deck is already in hand. Draw experiments: 2/3 wins; winning mean 6 operations and 6 turns. The unresolved involution attempt is excluded from winning averages. These exploratory, deliberately planned cases do not estimate population success rates or normal game length.

## Strategies and observations

- **advanced01, skew symmetry:** The first attempted LU was rejected because the second pivot was zero; no card was consumed. A row swap made LU legal. Choosing L, subtracting identity, and replacing the last two rows produced `[[0,0,0],[0,0,1],[0,-1,0]]`. The program verified nonzero skew symmetry. The zero-pivot restriction is real even when the starting matrix is invertible.
- **advanced02, involution:** The retained-hand plan isolated the third coordinate, maintained an admissible 2x2 block, and sought LU followed by a row replacement to produce a triangular reflection. An inverse introduced exact sixths and halves. Neither LU nor a second replacement operation arrived through the turn-8 draw. Final matrix: `[[1/6,1/2,1/6],[3/2,1/2,1/2],[0,0,-1]]`. Legal operations remained; this was a strategic stop after no short justified alternative was found, not a blocked hand and not a proof of unreachability. The run was stopped before any turn-8 operation, without claiming a free pass or a cap-triggered result.
- **advanced03, rank-two projection:** Normalize the first row, then multiply by R13 to get a rank-one idempotent P. Its complement I-P is a non-diagonal rank-two projection. I mistakenly used the entrywise +1 card as though it added identity; that played mistake remains recorded, and was reversed with entrywise -1 before subtracting the -I card. Final `[[0,0,0],[3,1,0],[0,0,1]]` passed the exact check in six operations. The underlying intended construction needs four, but that shorter result was not played and is not counted.
- **advanced04, nilpotency index three:** Multiplication by R20 produced the sparse 3x2 rectangle `[[0,1],[0,1],[0,0]]`. A vector addition zeroed its middle row; doubling preserved the sparse chain while waiting for an append card. Appending column 1 of retained R21 completed `[[0,2,0],[0,0,1],[0,0,0]]`. Its square has a nonzero (0,2) entry and its cube is zero, as verified by the program. Strategic retention of the append vector mattered.
- **advanced05, order three:** Reduce to 3x2, transpose to 2x3, and multiply back to 2x2. Two row replacements and one vector addition constructed `[[-1,-1],[1,0]]`, the companion matrix of x²+x+1. It cubes to identity and has two nonzero entries in its first row, so it is not a signed permutation. The program verified both conditions. The intermediate 2x2 matrix was singular; row replacement restored rank.
- **advanced06, projection in draw mode:** Reduce to 3x2 and append a zero column to preserve a rank-two scaffold. Row additions normalized the first row and cleared the middle first-column entry, and transpose oriented the scaffold as `[[1,0,1],[0,-3,0],[0,0,0]]`. Two +2 vector additions, the second using the legitimately redrawn R12 after red discard recycling, completed `[[1,0,1],[0,1,0],[0,0,0]]`. No replacement operation was needed. The exact rank and idempotence checks passed.

## Arithmetic, rank, and dimension limits

All played matrices stayed at most 3x3; temporary rectangles were 3x2 or 2x3. No run approached the dimension-4 bound. Maximum absolute entry across the played trajectories was 4, in advanced03's mistaken entrywise-shift intermediate. Only advanced02 introduced fractions; its largest denominator was 6. Thus these particular routes avoided arithmetic explosion, though inversion and LU can create fractions in otherwise small integer positions.

Useful constraints were distinguished from unsuccessful plans: an odd-dimensional real skew-symmetric target must be singular; a 3x3 matrix of nilpotency index three has rank two; and rank two alone does not establish projection. Right multiplication cannot restore lost rank, whereas appending and row replacement did restore rank in these runs. A 2x2 shape cannot satisfy C08 or C09, so those runs kept three rows when shrinking columns. C10 permits 2x2, making the companion-block route economical. Triangular real order-three matrices would have all diagonal entries one and cannot supply the desired nontrivial order-three block; the played C10 construction deliberately used a nontriangular block.

The five winning final states were exactly checked by the program. No impossibility result is claimed for advanced02, for other deals, for shorter operation budgets, or for universal reachability of the blue cards.
