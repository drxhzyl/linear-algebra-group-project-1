"""Player-facing dispatch, parameter, and damaged-save regressions."""

from copy import deepcopy
from fractions import Fraction
import json
import unittest

from digital.game import (AnswerError, BINARY_CODES, BUILTIN_OPERATIONS, Game, GameError,
                          MatrixCard, parse_answer)
import matrix as maths


def controlled_hand(code, a=None, b=None, *, mode="auto"):
    """Isolate one operation, preserving physical-card conservation."""
    game = Game(mode=mode, seed=19, blue_id="B01")
    operation = (BUILTIN_OPERATIONS[f"builtin:{code}"] if code in ("add", "multiply") else
                 next(c for c in game._ops.values() if c["code"] == code))
    game.operations = [] if operation.get("builtin") else [deepcopy(operation)]
    game._op_draw = [i for i in game._ops if i != operation["id"]]
    game._op_discard = []
    a = [[2, 1], [4, 3]] if a is None else a
    b = [[1, 2], [3, 4]] if b is None else b
    game.matrices = [MatrixCard("B01", "blue", maths.matrix(a)),
                     MatrixCard("R01", "red", maths.matrix(b))]
    game._red_draw = [i for i in game._reds if i != "R01"]
    game._red_discard = []
    game._seen = {json.dumps(maths.dump(game.matrices[0].values), separators=(",", ":"))}
    return game, operation["id"]


# Each expected result is explicit, so dispatch cannot silently call a different
# operation that happens to agree on an identity or zero matrix.
DISPATCH = (
    ("add", {}, [[3, 3], [7, 7]]),
    ("subtract", {}, [[1, -1], [1, -1]]),
    ("multiply", {}, [[5, 8], [13, 20]]),
    ("add_vector", {"axis": "column", "source": 1, "target": 0}, [[4, 1], [8, 3]]),
    ("replace_vector", {"axis": "row", "source": 1, "target": 0}, [[3, 4], [4, 3]]),
    ("append_vector", {"axis": "column", "source": 1}, [[2, 1, 2], [4, 3, 4]]),
    ("transpose", {}, [[2, 4], [1, 3]]),
    ("swap", {"axis": "column", "i": 0, "j": 1}, [[1, 2], [3, 4]]),
    ("shift_plus", {}, [[3, 2], [5, 4]]),
    ("shift_minus", {}, [[1, 0], [3, 2]]),
    ("negate", {}, [[-2, -1], [-4, -3]]),
    ("double", {}, [[4, 2], [8, 6]]),
    ("inverse", {}, [["3/2", "-1/2"], [-2, 1]]),
    ("lu", {"factor": "L"}, [[1, 0], [2, 1]]),
    ("lu", {"factor": "U"}, [[2, 1], [0, 1]]),
    ("entry_plus", {"i": 1, "j": 0}, [[2, 1], [5, 3]]),
    ("entry_minus", {"i": 0, "j": 1}, [[2, 0], [4, 3]]),
    ("entry_zero", {"i": 1, "j": 1}, [[2, 1], [4, 0]]),
    ("combine_vectors", {"axis": "column", "source": 0, "target": 1, "delta": -1},
     [[2, -1], [4, -1]]),
)


