# Core playtest review

All six manifest `group=core` cases were played with their assigned seed, objective, blue card, mode, and caps. Draw-mode decisions used only visible hands through `show`; no hidden draw order was inspected. Calculations and checks were exact. Open-mode outcomes are resource experiments and are not comparable to draw-mode turn counts.

| Case | Mode | Outcome | Moves / last turn reached | Result |
|---|---|---|---:|---|
| core01 — C01 Mirror Match | draw | unresolved; stopped at start of turn 8 | 7 / turn 8 | Invertible, still asymmetric |
| core02 — C02+ Signed Identity | draw | unresolved; stopped at start of turn 8 | 7 / turn 8 | Closest final candidate had one `-1/2` off-diagonal |
| core03 — C02- Signed Identity | open | explicit planning stop after 2 moves | 2 / turn 1 | Two rows became `-e0` and `-e1`; remaining row unresolved |
| core04 — C03 Diagonal Diversity | open | won | 2 / turn 1 | `diag(2,-1,1)` |
| core05 — C04 Two-way Balance | draw | unresolved; stopped at start of turn 8 | 7 / turn 8 | Row sums `(1,-1,3)`, column sums `(4,4,-5)` |
| core06 — C07 Volume-Preserving Mix | open | won | 3 / turn 1 | Determinant 1 and at least two nonzeros in every row and column |

## Case notes

### core01 — C01 Mirror Match, draw

Moves: subtract R11; add R10 row 0 to row 1; add R14; transpose; add R08 row 2 to row 0; multiply by R09; add R12. The plan first repaired one asymmetric pair, then used later visible red cards and previews to reduce the remaining skew while keeping the determinant nonzero. Final matrix was `[[−2,2,2],[2,−7,−3],[3,0,−2]]`, determinant 4; off-diagonal differences remained `(0,1)=0`, `(0,2)=−1`, `(1,2)=−3`. The session was explicitly stopped at the start of turn 8 (7 moves), before taking an eighth-turn action. This is an unresolved planning stop at the assigned boundary, not an actual no-legal-action deadlock or an impossibility result. Main burden: coordinating three independent off-diagonal equalities while preserving nonzero determinant; dimensions stayed 3×3.

### core02 — C02+ Signed Identity, draw

Moves: swap rows 0 and 1; multiply by R11; add R03; multiply by R09; add R12 row 0 to row 0; add R07 row 2 to row 2; take LU factor L. The visible-card route progressively altered the entries; LU produced two exact identity rows and a final row `(-1/2,0,1)`, with determinant 1. It did not satisfy identity. The session was stopped at the start of turn 8 after 7 moves, before an eighth-turn action. This was unresolved bounded planning, not a legal-action deadlock. Exact fractions appeared only at the final LU step; dimensions stayed 3×3. The `-1/2` residue suggests that integer red vectors available in the draw hand may be the remaining obstacle for this short plan, but does not establish global unreachability.

### core03 — C02- Signed Identity, open

Moves: add R22 row 3 `(-1,1,0)` to row 0, making the first row `-e0`; replace row 1 with R04 row 1, making it `-e1`. I then stopped after noticing that the unique physical R04 card had been consumed, so the planned second replacement with that same card was unavailable. The matrix at stop was `[[-1,0,0],[0,-1,0],[1,2,0]]`, rank 2, determinant 0. This was an explicit planner stop after a card-use mistake, not a game deadlock or an impossibility result. Open mode exposed the whole finite hand; dimensions stayed 3×3. The main operational lesson is to account for single-copy physical red cards when planning repeated row replacements.

### core04 — C03 Diagonal Diversity, open

Moves: replace row 1 with R04 row 1, then replace row 2 with R03 row 2. The unchanged first row was already `(2,0,0)`, so the final matrix was `diag(2,−1,1)`: all diagonal entries nonzero, three distinct values, determinant −2. Won on move 2 in turn 1. The plan required two exact row replacements; no fractions or dimension changes.

### core05 — C04 Two-way Balance, draw

Moves: add R04; transpose; subtract R14; add R07 row 2 to row 2; add R11; add R09; multiply by R03 (unchanged). This explored row- and column-sum changes using visible cards. R07 brought one row sum to 1; R09 had total sum +4 and made row 0 sum 1. Final sums remained `(1,−1,3)` by rows and `(4,4,−5)` by columns, despite the required total sum of 3 being met. The unchanged multiplication by I3 was legal and logged; there was no no-legal-action deadlock. The session was stopped at the start of turn 8 after 7 moves, before an eighth-turn action, as an unresolved bounded plan. All matrices remained 3×3 and integer-valued. The balance condition couples row and column sums, so improving one profile can worsen the other; total-sum agreement alone is insufficient.

### core06 — C07 Volume-Preserving Mix, open

Moves: swap rows 1 and 2; take LU factor L; add R11 row 2 `(-2,1,1)` to row 0. The swap enabled LU without row swaps; `det(L)=1`. The added vector equals the sum of the other two rows of L, so the row addition preserved determinant while filling the sparse row and columns. Final matrix was `[[-1,1,1],[-1,1,0],[-1,0,1]]`; each row and column has at least two nonzeros. Won in 3 moves in turn 1. This was a compact exact plan with no fractional arithmetic or dimension changes.

## Rule and design observations

- Open mode makes useful row-replacement and LU sequences immediately available, but the results measure finite-deck feasibility, not ordinary draw-game pace.
- Red cards are physical single-copy resources. A plan that uses one red card twice must account for its consumption; core03 stopped after that assumption failed.
- LU can change the determinant materially: core06 used L to move from determinant −4 to +1, while core02's L factor produced a near-identity matrix with a fractional residue.
- A legal unchanged action is accepted and logged: core05's multiplication by R03 (I3) did not change the matrix. No case encountered a genuine state where all operations were unusable after a draw.
- The three non-winning draw cases ended at the start of turn 8 with unused actions still possible in that turn; these are planning stops at the requested cap boundary, not evidence that the objectives are unreachable.
