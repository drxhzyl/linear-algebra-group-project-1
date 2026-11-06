# Rectangular objective playtest review

Player: `play_rectangular`. All six preassigned rectangular cases were played with their manifest seeds, starting cards, modes, and caps. Every case won. These are deliberate human-style agent attempts using the dealer/calculator, not solver searches. Draw-mode planning used only CLI-visible hands; no failed seeds were replaced and no hidden draw order was read.

| Case | Mode | Seed | Blue / objective | Result | Operations | Turn at win | Final shape |
|---|---|---:|---|---|---:|---:|---|
| rect01 | draw | 301 | B01 / C11 | won | 4 | 3 | 3×2 |
| rect02 | open | 302 | B02 / C12 | won | 4 | 1 | 2×3 |
| rect03 | draw | 303 | B03 / C13 | won | 10 | 7 | 4×3 |
| rect04 | open | 304 | B04 / C14 | won | 5 | 1 | 2×3 |
| rect05 | open | 305 | B05 / C11 | won | 2 | 1 | 3×2 |
| rect06 | draw | 306 | B06 / C14 | won | 11 | 7 | 2×3 |

Draw mode: 3/3 wins, mean 8.33 operations and 5.67 turns among these wins. Open mode: 3/3 wins, mean 3.67 operations; the single-turn labels merely mean the finite deck was available together. Open results are resource-feasibility experiments and cannot estimate ordinary game length. The sample is exploratory and selected by the manifest, with no estimate of population win rates or opening-win frequency.

## Case details

### rect01: orthogonal columns, draw

Turn 1 added R04 = −I using O05, simplifying the first column to a coordinate vector. Turn 2 swapped rows 0 and 2 with O32, preserving column dot products while obtaining the next legal draw. Turn 3 used O11 × R18 to reach columns (−2,−2,2) and (−3,3,2), whose dot product was 4. O17 then added R13 column 0, (1,1,0), to column 1. Its dot product with the first column is −4, exactly removing the discrepancy.

Final matrix: `[[−2,−2],[−2,4],[2,2]]`. Column Gram matrix is diag(12,24), and every row is nonzero. Four operations over three turns; all arithmetic integral. The row swap was a resource-preserving waiting move, not a claim of progress on orthogonality by itself.

### rect02: orthogonal rows, open

O11 × R16 reduced the matrix from 3×3 to 3×2. O25 replaced column 0 with R18 column 1 = (1,0,1). O26 replaced column 1 with R03 column 1 = (0,1,0). O27 transposed the resulting orthogonal columns into rows.

Final matrix: `[[1,0,1],[0,1,0]]`, with row Gram matrix diag(2,1), no zero columns, and the required wide shape. Four finite-deck operations, consuming both replacement copies and three distinct red cards. This establishes a short available-card construction for this case only; it is not a random-hand finish rate.

### rect03: rectangular balance, draw

Turn 1 appended R23 column 0 = (1,0,−1) using O21, reaching 3×4. Turn 2 transposed with O29 to 4×3. Turn 3 swapped rows 0 and 3 with O31 while retaining correction resources. On turn 4, O26 replaced column 1 with R26 column 2 = (−1,0,0,1); O25 replaced column 2 with R05 column 1; and O20 added R06 column 3 to that column. The result `[[1,−1,0],[−1,0,1],[0,0,0],[0,1,−1]]` had every row sum and column sum zero.

A +1 shift at this point would have removed every negative entry and failed the objective. Turn 5 negated with O37 and turn 6 swapped rows 0 and 1 with O32, both preserving zero margins. Turn 7 drew multiplication O12. Right multiplication by R14 preserved zero row sums because all R14 row sums equal −1; zero column sums were also preserved. It produced `[[0,0,0],[1,2,−3],[0,0,0],[−1,−2,3]]`. O33 then added one to every entry.

Final matrix: `[[1,1,1],[2,3,−2],[1,1,1],[0,−1,4]]`. Every row sums to 3, every column to 4, and negative entries remain. Ten operations over seven turns. Arithmetic stayed integral and small; the strategic burden was coordinating both margins and preserving the negative-entry requirement. This route used an append for expansion rather than a width-reducing product. Three neutral-to-the-margin waiting operations affected turn count. No deadlock occurred, and a later-drawn product completed the plan.

### rect04: zero-sum orthogonal rows, open

O11 × R16 reduced to 3×2, and O27 transposed to 2×3. O25 replaced row 0 with R15 row 0 = (1,−1,0). O26 replaced row 1 with R14 row 1 = (0,1,−2). O16 added R03 row 0 = (1,0,0) to row 1.

