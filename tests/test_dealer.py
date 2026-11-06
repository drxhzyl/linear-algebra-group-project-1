import copy
from pathlib import Path
import tempfile
import unittest

import gametrix as g
import matrix as mx


class DealerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.deck = g.generate_deck(20261028)
        cls.path = Path(cls.directory.name)/"deck.json"
        g.write_json(cls.path, cls.deck)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def session(self, mode="open"):
        return g.new_session(self.path, 72, "C11", "B01", mode, "test", 12)

    def test_quotas_reproducibility_and_initial_goals(self):
        d = self.deck
        self.assertEqual([len(d[k]) for k in ("blue", "red", "operations", "objectives")],
                         [12, 30, 40, 15])
        self.assertEqual(d, g.generate_deck(20261028))
        self.assertEqual(sum(c["code"] == "append_vector" for c in d["operations"]), 4)
        for b in d["blue"]:
            A = mx.matrix(b["matrix"])
            self.assertEqual(mx.shape(A), (3, 3))
            self.assertTrue(0 < abs(mx.det(A)) <= 6)
            self.assertFalse(any(mx.check(o["id"], A)["won"] for o in d["objectives"]))
        quotas = g.collections.Counter(tuple(c["shape"]) for c in d["red"])
        self.assertEqual(quotas[(3, 3)], 10)
        self.assertEqual(len(quotas), 9)
        for objective in d["objectives"]:
            self.assertTrue(mx.check(objective["id"], mx.matrix(objective["A"]))["won"], objective["id"])

    def test_invalid_play_is_transactional(self):
        s = self.session()
        before = copy.deepcopy(s)
        op = next(c["id"] for c in self.deck["operations"] if c["code"] == "add")
        with self.assertRaises(ValueError):
            g.play(s, self.deck, op, "R01", {})
        self.assertEqual(s, before)

    def test_at_least_one_multiple_plays_and_no_automatic_draw(self):
        s = self.session()
        with self.assertRaises(ValueError):
            g.advance(s)
        transposes = [c["id"] for c in self.deck["operations"] if c["code"] == "transpose"]
        for op in transposes[:2]:
            g.play(s, self.deck, op, None, {})
        self.assertEqual((s["turn"], s["turn_operations"], s["moves"]), (1, 2, 2))
        self.assertEqual(len(s["operation_hand"]), 38)
        self.assertEqual(len(s["red_hand"]), 30)
        g.advance(s)
        self.assertEqual((s["turn"], s["turn_operations"]), (2, 0))

    def test_draws_retain_unused_cards(self):
        s = self.session("draw")
        self.assertEqual((len(s["operation_hand"]), len(s["red_hand"])), (3, 5))
        old_red = set(s["red_hand"])
        s["turn_operations"] = 1
        g.advance(s)
        self.assertEqual((len(s["operation_hand"]), len(s["red_hand"])), (6, 10))
        self.assertTrue(old_red <= set(s["red_hand"]))
        g.inventory_check(s, self.deck)

    def test_red_consumption_and_dimension_change(self):
        s = self.session()
        op = next(c["id"] for c in self.deck["operations"] if c["code"] == "append_vector")
        g.play(s, self.deck, op, "R03", {"axis": "row", "source": 0, "target": None})
        self.assertEqual(mx.shape(mx.matrix(s["current"])), (4, 3))
        self.assertNotIn("R03", s["red_hand"])
        self.assertEqual(s["red_discard"], ["R03"])
        self.assertEqual(s["turn"], 1)
        g.inventory_check(s, self.deck)

    def test_only_discards_are_reshuffled(self):
        s = self.session("draw")
        g.deal(s, "red", 100)
        self.assertEqual(len(s["red_hand"]), 30)
        card = s["red_hand"].pop()
        s["red_discard"].append(card)
        self.assertEqual(g.deal(s, "red", 5), [card])
        self.assertEqual(s["red_cycles"], 1)
        self.assertEqual(len(s["red_hand"]), 30)
        g.inventory_check(s, self.deck)

    def test_summary_rejects_changed_deck(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"bad.json"
            s = self.session()
            s["deck_sha256"] = "wrong"
            g.write_json(path, s)
            with self.assertRaises(ValueError):
                g.summarize(folder)

    def test_replay_catches_falsified_move_and_inventory(self):
        s = self.session()
        op = next(c["id"] for c in self.deck["operations"] if c["code"] == "transpose")
        g.play(s, self.deck, op, None, {})
        self.assertTrue(g.audit_session(s, self.deck))
        tampered = copy.deepcopy(s)
        tampered["history"][0]["after"][0][0] = 999
        with self.assertRaises(ValueError):
            g.audit_session(tampered, self.deck)
        tampered = copy.deepcopy(s)
        tampered["operation_hand"].append(tampered["operation_discard"].pop())
        with self.assertRaises(ValueError):
            g.audit_session(tampered, self.deck)

    def test_replay_checks_seeded_draw_and_end_turn(self):
        s = self.session("draw")
        op = next(c["id"] for c in self.deck["operations"] if c["id"] in s["operation_hand"] and c["code"] in ("transpose", "swap", "shift_plus", "shift_minus", "negate", "double", "inverse"))
        g.play(s, self.deck, op, None, {"axis": "row", "i": 0, "j": 1})
        drawn = g.advance(s)
        s["history"].append({"type": "end_turn", "turn": 1, "note": "", "drawn": drawn})
        self.assertTrue(g.audit_session(s, self.deck))
        s["history"][-1]["drawn"]["red"].reverse()
        with self.assertRaises(ValueError):
            g.audit_session(s, self.deck)


if __name__ == "__main__":
    unittest.main()
