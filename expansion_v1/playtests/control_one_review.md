# Control sessions 01 and 04

| Session | Result | Turns | Legal plays / candidates | Previews | Illegal attempts |
|---|---|---:|---:|---:|---:|
| control01 | turn_limit | 8 | 9 / 9 | 1 | 0 |
| control04 | won | 7 | 7 / 7 | 1 | 0 |

Both followed the two-candidate and one-preview per-turn limits and six-preview game limit. Control01 used one candidate on turns 1–7 and two on turn 8. Control04 used one each turn. No resets, reseeds, external calculations, source/deck inspection, or stop commands were used.

Control01: Turn 1 transpose was a [stall] waiting for a local edit. Turns 2–8 were marked [progress], targeting reflected entries. The turn-2 note was mistaken: R17 row 1 changed the first and third entries of the top row, leaving the intended top-middle entry unchanged. This was an entry-reading error despite a legal play. Turn 3 then matched the upper reflected pair; later small additions/subtractions retained that match. Turn 5 reduced one mismatch but enlarged another. The final matrix was [[4,2,0],[2,-1,0],[0,1,-3]], so two reflected pairs matched while the remaining pair was 0 versus 1. Progress was visible but uneven. Frustration came from whole-matrix changes disturbing other pairs and having many retained cards but few transparent corrections.

Control04: Turn 1 append immediately achieved a permitted 4-by-3 shape. Turns 2 and 4 reduced an overlap contribution; turn 3 was a [stall] row swap while waiting for a useful column edit. Turn 5 replaced the third column with a visible isolated column, and turn 6 cleared the second-column entry on its support row. Turn 7 multiplication retained that isolated column while combining the first two into one, giving [[1,0],[-1,0],[0,1],[2,0]]; the wrapper verified victory. This later visible progress persisted. No shape or arithmetic error was observed. Waiting after obtaining the tall shape felt less productive than the later replacement and local clearing.

These are bounded-intuition agent sessions. The cap is not evidence of mathematical impossibility, and the outcomes do not measure real student ability.
