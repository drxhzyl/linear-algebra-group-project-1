# Bounded intuition playtests: split03 and split06

| Session | Result | Turns reached | Legal plays | Candidates per turn | Previews |
|---|---|---:|---:|---|---:|
| split03 | won | 1 | 1 | 1 | 0/6 |
| split06 | turn_limit | 8 | 13 | 2, 2, 2, 2, 1, 1, 1, 2 | 0/6 |

Both precreated sessions were played once through student_play.py. There were no rejected candidates, no stale-plan attempts, no resets, and no stop commands. Every ended turn included a legal play. All proposals were committed; neither per-turn candidate limit nor either preview limit was exceeded.

In split03, the visible local aim was to clear the last row's negative entry. The fixed entry_plus card with arbitrary red fuel did exactly that, and the referee immediately verified the Projection win. No broader target construction or preview was used. There was no stall or shape wait.

In split06, local aims included making the first row sum zero, clearing a repeated first-column entry by row subtraction, appending a column to reach 3×4, and raising a negative middle-row entry to restore a zero row sum. The negative red row then lowered the large last-row sum but unexpectedly left the last column zero; entry_minus repaired that column. Two column additions later lowered the last-row sum without changing the first two rows. Turn 5 was explicitly [stall]: multiplication by the 4×4 identity preserved the existing progress while waiting for a smaller local edit. Turn 6 cleared the shared coordinate of the first two rows, deliberately giving up the middle row's zero sum. Turn 7 cleared a coordinate shared by the middle and last rows. Turn 8 restored the middle and last row sums to zero with a red row addition and an entry_zero.

The final split06 matrix had permitted 3×4 shape, nonzero rows, no zero columns, and visibly zero row sums. The goal was not achieved: row orthogonality did not persist through the final sum repairs. Thus local progress persisted in shape and row sums, while improvements to one condition interfered with another. The cap is not evidence of mathematical impossibility or a measurement of real student ability.

There were no arithmetic or illegal-shape rejections. The main oversight was the temporarily zero fourth column after turn 3's red-row addition; the next move repaired it. The turn 6 zero-sum sacrifice was recorded explicitly rather than mistaken for simultaneous progress on all conditions.

The fixed signs affected choices. split03's available plus matched the needed cancellation directly. In split06, plus restored a negative middle-row entry, whereas minus was useful for the last-column repair. Later, with plus cards available and no entry_minus in hand, lowering positive entries was not directly available through that card type: turn 5 stalled, and subsequent turns pursued orthogonality or used entry_zero and a negative red row. This is an observed constraint on these choices, not a claim that no other legal progress existed.