Final matrix: `[[1,−1,0],[1,1,−2]]`. Both row sums are zero, their dot product is zero, row squared lengths are 2 and 6, and every column is nonzero. Five operations and four consumed red cards. This uses all two replacement cards but stays within the finite eight-move budget. Arithmetic burden was low.

### rect05: orthogonal columns, open

O11 × R16 produced `[[0,1],[2,−1],[0,−1]]`. O25 replaced column 0 with R18 column 1 = (1,0,1). This already completed the goal, earlier than the provisional two-replacement plan.

Final matrix: `[[1,1],[0,−1],[1,−1]]`. Column squared lengths are 2 and 3 and the dot product is zero. Two operations, two consumed red cards, and no zero rows. One queued follow-up play was rejected by the CLI because the session had already won; it did not change the session or consume cards.

### rect06: zero-sum orthogonal rows, draw

Turn 1 transposed with O28, exposing three equal row sums of 2. Turn 2 added −I with O03/R04, lowering those sums to 1. An initial calculator-only attempt to take L before that correction failed because a required earlier pivot was zero; no card was played or consumed by the calculator.

Turn 3 O13 × R18 reduced to 3×2. Turn 4 negated with O37 and turn 5 doubled with O38, keeping the reduced shape while waiting for another transpose. Turn 6 O29 produced `[[−4,2,−4],[2,−4,2]]`, a wide matrix but still short of the algebraic goal. No replacement card had appeared by turn 7, so the plan changed.

On turn 7 O12 × R16 produced `[[−6,−4],[6,2]]`. Both Doolittle pivots were nonzero. O40 selected L = `[[1,0],[−1,1]]`. O22 appended R02 column 0 = (−1,0), giving `[[1,0,−1],[−1,1,0]]`. O20 added R11 row 0 = (2,−1,0) to row 1, then O17 added R12 row 1 = (0,−2,1).

Final matrix: `[[1,0,−1],[1,−2,1]]`. Both rows sum to zero, their dot product is zero, squared lengths are 2 and 6, and no column vanishes. Eleven operations over seven turns. The final five operations occurred within one turn, demonstrating why operations and turns need separate metrics. No replacement cards were used. The successful route had only integer results, despite LU being capable of introducing fractions. The early waiting operations became unnecessary to the eventual L construction, so this is a successful attempt rather than a minimal solution certificate.

## Shaping, deck quotas, and appendix observations

- Right products, transpose, and append all mattered. A 3×2 red can reduce a 3×3 current matrix immediately; transpose then exposes two rows. Append supplied the final dimension in rect06 and expanded the balance case in rect03. Merely enlarging a matrix did not establish orthogonality or balance.
- The 30-red quota supplies three each of 2×3/3×2 and 3×4/4×3, but only two each of 2×4/4×2. The 3×3 emphasis made the initial square hands usable, while moving away from 3×3 narrowed same-shape addition/subtraction choices. Retaining unused cards prevented those initially unusable rectangular operands from being wasted.
- Signed identities were especially useful as oriented unit-vector supplies: R03 completed rect04, R05 and R06 built balance margins, and R02 supplied the appended length-two column in rect06. A length-three row was never treated as a column, and all source/target indices were zero-based.
- Only two replacement copies exist. Both were consumed by rect02, rect03, and rect04. Rect05 needed just one; rect01 used a correction instead. Rect06 solved without drawing any replacements, through a second reduction, LU, append, and additions. This is concrete evidence of alternative routes, not a universal reachability result.
- The appendix's interaction notes were borne out: transposition transfers column orthogonality to row orthogonality; appending changes dot products; the zero-sum condition adds work beyond C12; and a rectangular balance solution needs compatible totals mn plus a negative entry. A zero-margin matrix plus the all-ones matrix is a useful balance construction, but only if the zero-margin part has an entry below −1.
- The appendix asks for universal per-blue/objective certificates initially within six operations before reshuffling. These six plays do not certify that requirement: rect03 and rect06 took more than six operations, though each open case finished within five. Their successful longer attempts cannot establish that shorter paths do not exist.
- No legal-action deadlock, exhaustion stop, cap, or unresolved path remained in these six cases. That does not prove every possible deal is playable. All ended turns had at least one accepted operation, all unused cards were retained, and no rescue draw or free pass was used. Draw-mode red recycling appeared by turn 7; operation cards had not exhausted. Open mode had no recycling.
- Arithmetic verification was manageable: low-dimensional integer products and dot products, one successful 2×2 LU, and explicit row/column-sum checks. Hand management and route selection were more demanding than arithmetic. Exact CLI previews were used at critical products and finishes, and every played move carries a rationale in its JSON log.
