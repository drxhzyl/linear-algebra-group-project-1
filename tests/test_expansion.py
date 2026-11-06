import argparse
import copy
from collections import Counter
from contextlib import redirect_stderr
from fractions import Fraction
from io import StringIO
from pathlib import Path
import tempfile
import unittest

import diagnostics
import gametrix as g
import matrix as mx


class ExpansionMatrixTests(unittest.TestCase):
    def setUp(self):
        self.A = mx.matrix([["1/2", 2, 3], [4, 5, 6]])

    def test_single_entry_changes_are_exact_and_do_not_mutate(self):
        before = mx.dump(self.A)
        self.assertEqual(mx.dump(mx.entry_tweak(self.A, 0, 0)),
                         [["3/2", 2, 3], [4, 5, 6]])
        self.assertEqual(mx.dump(mx.entry_tweak(self.A, 0, 0, -1)),
                         [["-1/2", 2, 3], [4, 5, 6]])
        zeroed = mx.entry_zero(self.A, 1, 2)
        self.assertEqual(mx.dump(zeroed), [["1/2", 2, 3], [4, 5, 0]])
        self.assertIsInstance(zeroed[1][2], Fraction)
        self.assertEqual(mx.dump(self.A), before)

    def test_only_target_row_or_column_changes(self):
        before = mx.dump(self.A)
        cases = [("row", 0, 1, 1, [["1/2", 2, 3], ["9/2", 7, 9]]),
                 ("row", 1, 0, -1, [["-7/2", -3, -3], [4, 5, 6]]),
                 ("column", 0, 2, 1, [["1/2", 2, "7/2"], [4, 5, 10]]),
                 ("column", 2, 1, -1, [["1/2", -1, 3], [4, -1, 6]])]
        for axis, source, target, delta, expected in cases:
            with self.subTest(axis=axis, delta=delta):
                result = mx.combine_vectors(self.A, axis, source, target, delta)
                self.assertEqual(mx.dump(result), expected)
                self.assertEqual(mx.shape(result), mx.shape(self.A))
                self.assertEqual(mx.dump(self.A), before)

    def test_entry_index_and_delta_validation(self):
        for i, j in [(-1, 0), (2, 0), (0, 3), (0, -1), (True, 0), (0, None)]:
            for operation in (mx.entry_tweak, mx.entry_zero):
                with self.subTest(operation=operation.__name__, i=i, j=j):
                    with self.assertRaises(ValueError):
                        operation(self.A, i, j)
        for delta in (0, 2, -2, True, 1.0, "1", Fraction(1)):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                mx.entry_tweak(self.A, 0, 0, delta)
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                mx.combine_vectors(self.A, "row", 0, 1, delta)

    def test_vector_axis_indices_and_distinctness_validation(self):
        for args in [("diagonal", 0, 1), ("row", -1, 0), ("row", 0, 2),
                     ("column", 3, 0), ("row", True, 1), ("row", 0, None),
                     ("row", 1, 1), ("column", 2, 2)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                mx.combine_vectors(self.A, *args)

    def test_apply_ignores_fuel_contents_and_requires_its_presence(self):
        for code, expected in [("entry_tweak", [["3/2", 2, 3], [4, 5, 6]]),
                               ("entry_zero", [[0, 2, 3], [4, 5, 6]])]:
            with self.subTest(code=code):
                self.assertEqual(mx.dump(g.apply(self.A, code, object(), i=0, j=0)), expected)
                with self.assertRaises(ValueError):
                    g.apply(self.A, code, i=0, j=0)
        self.assertEqual(g.apply(self.A, "combine_vectors", axis="row", source=0, target=1),
                         mx.combine_vectors(self.A, "row", 0, 1))


class ExpansionPlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.original = g.generate_deck(20261028)
        cls.deck = copy.deepcopy(cls.original)
        cls.deck["blue"][0]["matrix"] = [["1/2", 2, 3], [4, 5, 6]]
        for code in ("entry_tweak", "entry_zero", "entry_plus", "entry_minus", "combine_vectors"):
            cls.deck["operations"].append({"id": "E_" + code, "kind": "operation", "code": code})
        cls.path = Path(cls.directory.name) / "deck.json"
        g.write_json(cls.path, cls.deck)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def session(self):
        return g.new_session(self.path, 72, "C11", "B01", "open", "test", 12)

    def test_original_distribution_stays_unchanged(self):
        self.assertEqual(len(self.original["operations"]), 40)
        self.assertEqual(Counter(c["code"] for c in self.original["operations"]),
                         Counter({code: count for code, _, count, _ in g.OPS}))
        self.assertFalse(g.RED_FUEL_OPS & set(c["code"] for c in self.original["operations"]))

    def test_any_red_shape_is_consumed_as_fuel(self):
        for code in ("entry_tweak", "entry_zero"):
            for red in self.deck["red"]:
                with self.subTest(code=code, shape=red["shape"]):
                    s = self.session()
                    operation_id = "E_" + code
                    event = g.play(s, self.deck, operation_id, red["id"],
                                   {"i": 0, "j": 0, "delta": -1})
                    expected = [["-1/2" if code == "entry_tweak" else 0, 2, 3], [4, 5, 6]]
                    self.assertEqual(s["current"], expected)
                    self.assertEqual(s["red_discard"], [red["id"]])
                    self.assertEqual(s["operation_discard"], [operation_id])
                    self.assertNotIn(red["id"], s["red_hand"])
                    self.assertEqual(event["red"], red["id"])
                    g.inventory_check(s, self.deck)
                    self.assertTrue(g.audit_session(s, self.deck))

    def test_play_does_not_read_fuel_matrix(self):
        deck = copy.deepcopy(self.deck)
        del deck["red"][0]["matrix"]
        s = self.session()
        g.play(s, deck, "E_entry_zero", deck["red"][0]["id"], {"i": 0, "j": 0})
        self.assertEqual(s["current"][0][0], 0)

    def test_fixed_sign_cards_cannot_choose_the_other_direction(self):
        for code, override, expected in (("entry_plus", -1, "3/2"), ("entry_minus", 1, "-1/2")):
            with self.subTest(code=code):
                s = self.session()
                g.play(s, self.deck, "E_" + code, "R05", {"i": 0, "j": 0, "delta": override})
                self.assertEqual(s["current"], [[expected, 2, 3], [4, 5, 6]])
                self.assertEqual(s["red_discard"], ["R05"])
                self.assertTrue(g.audit_session(s, self.deck))

    def test_combination_consumes_only_operation_and_replays_default_delta(self):
        s = self.session()
        red_hand = s["red_hand"][:]
        arguments = {"axis": "column", "source": 0, "target": 2}
        g.play(s, self.deck, "E_combine_vectors", None, arguments)
        self.assertEqual(s["current"], [["1/2", 2, "7/2"], [4, 5, 10]])
        self.assertEqual(s["red_hand"], red_hand)
        self.assertEqual(s["red_discard"], [])
        self.assertNotIn("delta", s["history"][0]["params"])
        self.assertTrue(g.audit_session(s, self.deck))

    def test_rejection_leaves_entire_session_untouched(self):
        invalid = [("entry_tweak", None, {"i": 0, "j": 0}),
                   ("entry_zero", "missing", {"i": 0, "j": 0}),
                   ("entry_tweak", "R01", {"i": 0, "j": 0, "delta": 0}),
                   ("entry_zero", "R01", {"i": 2, "j": 0}),
                   ("entry_zero", "R01", {"i": 0, "j": -1}),
                   ("combine_vectors", "R01", {"source": 0, "target": 1}),
                   ("combine_vectors", None, {"source": 0, "target": 0}),
                   ("combine_vectors", None, {"source": 0, "target": 2}),
                   ("combine_vectors", None, {"source": 0, "target": 1, "delta": 2}),
                   ("combine_vectors", None, {"axis": "diagonal", "source": 0, "target": 1})]
        for code, red, arguments in invalid:
            with self.subTest(code=code, red=red, arguments=arguments):
                s = self.session()
                before = copy.deepcopy(s)
                with self.assertRaises(ValueError):
                    g.play(s, self.deck, "E_" + code, red, arguments)
                self.assertEqual(s, before)

    def test_old_history_parameters_replay_exactly_without_delta(self):
        s = self.session()
        operation = next(c["id"] for c in self.deck["operations"] if c["code"] == "add_vector")
        arguments = {"axis": "column", "source": 0, "target": 1,
                     "i": None, "j": None, "factor": "L", "exponent": 2}
        event = copy.deepcopy(g.play(s, self.deck, operation, "R01", arguments))
        self.assertTrue(g.audit_session(s, self.deck))
        self.assertEqual(s["history"][0], event)
        self.assertNotIn("delta", s["history"][0]["params"])


class ExpansionInterfaceTests(unittest.TestCase):
    def test_cli_delta_default_choices_and_params(self):
        parser = argparse.ArgumentParser()
        g.action_options(parser)
        self.assertEqual(g.params(parser.parse_args([]))["delta"], 1)
        self.assertEqual(g.params(parser.parse_args(["--delta", "-1"]))["delta"], -1)
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["--delta", "0"])

    def test_diagnostics_fuel_and_combine_legality_for_all_allowed_shapes(self):
        fuel = {"id": "fuel", "matrix": [[99, 98], [97, 96]]}
        for m in range(2, 5):
            for n in range(2, 5):
                A = mx.matrix([[0] * n for _ in range(m)])
                with self.subTest(shape=(m, n)):
                    no_red = diagnostics.usable_codes(A, [])
                    with_red = diagnostics.usable_codes(A, [fuel])
                    self.assertIn("combine_vectors", no_red)
                    self.assertFalse(g.RED_FUEL_OPS & no_red)
                    self.assertTrue(g.RED_FUEL_OPS <= with_red)
        for A in (mx.identity(1), mx.identity(5)):
            usable = diagnostics.usable_codes(A, [fuel])
            self.assertFalse((g.RED_FUEL_OPS | {"combine_vectors"}) & usable)


if __name__ == "__main__":
    unittest.main()
