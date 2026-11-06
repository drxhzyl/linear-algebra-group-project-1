# Control playtest review: control02 and control05

Both precreated sessions reached `turn_limit` after eight turns and eight legal plays each. Neither won. Each used eight candidates, exactly one each turn, with zero rejected plays or invalid previews. control02 used two previews (turns 4 and 8); control05 used none. No resets, reseeds, source/deck inspection, external calculators, or hidden-draw reads were used.

## control02 — Two-way Balance

Most moves had a concrete local row-sum purpose: lifting the negative bottom row, matching the second-row sum, or reducing an oversized row. Simple right multiplication on turns 4 and 8 was previewed to confirm a column addition/subtraction. Turn 7 was explicitly `[stall]`: transpose while waiting for a targeted edit. The matrix stayed square throughout; there was no wait for shape-changing cards. Improvements were fragile: changing one row or column often displaced another sum, and the second row needed repair again later. The final matrix was `[[3,1,-1],[1,-2,2],[0,2,0]]`; a negative entry remained, but balance was incomplete. No arithmetic or shape rejection occurred. Frustration came from broad operations affecting several constraints while precise edits were unavailable in the visible hand.

## control05 — Rectangular Balance

Appending a sparse column on turn 1 immediately achieved a permitted non-square shape, which persisted (later transposed from 3×4 to 4×3). Shift-plus and row additions gave obvious local sum targets. Replacing a column repaired the bottom row but disrupted another row. Turn 5 was `[stall]`: transpose while waiting for a targeted balance edit. Later row additions repaired the second and third rows while retaining a negative entry; the final replacement reduced an oversized top row. The final matrix was `[[1,0,1],[1,1,1],[2,-1,2],[2,0,1]]`. Some visible row progress persisted, but column balance remained incomplete. No arithmetic or shape rejection occurred. The growing hand and many irrelevant matrix shapes made selecting a modest useful move feel cumbersome even when legal actions remained.

These capped outcomes do not establish mathematical impossibility and do not measure real student ability. They record bounded local intuition under this protocol.