class DispatchEdgeTests(unittest.TestCase):
    def assert_conserved(self, game):
        op_ids = ([c["id"] for c in game.operations]
                  + game._op_draw + game._op_discard)
        red_ids = ([c.id for c in game.matrices if c.color == "red"]
                   + game._red_draw + game._red_discard)
        self.assertCountEqual(op_ids, game._ops)
        self.assertCountEqual(red_ids, game._reds)
        self.assertEqual(len({c.id for c in game.matrices}), len(game.matrices))

    def test_all_deck_operations_dispatch_exactly_and_conserve_physical_cards(self):
        deck_codes = {c["code"] for c in Game()._deck["operations"]}
        self.assertEqual({code for code, _, _ in DISPATCH}, deck_codes)
        self.assertEqual(len(deck_codes), 18)
        for code, params, expected in DISPATCH:
            with self.subTest(code=code, params=params):
                game, op = controlled_hand(code)
                b_id = "R01" if code in BINARY_CODES else None
                before = game.to_dict()
                self.assertEqual(game.calculate(op, "B01", b_id, **params), maths.matrix(expected))
                self.assertEqual(game.to_dict(), before)
                result = game.perform(op, "B01", b_id, **params)["result"]
                self.assertEqual(result.values, maths.matrix(expected))
                self.assertEqual(result.color, "blue")
                self.assertEqual(game.get_matrix("B01").to_dict(), before["matrices"][0])
                self.assertEqual(any(c.id == "R01" for c in game.matrices), b_id is None)
                self.assert_conserved(game)

    def test_every_dispatch_rejects_wrong_student_answer_without_commit_or_solution(self):
        for code, params, _ in DISPATCH:
            with self.subTest(code=code, params=params):
                game, op = controlled_hand(code, mode="student")
                before = game.to_dict()
                b_id = "R01" if code in BINARY_CODES else None
                with self.assertRaises(AnswerError) as raised:
                    game.perform(op, "B01", b_id, answer="0 0;0 0", **params)
                self.assertEqual(str(raised.exception), "Answer is incorrect. Try again.")
                self.assertEqual(game.to_dict(), before)

    def test_rectangular_column_indices_use_column_count(self):
        a, b = [[1, 2, 3], [4, 5, 6]], [[7, 8, 9], [10, 11, 12]]
        cases = (
            ("add_vector", {"axis": "column", "source": 2, "target": 2},
             [[1, 2, 12], [4, 5, 18]]),
            ("replace_vector", {"axis": "column", "source": 2, "target": 2},
             [[1, 2, 9], [4, 5, 12]]),
            ("append_vector", {"axis": "column", "source": 2},
             [[1, 2, 3, 9], [4, 5, 6, 12]]),
            ("swap", {"axis": "column", "i": 0, "j": 2}, [[3, 2, 1], [6, 5, 4]]),
            ("combine_vectors", {"axis": "column", "source": 2, "target": 0, "delta": 1},
             [[4, 2, 3], [10, 5, 6]]),
            ("entry_zero", {"i": 1, "j": 2}, [[1, 2, 3], [4, 5, 0]]),
        )
        for code, params, expected in cases:
            with self.subTest(code=code):
                game, op = controlled_hand(code, a, b)
                b_id = "R01" if code in BINARY_CODES else None
                self.assertEqual(game.calculate(op, "B01", b_id, **params), maths.matrix(expected))

    def test_invalid_indices_dimensions_and_parameters_are_atomic(self):
        a = [[1, 2, 3], [4, 5, 6]]
        cases = (
            ("add_vector", {"axis": "row", "source": 2, "target": 0}),
            ("replace_vector", {"axis": "column", "source": 3, "target": 0}),
            ("add_vector", {"axis": "column", "source": 0, "target": 3}),
            ("append_vector", {"axis": "column", "source": -1}),
            ("swap", {"axis": "row", "i": 0, "j": 2}),
            ("swap", {"axis": "diagonal", "i": 0, "j": 1}),
            ("combine_vectors", {"axis": "column", "source": 1, "target": 1, "delta": 1}),
            ("combine_vectors", {"axis": "row", "source": 0, "target": 1, "delta": True}),
            ("entry_plus", {"i": True, "j": 0}),
            ("entry_minus", {"i": 0.0, "j": 0}),
            ("entry_zero", {"i": 0, "j": "1"}),
            ("lu", {"factor": "U"}),
            ("inverse", {}),
        )
        for code, params in cases:
            with self.subTest(code=code, params=params):
                game, op = controlled_hand(code, a, a)
                before = game.to_dict()
                b_id = "R01" if code in BINARY_CODES else None
                with self.assertRaises(GameError):
                    game.perform(op, "B01", b_id, **params)
                self.assertEqual(game.to_dict(), before)

    def test_vector_source_lengths_and_append_dimension_limit(self):
        for axis, a, b in (
            ("row", [[1, 2, 3], [4, 5, 6]], [[1, 2], [3, 4]]),
            ("column", [[1, 2], [3, 4]], [[1, 2], [3, 4], [5, 6]]),
            ("column", [[1, 2, 3, 4], [5, 6, 7, 8]], [[1, 2], [3, 4]]),
        ):
            game, op = controlled_hand("append_vector", a, b)
            before = game.to_dict()
            with self.subTest(axis=axis, shape=maths.shape(game.matrices[0].values)), self.assertRaises(GameError):
                game.perform(op, "B01", "R01", axis=axis, source=0)
            self.assertEqual(game.to_dict(), before)


class SaveAndParsingEdgeTests(unittest.TestCase):
    def test_fraction_canonicalization_and_rectangular_parse(self):
        self.assertEqual(parse_answer('[["2/4", "+2", 0], ["-6/3", "0/7", "4/6"]]'),
                         [[Fraction(1, 2), Fraction(2), Fraction(0)],
                          [Fraction(-2), Fraction(0), Fraction(2, 3)]])
        for value in ('[[1,2],[3,4,5]]', [[1, 2], [3, False]], "1/0 2;3 4", "1 2;;3 4"):
            with self.subTest(value=value), self.assertRaises(AnswerError):
                parse_answer(value)

    def test_damaged_save_containers_are_rejected_at_restore(self):
        mutations = (
            ("history", None), ("history", {}), ("history", [None]),
            ("seen", []), ("seen", ["not a matrix"]),
            ("rng_state", []), ("rng_state", [3]),
            ("last_draw", None), ("next_result", True),
        )
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                state = Game(seed=11).to_dict()
                state[key] = value
                with self.assertRaises(GameError):
                    Game.from_dict(state)

    def test_duplicate_piles_and_unknown_blue_identity_are_rejected(self):
        for mutation in ("duplicate_operation", "duplicate_red", "unknown_blue"):
            with self.subTest(mutation=mutation):
                state = Game(seed=11).to_dict()
                if mutation == "duplicate_operation":
                    state["op_draw"].append(state["operations"][0])
                elif mutation == "duplicate_red":
                    red = next(c for c in state["matrices"] if c["color"] == "red")
                    state["red_discard"].append(red["id"])
                else:
                    state["matrices"][0]["id"] = "not-a-physical-or-result-card"
                with self.assertRaises(GameError):
                    Game.from_dict(state)


if __name__ == "__main__":
    unittest.main()
