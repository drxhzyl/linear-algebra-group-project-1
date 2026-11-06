# Play GameTrix locally

This is the solo Arcade version of GameTrix. It includes the objectives and operations from the expanded deck, an eight-turn game, exact matrix arithmetic, move history, and separate local saves for the two calculation modes.

## Start on this Mac

The Python environment and Arcade are already installed in this folder. Double-click either launcher in Finder:

- **Play Automatic.command** — the computer calculates each selected operation.
- **Play Student.command** — you calculate the result and fill in its entries; the computer verifies it before playing the cards.

Both launchers open the same game with the corresponding mode selected. You can also change modes on the menu.

## Play a game

The game opens in a fixed, non-resizable 1680 × 1050 window. Cards use a larger, raised printed-card style. Your hand is one mixed set of operation cards and matrix cards; new results join it too.

1. Choose a mode and objective. Random objective selection is the default and is determined by the deal seed, so repeating a seed repeats the objective and deal. Use the left and right arrows to select a specific objective. Enter a whole-number seed to repeat a deal; both modes use the same deal.
2. Start the game. Your hand receives one blue matrix, three operation cards, and three red matrices. **Add** and **Multiply** are built-in controls, each limited to **two uses per turn**, and are not dealt as physical operation cards. The buttons show remaining uses (`2/2`, `1/2`, `0/2`) and disable when exhausted. Use the mouse wheel or trackpad, drag the scrollbar, or move a card to either edge of the window while dragging to browse the hand; drag cards within it to reorder them.
3. Drag cards into the large central table area and place them freely. Moving, overlapping, or arranging cards there does not play them. To prepare an action, put a matrix in **A**, choose an operation card or built-in operation, and—only when required—a different physical matrix in **B**. Controls below the slots set parameters. The matrix highlights show relevant rows, columns, or entries; for entry and vector operations, click a cell in **A** to select its entry or target vector (and click **B** to select the source vector where applicable).
4. Once the selected action is valid, its calculated result appears in the **Result** slot as a preview. In student mode, enter integers or exact fractions such as `-3/2` directly in its cells; press **Enter** or click **Check** to check the answer. An incorrect answer stays on the preview and does not consume cards or uses. To commit a valid result, drag the preview to the hand, table, or A/B slot, or click **Take result**. This consumes any red input cards and physical operation card, or one use of the selected built-in operation; blue inputs remain available. Previewing and checking never spend a use.
5. Double-click or right-click a card to read it, or select it and press **I**. The inspector shows complete exact matrix values; card faces may abbreviate very long entries.
6. Each committed result becomes a new blue card. Each different qualifying result earns one point. Repeated matrices and the starting matrix earn no additional points.
7. Keep playing, or end the turn to draw three operation cards and up to three red matrices. Each new turn resets Add and Multiply to two uses each; unused uses do not carry over. Unused cards and their positions carry over. Discarded cards can recycle when a draw pile runs out. Solo practice allows ending a turn without a move. Finish turn eight to see the score and review your moves.

**Help** explains the rules, and **History** records every committed calculation.

The **Remove card** slot sits to the left of the result preview. Drop an operation, red matrix, or blue matrix into it; the newest card stays there and can be dragged back out. Dropping a different card into the occupied slot permanently removes the previous card from play, without recycling it or changing earned points or calculation history. Dropping the same card back into the slot does nothing. The slot survives turn changes and saving/loading; **Clear slots** only clears A, operation, and B. A correct result preview may also be dragged directly into Remove card: this first commits the calculation, then replaces the slot's previous card.

## Digital operation deck

The digital deck has **90 operation cards**, with extra copies of the rare operations:

| Operation | Previous copies | Current copies |
| --- | ---: | ---: |
| LU factorization | 1 | 5 |
| Inverse | 1 | 5 |
| Negate | 1 | 4 |
| Double | 1 | 4 |
| Replace vector | 2 | 4 |
| Shift every entry +1 | 2 | 4 |
| Shift every entry −1 | 2 | 4 |

Other counts remain: Subtract 5, Add vector 5, Append vector 4, Transpose 3, Swap 3, Entry +1 and Entry −1 12 each, Entry zero 8, Combine vectors 8. LU and Inverse each now make up 5/90 (5.6%) of the full pile, up from 1/70 (1.4%). New digital copies have separate IDs such as `O40x2`; each is drawn and discarded independently. The print deck and command-line playtests use their own existing distributions.

## Saves

The game saves after a successful move, when card positions change, at each turn end, and when returning to the menu. Student answer drafts are saved with the table layout. **Continue saved game** restores the selected mode, including its cards, score, history, hand order, table positions, and calculation slots. New saves use version 4, retaining removed-card records for history validation and preserving the one card held in Remove card. Versions 1–3 load with no removed cards and an empty removal slot. Version 1 saves first remove retired physical Add and Multiply cards. Versions 1 and 2 then mix the 20 extra copies into the draw pile, preserving existing cards, results, history, score, RNG state, and relative order of old draw cards. Current hands are not redealt. Remaining built-in uses come from committed history, so loading does not reset them. Old turns with more than two uses keep their results but allow no further use of that operation until the next turn. Old table layout and draft state are retained when applicable. Older saves without layout data still load; available cards appear in the mixed hand.

- Automatic mode: `digital/saves/auto.json`
- Student mode: `digital/saves/student.json`
- Starting a new game keeps the previous save as `auto.previous.json` or `student.previous.json`.

Saves are written through a temporary file before replacing the old save. If saving fails, a warning remains visible and **Menu** keeps the current game open so you can retry. The finished-game screen also offers **Retry save**. Answer drafts save shortly after typing stops and are restored for the same calculation.

## Install on another computer

Use Python 3.11 or later and a desktop graphics environment supported by Arcade. Run these commands from the GameTrix folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-digital.txt
.venv/bin/python run_auto.py
# Or:
.venv/bin/python run_student.py
```

On Windows, use `py -3 -m venv .venv`, then `.venv\Scripts\python` instead of `.venv/bin/python`. The `.command` launchers are for macOS. This build was exercised on macOS with Python 3.11 and Arcade 3.3.3.

## Small architecture

The two launchers choose a default mode. `digital/app.py` draws the Arcade screens and handles input. `digital/table.py` tracks cards in the mixed hand, on the table, or in the A/operation/B slots; `digital/card_faces.py` draws the printed-style faces and shadows. `digital/game.py` manages rules, turns, scoring, validation, and the atomic save that includes optional UI layout state. `matrix.py` calculates exact results and checks objective conditions using fractions. The game model has no Arcade dependency, so its rules can be tested without opening a window.

The older `gametrix.py` command-line playtest tool remains separate; its session files are not digital-game saves. See [the Chinese architecture document](digital/ARCHITECTURE.zh-CN.md) for a fuller explanation.

Run all tests, including the card-table checks in an invisible graphics window, with:

```sh
.venv/bin/python -m unittest discover -s tests -v
```
