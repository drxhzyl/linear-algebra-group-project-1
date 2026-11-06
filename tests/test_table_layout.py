"""Card placement and layout snapshot regressions without a graphical window."""

from copy import deepcopy
import json
import random
import unittest

from digital.game import Game, MatrixCard
from digital.table import TableLayout


class TableLayoutTests(unittest.TestCase):
    def setUp(self):
        self.game = Game(seed=19, blue_id="B01")
        self.layout = TableLayout(self.game)
        self.operation = self.game.operations[0]["id"]
        self.blue = self.game.matrices[0].id
        self.red = next(card.id for card in self.game.matrices if card.color == "red")

    def assert_physical_cards(self):
        placements = (self.layout.hand + list(self.layout.table)
                      + [card_id for card_id in self.layout.slots.values() if card_id is not None])
        live = [card["id"] for card in self.game.operations] + [card.id for card in self.game.matrices]
        self.assertCountEqual(placements, live)
        self.assertEqual(len(placements), len(set(placements)))

    def test_all_cards_start_in_one_deterministic_mixed_hand_without_changing_game(self):
        before = self.game.to_dict()
        layout = TableLayout(self.game)
        expected = [card["id"] for card in self.game.operations] + [card.id for card in self.game.matrices]
        random.Random("19:1:layout").shuffle(expected)
        self.assertEqual(layout.hand, expected)
        self.assertEqual(layout.hand, self.layout.hand)
        self.assertEqual(self.game.to_dict(), before)
        self.assertNotIn(self.game.objective["id"], layout.hand)
        self.assertEqual(set(layout.kind(card_id) for card_id in layout.hand), {"operation", "blue", "red"})
        operation_positions = [i for i, card_id in enumerate(layout.hand) if layout.kind(card_id) == "operation"]
        self.assertNotEqual(operation_positions, list(range(len(self.game.operations))))
        self.assertEqual(layout.table, {})
        self.assertTrue(all(card_id is None for card_id in layout.slots.values()))
        self.assertIs(layout.card(self.operation), self.game.operations[0])
        self.assertIs(layout.card(self.blue), self.game.matrices[0])
        self.assert_physical_cards()

    def test_moves_replacement_and_stack_order_keep_one_physical_card(self):
        layout = self.layout
        layout.move_to_table(self.blue, -100, 200)
        layout.move_to_table(self.red, 30, 40)
        layout.bring_to_front(self.blue)
        self.assertEqual(list(layout.table), [self.red, self.blue])
        self.assertEqual(layout.location(self.blue), "table")
        layout.place_slot(self.blue, "A")
        layout.place_slot(self.red, "B")
        layout.place_slot(self.operation, "operation")
        layout.place_slot(self.blue, "B")
        self.assertIsNone(layout.slots["A"])
        self.assertEqual(layout.slots["B"], self.blue)
        self.assertEqual(layout.location(self.red), "hand")
        self.assertEqual(layout.hand[-1], self.red)
        layout.place_slot(self.blue, "B")
        layout.move_to_hand(self.operation)
        layout.move_to_hand(self.operation)
        self.assertIsNone(layout.slots["operation"])
        self.assert_physical_cards()

    def test_invalid_drops_preserve_original_placement(self):
        self.layout.move_to_table(self.operation, 10, 20)
        self.layout.place_slot(self.blue, "A")
        before = self.layout.to_dict()
        for card_id, slot in ((self.operation, "A"), (self.red, "operation"),
                              (self.blue, "unknown"), ("unknown", "A"), (self.blue, [])):
            with self.subTest(card_id=card_id, slot=slot), self.assertRaises(ValueError):
                self.layout.place_slot(card_id, slot)
            self.assertEqual(self.layout.to_dict(), before)
        for coordinate in (float("nan"), float("inf"), True, "12", 10 ** 1000):
            with self.subTest(coordinate=coordinate), self.assertRaises(ValueError):
                self.layout.move_to_table(self.blue, coordinate, 5)
            self.assertEqual(self.layout.to_dict(), before)
        with self.assertRaises(ValueError):
            self.layout.move_to_hand("unknown")
        self.assert_physical_cards()

    def test_sync_removes_consumed_cards_preserves_placements_and_adds_results(self):
        self.layout.move_to_table(self.operation, 10, 20)
        self.layout.place_slot(self.red, "A")
        self.layout.move_to_table(self.blue, 30, 40)
        held_operation = self.game.operations[1]["id"]
        self.layout.place_slot(held_operation, "operation")
        # A real unary action consumes its operation and red operand.
        operation = next(card for card in self.game._deck["operations"] if card["code"] == "transpose")
        self.game.operations[0] = deepcopy(operation)
        self.layout.sync(self.game)
        self.layout.move_to_table(operation["id"], 10, 20)
        result = self.game.perform(operation["id"], self.red)["result"]
        self.layout.sync(self.game)
        self.assertNotIn(operation["id"], self.layout.table)
        self.assertIsNone(self.layout.slots["A"])
        self.assertEqual(self.layout.table[self.blue], (30, 40))
        self.assertEqual(self.layout.slots["operation"], held_operation)
        self.assertEqual(self.layout.hand[-1], result.id)
        self.assertIs(self.layout.card(result.id), result)
        self.assert_physical_cards()

    def test_new_turn_deals_append_mixed_cards_without_moving_existing_cards(self):
        self.layout.place_slot(self.blue, "A")
        self.layout.move_to_table(self.operation, 10, 20)
        before_hand = list(self.layout.hand)
        self.game.end_turn()
        game_state = self.game.to_dict()
        self.layout.sync(self.game)
        new_ids = set(self.game.last_draw["operations"] + self.game.last_draw["red"])
        self.assertEqual(self.layout.hand[:len(before_hand)], before_hand)
        self.assertEqual(set(self.layout.hand[len(before_hand):]), new_ids)
        self.assertEqual(self.layout.slots["A"], self.blue)
        self.assertEqual(self.layout.table[self.operation], (10, 20))
        self.assertEqual(self.game.to_dict(), game_state)
        self.assert_physical_cards()

    def test_roundtrip_preserves_order_and_is_detached(self):
        self.layout.move_to_table(self.operation, 11.5, -21)
        self.layout.move_to_table(self.blue, 1, 2)
        self.layout.place_slot(self.red, "B")
        snapshot = self.layout.to_dict()
        restored = TableLayout.from_dict(self.game, json.loads(json.dumps(snapshot)))
        self.assertEqual(restored.to_dict(), snapshot)
        self.assertEqual(list(restored.table), [self.operation, self.blue])
        snapshot["hand"].clear()
        snapshot["table"][self.blue][0] = 99
        snapshot["slots"]["B"] = None
        self.assertEqual(restored.to_dict(), self.layout.to_dict())

    def test_restore_missing_live_cards_adds_them_to_hand(self):
        snapshot = {"hand": [], "table": {self.blue: [1, 2]},
                    "slots": {"A": None, "operation": None, "B": None}}
        restored = TableLayout.from_dict(self.game, snapshot)
        self.assertEqual(restored.table[self.blue], (1, 2))
        self.assertEqual(restored.hand, [card_id for card_id in self.layout.hand if card_id != self.blue])
        self.game.matrices.append(MatrixCard("G0001", "blue", self.game.matrices[0].values))
        restored = TableLayout.from_dict(self.game, snapshot)
        self.assertIn("G0001", restored.hand)

    def test_remove_slot_accepts_any_card_and_restores_old_three_slot_layouts(self):
        for card_id in (self.blue, self.red, self.operation):
            self.layout.place_slot(card_id, "remove")
            self.assertEqual(self.layout.location(card_id), "remove")
            snapshot = self.layout.to_dict()
            self.assertEqual(TableLayout.from_dict(self.game, snapshot).to_dict(), snapshot)
            self.layout.move_to_hand(card_id)
        self.layout.place_slot(self.red, "remove")
        before = self.layout.to_dict()
        with self.assertRaises(ValueError):
            self.layout.place_slot(self.blue, "remove")
        self.assertEqual(self.layout.to_dict(), before)
        self.assert_physical_cards()
        old = self.layout.to_dict()
        del old["slots"]["remove"]
        old["hand"].append(self.red)
        restored = TableLayout.from_dict(self.game, old)
        self.assertIsNone(restored.slots["remove"])
        self.assertIn(self.red, restored.hand)

    def test_restore_rejects_invalid_zones_cards_coordinates_and_duplicates(self):
        mutations = (
            lambda data: data.update(hand=None),
            lambda data: data.update(table=[]),
            lambda data: data.update(slots={"A": None}),
            lambda data: data["slots"].update(extra=None),
            lambda data: data["hand"].append("unknown"),
            lambda data: data["hand"].append(data["hand"][0]),
            lambda data: data["table"].update({self.blue: [1, 2]}),
            lambda data: data["slots"].update(A=self.blue),
            lambda data: data["table"].update({"unknown": [1, 2]}),
        )
        for mutate in mutations:
            data = self.layout.to_dict()
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                TableLayout.from_dict(self.game, data)
        for position in ([float("nan"), 0], [0, float("inf")], [True, 0], [1], "12", [1, "2"]):
            data = self.layout.to_dict()
            data["hand"].remove(self.blue)
            data["table"][self.blue] = position
            with self.subTest(position=position), self.assertRaises(ValueError):
                TableLayout.from_dict(self.game, data)
        for card_id, slot in ((self.operation, "A"), (self.blue, "operation")):
            data = self.layout.to_dict()
            data["hand"].remove(card_id)
            data["slots"][slot] = card_id
            with self.subTest(slot=slot), self.assertRaises(ValueError):
                TableLayout.from_dict(self.game, data)
        with self.assertRaises(ValueError):
            TableLayout.from_dict(self.game, None)


if __name__ == "__main__":
    unittest.main()
