"""The card table's preview/take boundary, saved drafts, and input geometry."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import arcade
from pyglet.event import EventDispatcher

from digital import app
from digital.game import Game
import matrix as maths


def controlled_game(mode="auto", code="transpose"):
    game = Game(mode=mode, objective_id="C02+", seed=17, blue_id="B01")
    data = game.to_dict()
    chosen = next(cid for cid, card in game._ops.items() if card["code"] == code)
    data["operations"] = [chosen]
    data["op_draw"] = [cid for cid in game._ops if cid != chosen]
    data["op_discard"] = []
    data["matrices"] = [{"id": "B01", "color": "blue", "values": [[1, 0], [0, 1]]},
                        {"id": "R01", "color": "red", "values": [[1, 0], [0, 1]]}]
    data["red_draw"] = [cid for cid in game._reds if cid != "R01"]
    data["red_discard"] = []
    data["seen"] = [json.dumps([[1, 0], [0, 1]], separators=(",", ":"))]
    return Game.from_dict(data)


class BoardInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.window = arcade.Window(app.WIDTH, app.HEIGHT, visible=False, antialiasing=True)

    @classmethod
    def tearDownClass(cls):
        cls.window.close()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.patch = patch.object(app, "SAVE_DIR", Path(self.directory.name))
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def board(self, mode="auto", code="transpose"):
        board = app.Board(controlled_game(mode, code))
        self.window.show_view(board)
        return board

    def fill_add(self, board):
        board.layout.place_slot("B01", "A")
        board.layout.place_slot("R01", "B")
        board.choose_builtin("builtin:add")

    def drag_result(self, board, destination):
        x, y, w, h = board.RESULT_RECT
        board.on_mouse_press(x + w / 2, y + h - 35, arcade.MOUSE_BUTTON_LEFT, 0)
        board.on_mouse_drag(*destination, 20, 20, arcade.MOUSE_BUTTON_LEFT, 0)
        board.on_mouse_release(*destination, arcade.MOUSE_BUTTON_LEFT, 0)

    def drag_card(self, board, card_id, destination):
        x, y, w, h = dict(board.card_rects())[card_id]
        board.on_mouse_press(x + w / 2, y + h - 35, arcade.MOUSE_BUTTON_LEFT, 0)
        board.on_mouse_drag(*destination, 20, 20, arcade.MOUSE_BUTTON_LEFT, 0)
        board.on_mouse_release(*destination, arcade.MOUSE_BUTTON_LEFT, 0)

    def removal_center(self, board):
        x, y, w, h = board.SLOT_BOXES["remove"]
        return x + w / 2, y + h / 2

    def test_remove_slot_retrieval_replacement_and_saved_removed_cards(self):
        board = self.board()
        target = self.removal_center(board)
        initial = board.game.to_dict()
        self.drag_card(board, "R01", target)
        self.assertEqual(board.layout.slots["remove"], "R01")
        self.assertEqual(board.game.to_dict(), initial)
        self.drag_card(board, "R01", target)
        self.assertEqual(board.game.to_dict(), initial)
        self.drag_card(board, "R01", (600, 600))
        self.assertIsNone(board.layout.slots["remove"])
        self.assertEqual(board.layout.location("R01"), "table")
        operation = board.game.operations[0]["id"]
        self.drag_card(board, operation, target)
        self.drag_card(board, "B01", target)
        self.assertEqual(board.layout.slots["remove"], "B01")
        self.assertNotIn(operation, board.layout._cards)
        self.assertEqual(board.game._removed_operations, [operation])
        board.clear_slots()
        self.assertEqual(board.layout.slots["remove"], "B01")
        board.end_turn()
        self.assertEqual(board.layout.slots["remove"], "B01")
        saved = json.loads((app.SAVE_DIR / "auto.json").read_text())
        board = app.Board(Game.from_dict(saved), saved["ui_state"])
        self.window.show_view(board)
        self.assertEqual(board.layout.slots["remove"], "B01")
        self.assertNotIn(operation, board.layout._cards)
        self.drag_card(board, "R01", target)
        self.assertNotIn("B01", board.layout._cards)
        self.assertEqual(board.layout.slots["remove"], "R01")
        replacement = board.game.operations[0]["id"]
        # Reveal cards after the new turn, then drag from the table so the
        # viewport cannot hide the selected replacement.
        board.layout.move_to_table(replacement, 500, 400)
        self.drag_card(board, replacement, target)
        self.assertNotIn("R01", board.layout._cards)
        self.assertEqual(board.layout.slots["remove"], replacement)
        saved = json.loads((app.SAVE_DIR / "auto.json").read_text())
        restored = app.Board(Game.from_dict(saved), saved["ui_state"])
        self.window.show_view(restored)
        self.assertEqual(restored.layout.slots["remove"], replacement)
        self.assertTrue({"B01", "R01", operation}.isdisjoint(restored.layout._cards))
        restored.on_draw()

    def test_student_result_drop_into_remove_slot_commits_only_correct_answer(self):
        board = self.board("student")
        operation = board.game.operations[0]["id"]
        board.place_in_remove_slot("R01")
        board.layout.place_slot("B01", "A")
        board.layout.place_slot(operation, "operation")
        board.rebuild()
        original = board.game.to_dict()
        self.drag_result(board, self.removal_center(board))
        self.assertEqual(board.game.to_dict(), original)
        self.assertEqual(board.layout.slots["remove"], "R01")
        for field, value in zip(board.fields, ("1", "0", "0", "1")):
            field.text = value
        self.drag_result(board, self.removal_center(board))
        self.assertEqual(board.layout.slots["remove"], "G0001")
        self.assertNotIn("R01", board.layout._cards)
        self.assertEqual(len(board.game.history), 1)
        self.assertIn(operation, board.game._op_discard)
        self.drag_card(board, "B01", self.removal_center(board))
        self.assertNotIn("G0001", board.layout._cards)
        self.assertEqual(board.game.history[0]["result_id"], "G0001")
        saved = json.loads((app.SAVE_DIR / "student.json").read_text())
        restored = app.Board(Game.from_dict(saved), saved["ui_state"])
        self.assertEqual(restored.layout.slots["remove"], "B01")
        self.assertNotIn("G0001", restored.layout._cards)

    def test_preview_cancel_and_invalid_drop_are_free_then_take_commits_once(self):
        board = self.board()
        self.fill_add(board)
        original = board.game.to_dict()
        self.assertEqual(board.preview_values, maths.matrix([[2, 0], [0, 2]]))
        board.rebuild()
        board.on_draw()
        self.drag_result(board, (1668, 800))
        self.assertEqual(board.game.to_dict(), original)
        self.drag_result(board, (700, 650))
        self.assertEqual(len(board.game.history), 1)
        self.assertNotIn("R01", board.layout._cards)
        self.assertIn("B01", board.layout._cards)
        self.assertEqual(board.game.to_dict()["operations"], original["operations"])
        self.assertIn("G0001", board.layout.table)
        self.assertIs(self.window.current_view, board)
        self.assertIsNone(board.take_result())
        self.assertEqual(len(board.game.history), 1)

    def test_physical_operation_cost_is_delayed_and_preview_changes_with_inputs(self):
        board = self.board(code="entry_plus")
        opid = board.game.operations[0]["id"]
        board.layout.place_slot("R01", "A")
        board.layout.place_slot(opid, "operation")
        board.rebuild()
        original = board.game.to_dict()
        initial = deepcopy(board.preview_values)
        board.step_index("i", 1)
        self.assertNotEqual(board.preview_values, initial)
        self.assertEqual(board.game.to_dict(), original)
        board.layout.move_to_table("R01", 400, 450)
        board.rebuild()
        self.assertIsNone(board.preview_card)
        self.assertIsNone(board.take_result())
        self.assertEqual(board.game.to_dict(), original)
        board.layout.place_slot("R01", "A")
        board.rebuild()
        board.take_result()
        self.assertNotIn(opid, board.layout._cards)
        self.assertNotIn("R01", board.layout._cards)
        self.assertEqual(board.game._op_discard, [opid])
        self.assertEqual(board.game._red_discard, ["R01"])
        self.assertEqual(len(board.game.history), 1)

    def test_builtin_buttons_count_commits_survive_reload_and_reset_next_turn(self):
        for mode in ("auto", "student"):
            with self.subTest(mode=mode):
                board = self.board(mode)
                self.fill_add(board)
                for remaining in (1, 0):
                    if mode == "student":
                        values = [str(value) for row in board.preview_values for value in row]
                        for field, value in zip(board.fields, values):
                            field.text = value
                    self.assertTrue(board.verify_preview())
                    self.assertEqual(board.game.builtin_remaining("builtin:add"), remaining + 1)
                    result = board.take_result()
                    self.assertIsNotNone(result)
                    self.assertEqual(board.game.builtin_remaining("builtin:add"), remaining)
                    if remaining:
                        board.layout.place_slot(result["result"].id, "B")
                        board.rebuild()
                add = next(b for b in board.buttons if b.text.startswith("+ Add"))
                multiply = next(b for b in board.buttons if b.text.startswith("× Multiply"))
                self.assertEqual(add.text, "+ Add  0/2")
                self.assertFalse(add.enabled)
                self.assertEqual(multiply.text, "× Multiply  2/2")
                self.assertTrue(multiply.enabled)
                self.assertIsNone(board.preview_card)
                self.assertIn("both uses spent", board.preview_error)
                self.assertIsNone(board.take_result())
                saved = json.loads((app.SAVE_DIR / f"{mode}.json").read_text())
                board = app.Board(Game.from_dict(saved), saved["ui_state"])
                self.window.show_view(board)
                self.assertEqual(board.game.builtin_remaining("builtin:add"), 0)
                self.assertIsNone(board.preview_card)
                board.on_draw()
                board.end_turn()
                self.assertEqual(board.game.builtin_remaining("builtin:add"), 2)
                self.assertIsNotNone(board.preview_card)
                self.assertTrue(next(b for b in board.buttons if b.text.startswith("+ Add")).enabled)
                board.on_draw()

    def test_manual_card_input_checks_without_commit_and_restores_draft(self):
        board = self.board("student")
        self.fill_add(board)
        original = board.game.to_dict()
        self.assertEqual(len(board.fields), 4)
        for field in board.fields:
            field.text = "0"
            self.assertTrue(app.inside(field.left, field.bottom, board.RESULT_RECT))
        self.assertFalse(board.verify_preview())
        self.assertIsNone(board.take_result())
        self.assertEqual(board.game.to_dict(), original)
        for field, value in zip(board.fields, ("2", "0", "0", "2")):
            field.text = value
        self.assertTrue(board.verify_preview())
        self.assertEqual(board.game.to_dict(), original)
        saved = json.loads((app.SAVE_DIR / "student.json").read_text())
        restored = app.Board(Game.from_dict(saved), saved["ui_state"])
        self.window.show_view(restored)
        self.assertEqual([field.text for field in restored.fields], ["2", "0", "0", "2"])
        restored.on_draw()
        self.assertEqual(restored.game.to_dict(), original)
        restored.take_result()
        self.assertEqual(len(restored.game.history), 1)
        self.assertNotIn("R01", restored.layout._cards)
        self.assertIs(self.window.current_view, restored)

    def test_keyboard_entry_and_drag_use_the_live_gui_handler_stack(self):
        board = self.board("student")
        self.fill_add(board)
        original = board.game.to_dict()
        def event(name, *args):
            return EventDispatcher.dispatch_event(self.window, name, *args)
        field = board.fields[0]
        x, y = field.center_x, field.center_y
        event("on_mouse_press", x, y, arcade.MOUSE_BUTTON_LEFT, 0)
        event("on_mouse_release", x, y, arcade.MOUSE_BUTTON_LEFT, 0)
        self.assertTrue(field.active)
        self.assertIsNone(board.drag)
        for index, value in enumerate(("2", "0", "0", "2")):
            event("on_text", value)
            if index < 3:
                event("on_key_press", arcade.key.TAB, 0)
        event("on_key_press", arcade.key.ENTER, 0)
        self.assertTrue(board.preview_verified)
        self.assertEqual(board.result_cell, (1, 1))
        self.assertEqual(set(board.highlight_cells("A")), {(1, 1)})
        self.assertEqual(board.game.to_dict(), original)
        event("on_key_press", arcade.key.TAB, arcade.key.MOD_SHIFT)
        self.assertTrue(board.fields[2].active)
        event("on_key_press", arcade.key.ESCAPE, 0)
        self.assertFalse(any(f.active for f in board.fields))
        x, y, w, h = board.RESULT_RECT
        event("on_mouse_press", x + w / 2, y + h - 30, arcade.MOUSE_BUTTON_LEFT, 0)
        event("on_mouse_drag", 700, 600, -20, 20, arcade.MOUSE_BUTTON_LEFT, 0)
        event("on_mouse_release", 700, 600, arcade.MOUSE_BUTTON_LEFT, 0)
        self.assertEqual(len(board.game.history), 1)
        self.assertIn("G0001", board.layout.table)

    def test_changed_parameters_discard_stale_answer_and_highlight_selected_entry(self):
        board = self.board("student", "entry_minus")
        board.layout.place_slot("B01", "A")
        board.layout.place_slot(board.game.operations[0]["id"], "operation")
        board.rebuild()
        for field in board.fields:
            field.text = "99"
        board.step_index("j", 1)
        self.assertTrue(all(field.text == "" for field in board.fields))
        self.assertEqual(set(board.highlight_cells("A")), {(board.params["i"], board.params["j"])})
        original = board.game.to_dict()
        board.choose_builtin("builtin:multiply")
        self.assertIsNone(board.layout.slots["operation"])
        self.assertIn(original["operations"][0], board.layout.hand)
        self.assertIsNone(board.preview_card)
        self.assertEqual(board.game.to_dict(), original)

    def test_continuous_scroll_keeps_fractional_positions_and_clips_hits(self):
        board = self.board()
        for _ in range(3):
            board.game.end_turn()
        board.layout.sync(board.game)
        board.rebuild()
        self.assertGreater(board.max_scroll(), 0)
        board.on_mouse_scroll(800, 150, .25, -.5)
        self.assertEqual(board.hand_target, 36)
        board.on_update(.02)
        self.assertGreater(board.hand_scroll, 0)
        self.assertLess(board.hand_scroll, board.hand_target)
        board.on_draw()
        self.assertIsNone(board.card_at(10, 150))
        self.assertIsNone(board.card_at(1665, 150))
        board.scroll_hand(10**6)
        for _ in range(15):
            board.on_update(.1)
        self.assertEqual(board.hand_scroll, board.max_scroll())
        board.on_draw()
        last_id, rect = board.hand_rects()[-1]
        self.assertAlmostEqual(rect[0] + rect[2], board.HAND_CLIP[0] + board.HAND_CLIP[2])
        self.assertEqual(board.card_at(rect[0] + 20, 150)[0], last_id)
        # Arcade applies the display's pixel ratio to scissor coordinates itself.
        image = arcade.get_image()
        ratio = image.width / app.WIDTH
        pixel = image.getpixel((round((rect[0] + app.CARD_W / 2) * ratio),
                                round((app.HEIGHT - 44) * ratio)))
        self.assertTrue(all(channel >= 252 for channel in pixel[:3]), pixel)

    def test_default_objective_varies_by_seed_manual_choice_stays(self):
        menu = app.Menu()
        indices = set()
        for seed in range(20):
            menu.seed.text = str(seed)
            indices.add(menu.current_goal_index())
        self.assertGreater(len(indices), 5)
        menu.change_goal(1)
        chosen = menu.current_goal_index()
        menu.seed.text = "493"
        self.assertEqual(menu.current_goal_index(), chosen)

    def test_legacy_layout_removes_retired_operation_without_resetting_table(self):
        game = controlled_game()
        retired = next(c["id"] for c in game._deck["operations"] if c["code"] == "multiply")
        layout = app.TableLayout(game).to_dict()
        layout["hand"].remove("R01")
        layout["table"]["R01"] = [411, 499]
        layout["slots"]["operation"] = retired
        board = app.Board(game, {"layout": layout, "params": {}})
        self.assertEqual(board.layout.table["R01"], (411, 499))
        self.assertEqual(board.builtin_id, "builtin:multiply")
        self.assertIsNone(board.layout.slots["operation"])


if __name__ == "__main__":
    unittest.main()
