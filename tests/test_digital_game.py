"""Behavioral tests for the UI-independent solo session."""

from fractions import Fraction
from copy import deepcopy
from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from digital.game import (AnswerError, BUILTIN_OPERATIONS, Game, GameError, MatrixCard,
                          REMOVED_OPERATION_CODES, parse_answer)
import matrix as maths


DECK = json.loads((Path(__file__).resolve().parents[1] /
                   "expansion_split/generated/deck.json").read_text())


def hand(codes, matrices, *, mode="auto", objective="C02+"):
    """Build controlled hands using physical deck IDs and the snapshot API."""
    game = Game(mode=mode, objective_id=objective, seed=19, blue_id="B01")
    state = game.to_dict()
    available = list(game._ops.values())
    selected = []
    for code in codes:
        if code in REMOVED_OPERATION_CODES:
            continue
        card = next(c for c in available if c["code"] == code)
        available.remove(card)
        selected.append(card["id"])
    state["operations"] = selected
    state["op_draw"] = [c["id"] for c in available]
    state["op_discard"] = []
    state["matrices"] = [{"id": i, "color": color, "values": values}
                         for i, color, values in matrices]
    state["red_draw"] = [c["id"] for c in DECK["red"]
                         if c["id"] not in {i for i, color, _ in matrices if color == "red"}]
    state["red_discard"] = []
    state["seen"] = [json.dumps(values, separators=(",", ":"))
                     for _, color, values in matrices if color == "blue"]
    return Game.from_dict(state)


class AnswerParsingTests(unittest.TestCase):
    def test_supported_exact_formats(self):
        expected = [[Fraction(1, 2), Fraction(-2)], [Fraction(3), Fraction(4, 5)]]
        for text in ("1/2 -2; 3 4/5", "1/2,-2\n3,4/5", '[["1/2", -2], [3, "4/5"]]'):
            self.assertEqual(parse_answer(text), expected)
        self.assertEqual(parse_answer(expected), expected)

    def test_malformed_or_excessive_input(self):
        for value in ("1 2", "1 2; 3", "1 2;3 1/0", "1e2 0;0 1", "nan 0;0 1",
                      "__import__('os') 0;0 1", '[[true,0],[0,1]]', "9" * 81 + " 0;0 1",
                      '[[1.0,0],[0,1]]', "1 2;3 4;", [[1, 2]] * 5, "1" * 4097):
            with self.subTest(value=str(value)[:40]), self.assertRaises(AnswerError):
                parse_answer(value)


class DigitalGameTests(unittest.TestCase):
    def test_seed_and_initial_draw(self):
        a, b = Game(seed=42), Game(seed=42)
        self.assertEqual(a.to_dict(), b.to_dict())
        self.assertEqual((a.turn, a.score, len(a.operations), len(a.matrices)), (1, 0, 3, 4))
        self.assertEqual(sum(c.color == "blue" for c in a.matrices), 1)
        self.assertEqual(Game(blue_id="B02").matrices[0].id, "B02")

    def test_builtins_remain_available_without_dealt_cards(self):
        game = hand([], [("B01", "blue", [[1, 0], [0, 1]]),
                         ("B02", "blue", [[2, 0], [0, 2]]),
                         ("R01", "red", [[3, 0], [0, 3]])])
        self.assertEqual(set(BUILTIN_OPERATIONS), {"builtin:add", "builtin:multiply"})
        for operation_id, expected in (("builtin:add", [[3, 0], [0, 3]]),
                                       ("builtin:multiply", [[2, 0], [0, 2]])):
            before = game.to_dict()
            game.operation(operation_id)["name"] = "Detached copy"
            self.assertEqual(game.calculate(operation_id, "B01", "B02"), maths.matrix(expected))
            self.assertEqual(game.to_dict(), before)
            game.perform(operation_id, "B01", "B02")
            self.assertEqual(game._op_draw, before["op_draw"])
            self.assertEqual(game._op_discard, [])
            self.assertEqual(game.operations, [])
        before = game.to_dict()
        game.calculate("builtin:add", "B01", "R01")
        self.assertEqual(game.to_dict(), before)
        game.perform("builtin:add", "B01", "R01")
        self.assertEqual(game._red_discard, ["R01"])
        self.assertEqual(Game.from_dict(game.to_dict()).to_dict(), game.to_dict())

    def test_dealt_deck_excludes_builtins_for_every_turn(self):
        game = Game(seed=1)
        self.assertEqual(len(game._ops), 90)
        for turn in range(1, 9):
            self.assertEqual(len(game.last_draw["red"]), 3)
            self.assertTrue(all(c["code"] not in REMOVED_OPERATION_CODES for c in game.operations))
            self.assertTrue(all(game._ops[i]["code"] not in REMOVED_OPERATION_CODES
                                for i in game._op_draw + game._op_discard))
            if turn < 8:
                game.end_turn()

    def test_builtins_have_separate_two_use_limits_reset_only_on_next_turn(self):
        game = hand([], [("B01", "blue", [[1, 0], [0, 1]]),
                         ("B02", "blue", [[2, 0], [0, 2]])])
        for op in ("builtin:add", "builtin:multiply"):
            self.assertEqual(game.builtin_remaining(op), 2)
            for remaining in (1, 0):
                before = game.to_dict()
                for _ in range(3):
                    game.calculate(op, "B01", "B02")
                self.assertEqual(game.to_dict(), before)
                game.perform(op, "B01", "B02")
                self.assertEqual(game.builtin_remaining(op), remaining)
                game = Game.from_dict(game.to_dict())
                self.assertEqual(game.builtin_remaining(op), remaining)
            before = game.to_dict()
            for action in (game.calculate, game.perform):
                with self.assertRaisesRegex(GameError, "both uses spent"):
                    action(op, "B01", "B02")
                self.assertEqual(game.to_dict(), before)
        game.end_turn()
        for op in BUILTIN_OPERATIONS:
            self.assertEqual(game.builtin_remaining(op), 2)
            game.perform(op, "B01", "B02")
        while not game.finished:
            game.end_turn()
        self.assertEqual(game.builtin_remaining("builtin:add"), 0)

    def test_wrong_answers_and_invalid_moves_never_spend_builtin_uses(self):
        game = hand([], [("B01", "blue", [[1, 0], [0, 1]]),
                         ("B02", "blue", [[2, 0], [0, 2]])], mode="student")
        for op, expected in (("builtin:add", "3 0;0 3"), ("builtin:multiply", "2 0;0 2")):
            before = game.to_dict()
            with self.assertRaises(AnswerError):
                game.perform(op, "B01", "B02", answer="0 0;0 0")
            with self.assertRaises(GameError):
                game.perform(op, "B01", "B01", answer=expected)
            self.assertEqual(game.to_dict(), before)
            self.assertEqual(game.builtin_remaining(op), 2)
            game.perform(op, "B01", "B02", answer=expected)
            self.assertEqual(game.builtin_remaining(op), 1)

    def test_rebalanced_deck_and_added_copy_can_be_played_and_restored(self):
        game = hand([], [("B01", "blue", [[2, 1], [4, 3]])])
        counts = Counter(c["code"] for c in game._ops.values())
        self.assertEqual(counts, {"subtract": 5, "add_vector": 5, "append_vector": 4,
                                 "replace_vector": 4, "transpose": 3, "swap": 3,
                                 "shift_plus": 4, "shift_minus": 4, "negate": 4,
                                 "double": 4, "inverse": 5, "lu": 5,
                                 "entry_plus": 12, "entry_minus": 12,
                                 "entry_zero": 8, "combine_vectors": 8})
        extra = next(i for i, c in game._ops.items()
                     if i not in game._original_ops and c["code"] == "lu")
        state = game.to_dict()
        state["op_draw"].remove(extra)
        state["operations"].append(extra)
        game = Game.from_dict(state)
        result = game.perform(extra, "B01", factor="U")
        self.assertEqual(result["result"].values, maths.matrix([[2, 1], [0, 1]]))
        self.assertEqual(game._op_discard, [extra])
        self.assertEqual(Game.from_dict(game.to_dict()).to_dict(), game.to_dict())

    def test_v2_save_adds_new_copies_once_and_retains_exhausted_legacy_turn(self):
        game = hand([], [("B01", "blue", [[1, 0], [0, 1]]),
                         ("B02", "blue", [[2, 0], [0, 2]])])
        # Version 2 allowed unlimited uses; these committed results must survive.
        with patch.object(Game, "builtin_remaining", return_value=2):
            for _ in range(3):
                game.perform("builtin:add", "B01", "B02")
        state = game.to_dict()
        state["version"] = 2
        for name in ("operations", "op_draw", "op_discard"):
            state[name] = [i for i in state[name] if i in game._original_ops]
        state["last_draw"]["operations"] = []
        before = deepcopy(state)
        restored = Game.from_dict(state)
        self.assertEqual(state, before)
        after = restored.to_dict()
        self.assertEqual(after, Game.from_dict(state).to_dict())
        for name in ("operations", "op_discard", "matrices", "history", "score", "rng_state", "last_draw"):
            self.assertEqual(after[name], state[name])
        self.assertEqual([i for i in after["op_draw"] if i in game._original_ops], state["op_draw"])
        self.assertEqual(len(after["op_draw"]), len(state["op_draw"]) + 20)
        self.assertEqual(Game.from_dict(after).to_dict(), after)
        self.assertEqual(restored.builtin_remaining("builtin:add"), 0)
        self.assertEqual(restored.builtin_remaining("builtin:multiply"), 2)
        with self.assertRaises(GameError):
            restored.perform("builtin:add", "B01", "B02")
        restored.end_turn()
        self.assertEqual(restored.builtin_remaining("builtin:add"), 2)
        restored.perform("builtin:add", "B01", "B02")

    def test_legacy_save_migrates_without_redealing_or_losing_results(self):
        game = Game(seed=7, blue_id="B01")
        red = next(c.id for c in game.matrices if c.color == "red")
        game.get_matrix(red).values = deepcopy(game.get_matrix("B01").values)
        game.perform("builtin:add", "B01", red)
        state = game.to_dict()
        state["version"] = 1
        for name in ("operations", "op_draw", "op_discard"):
            state[name] = [i for i in state[name] if i in game._original_ops]
        removed = [c["id"] for c in DECK["operations"]
                   if c["code"] in REMOVED_OPERATION_CODES]
        state["op_discard"].append("O01")
        state["op_draw"].extend(i for i in removed if i != "O01")
        state["history"][0]["operation_id"] = "O01"
        extras = [state["red_draw"].pop() for _ in range(2)]
        reds = {c["id"]: c for c in DECK["red"]}
        state["matrices"].extend({"id": i, "color": "red", "values": reds[i]["matrix"]}
                                 for i in extras)
        state["last_draw"]["red"].extend(extras)
        state["last_draw"]["operations"] = ["O02"]
        original = deepcopy(state)
        restored = Game.from_dict(state)
        saved = restored.to_dict()
        self.assertEqual(state, original)
        self.assertEqual(saved["version"], 4)
        for name in ("matrices", "history", "seen", "next_result", "score", "turn", "rng_state",
                     "red_draw", "red_discard"):
            self.assertEqual(saved[name], state[name])
        for name in ("operations", "op_draw", "op_discard"):
            self.assertEqual([i for i in saved[name] if i in game._original_ops],
                             [i for i in state[name] if i not in removed])
        self.assertEqual(len(saved["op_draw"]), len(state["op_draw"]) - 9 + 20)
        self.assertEqual(restored.builtin_remaining("builtin:add"), 1)
        self.assertEqual(saved["last_draw"]["operations"], [])
        self.assertEqual(len(saved["last_draw"]["red"]), 3)
        self.assertEqual(Game.from_dict(saved).to_dict(), saved)
        restored.perform("builtin:multiply", "B01", "G0001")
        self.assertEqual(len(restored.history), 2)
        self.assertEqual(Game.from_dict(restored.to_dict()).to_dict(), restored.to_dict())

        # A migration must not hide damaged retired-card partitions.
        for mutate in (lambda s: s["op_draw"].append("O01"),
                       lambda s: s["op_draw"].remove("O02")):
            damaged = deepcopy(original)
            mutate(damaged)
            with self.assertRaises(GameError):
                Game.from_dict(damaged)

    def test_new_save_rejects_retired_and_builtin_physical_piles_and_old_draw_size(self):
        for name, value in (("op_draw", "O01"), ("op_discard", "builtin:add"),
                            ("operations", "O11"), ("last_draw", None)):
            state = Game(seed=7).to_dict()
            if name == "last_draw":
                state[name]["red"].append(state["red_draw"][0])
            else:
                state[name].append(value)
            with self.subTest(name=name), self.assertRaises(GameError):
                Game.from_dict(state)

    def test_removal_excludes_cards_from_play_and_recycling(self):
        game = hand(["transpose"], [("B01", "blue", [[1, 0], [0, 1]]),
                                    ("R01", "red", [[2, 0], [0, 2]])])
        operation = game.operations[0]["id"]
        game.remove_card(operation)
        game.remove_card("R01")
        self.assertEqual(game._op_discard, [])
        self.assertEqual(game._red_discard, [])
        before = game.to_dict()
        for card_id in (operation, "R01", "builtin:add", "C01", "unknown"):
            with self.assertRaises(GameError):
                game.remove_card(card_id)
            self.assertEqual(game.to_dict(), before)
        with self.assertRaises(GameError):
            game.operation(operation)
        with self.assertRaises(GameError):
            game.get_matrix("R01")
        # Force a recycle with all remaining physical cards already held.
        game.operations = [deepcopy(c) for i, c in game._ops.items() if i != operation]
        game._op_draw = []
        recyclable_op = game.operations.pop()["id"]
        game._op_discard = [recyclable_op]
        game.matrices.extend(MatrixCard(i, "red", maths.matrix(c["matrix"]))
                             for i, c in game._reds.items() if i != "R01")
        game._red_draw = []
        recyclable_red = game.matrices.pop().id
        game._red_discard = [recyclable_red]
        game = Game.from_dict(game.to_dict())
        game.end_turn()
        self.assertEqual(game.last_draw, {"operations": [recyclable_op], "red": [recyclable_red]})
        self.assertNotIn(operation, [c["id"] for c in game.operations])
        self.assertNotIn("R01", [c.id for c in game.matrices])
        self.assertEqual(Game.from_dict(game.to_dict()).to_dict(), game.to_dict())

    def test_removed_blue_cards_keep_history_score_and_deduplication(self):
        game = hand(["negate", "negate"], [("B01", "blue", [[1, 0], [0, 1]]),
                                          ("B02", "blue", [[1, 0], [0, 1]])], objective="C02-")
        first = game.perform(game.operations[0]["id"], "B01")["result"]
        self.assertEqual(game.score, 1)
        history = deepcopy(game.history)
        game.remove_card("B01")
        game.remove_card(first.id)
        game = Game.from_dict(game.to_dict())
        self.assertEqual(game.history, history)
        self.assertEqual(game.score, 1)
        with self.assertRaises(GameError):
            game.get_matrix(first.id)
        second = game.perform(game.operations[0]["id"], "B02")
        self.assertFalse(second["scored"])
        self.assertEqual(game.score, 1)
        game.remove_card("B02")
        game.remove_card(second["result"].id)
        self.assertEqual(game.matrices, [])
        self.assertEqual(Game.from_dict(game.to_dict()).to_dict(), game.to_dict())

    def test_removed_records_must_be_disjoint_and_old_saves_default_to_empty(self):
        state = Game(seed=4).to_dict()
        old = deepcopy(state)
        old["version"] = 3
        del old["removed_operations"], old["removed_matrices"]
        self.assertEqual(Game.from_dict(old).to_dict(), state)
        for mutate in (
            lambda s: s["removed_operations"].append(s["operations"][0]),
            lambda s: s["removed_operations"].append("builtin:add"),
            lambda s: s["removed_matrices"].append(deepcopy(s["matrices"][0])),
            lambda s: s.update(removed_matrices=None),
            lambda s: s.update(removed_operations=None),
        ):
            damaged = deepcopy(state)
            mutate(damaged)
            with self.assertRaises(GameError):
                Game.from_dict(damaged)

    def test_student_and_automatic_have_identical_commits(self):
        matrices = [("B01", "blue", [[2, 0], [0, 3]]), ("R01", "red", [[1, 0], [0, 1]])]
        auto = hand(["inverse", "multiply"], matrices)
        student = hand(["inverse", "multiply"], matrices, mode="student")
        op = auto.operations[0]["id"]
        before = auto.to_dict()
        expected = auto.calculate(op, "B01")
        self.assertEqual(auto.to_dict(), before)
        self.assertEqual(expected[0][0], Fraction(1, 2))
        a = auto.perform(op, "B01")
        s = student.perform(op, "B01", answer="1/2 0;0 1/3")
        self.assertEqual(a, s)
        ad, sd = auto.to_dict(), student.to_dict()
        ad.pop("mode"); sd.pop("mode")
        self.assertEqual(ad, sd)
        self.assertEqual(auto.get_matrix("B01").values, maths.matrix([[2, 0], [0, 3]]))

    def test_wrong_and_invalid_answers_do_not_commit_or_reveal_result(self):
        game = hand(["inverse"], [("B01", "blue", [[2, 0], [0, 3]])], mode="student")
        op = game.operations[0]["id"]
        state = game.to_dict()
        for answer in ("1 0;0 1", "not a matrix", None):
            with self.subTest(answer=answer), self.assertRaises(AnswerError) as raised:
                game.perform(op, "B01", answer=answer)
            self.assertNotIn("1/2", str(raised.exception))
            self.assertNotIn("1/3", str(raised.exception))
            self.assertEqual(game.to_dict(), state)

    def test_all_binary_color_pairs_and_only_red_consumption(self):
        for first in ("blue", "red"):
            for second in ("blue", "red"):
                aid = "B01" if first == "blue" else "R01"
                bid = "B02" if second == "blue" else "R02"
                matrices = [(aid, first, [[1, 0], [0, 1]]),
                            (bid, second, [[1, 0], [0, 1]])]
                if first == second == "red":
                    matrices.append(("B01", "blue", [[3, 0], [0, 3]]))
                game = hand(["add"], matrices)
                op = "builtin:add"
                result = game.perform(op, aid, bid)["result"]
                self.assertEqual(result.color, "blue")
                self.assertEqual(result.values, maths.matrix([[2, 0], [0, 2]]))
                self.assertEqual(len(game.operations), 0)
                for i, color in ((aid, first), (bid, second)):
                    self.assertEqual(any(c.id == i for c in game.matrices), color == "blue")

    def test_same_physical_card_and_bad_parameters_are_transactional(self):
        game = hand(["add", "entry_plus", "swap"], [("B01", "blue", [[1, 0], [0, 1]])])
        state = game.to_dict()
        for op, kwargs in (("builtin:add", {"b_id": "B01"}),
                           (game.operations[0]["id"], {"i": 4, "j": 0}),
                           (game.operations[1]["id"], {"axis": "row", "i": 0, "j": 0})):
            with self.assertRaises(GameError):
                game.perform(op, "B01", **kwargs)
            self.assertEqual(game.to_dict(), state)

    def test_single_entry_costs_one_operation_and_red_unary_is_consumed(self):
        game = hand(["entry_plus"], [("B01", "blue", [[2, 0], [0, 2]]),
                                     ("R01", "red", [[0, 0], [0, 1]])])
        result = game.perform(game.operations[0]["id"], "R01", i=0, j=0)
        self.assertTrue(result["scored"])
        self.assertEqual(game.score, 1)
        self.assertEqual(game.operations, [])
        self.assertEqual({c.id for c in game.matrices}, {"B01", result["result"].id})

    def test_scoring_deduplicates_values_and_starting_blue(self):
        game = hand(["transpose", "transpose", "transpose"],
                    [("B01", "blue", [[1, 0], [0, 1]]),
                     ("R01", "red", [[1, 0, 0], [0, 1, 0], [0, 0, 1]])])
        first = game.perform(game.operations[0]["id"], "B01")
        self.assertFalse(first["scored"])
        second = game.perform(game.operations[0]["id"], "R01")
        self.assertTrue(second["scored"])
        third = game.perform(game.operations[0]["id"], second["result"].id)
        self.assertFalse(third["scored"])
        self.assertEqual(game.score, 1)
        self.assertEqual(len(game.history), 3)

    def test_vector_operations_and_lu(self):
        for code, params, expected in (
            ("add_vector", {"axis": "row", "source": 1, "target": 0}, [[1, 1], [0, 1]]),
            ("replace_vector", {"axis": "column", "source": 1, "target": 0}, [[0, 0], [1, 1]]),
            ("append_vector", {"axis": "row", "source": 0}, [[1, 0], [0, 1], [1, 0]]),
            ("combine_vectors", {"axis": "row", "source": 0, "target": 1, "delta": -1}, [[1, 0], [-1, 1]]),
            ("lu", {"factor": "L"}, [[1, 0], [0, 1]])):
            game = hand([code], [("B01", "blue", [[1, 0], [0, 1]]),
                                 ("R01", "red", [[1, 0], [0, 1]])])
            b = "R01" if code in {"add_vector", "replace_vector", "append_vector"} else None
            self.assertEqual(game.calculate(game.operations[0]["id"], "B01", b, **params),
                             maths.matrix(expected))

    def test_invalid_mathematics_and_fixed_signs_leave_state_unchanged(self):
        game = hand(["inverse", "multiply", "append_vector", "entry_plus", "lu"],
                    [("B01", "blue", [[0, 1], [0, 0]]),
                     ("R01", "red", [[1, 0, 0], [0, 1, 0]]),
                     ("R02", "red", [[1, 0], [0, 1], [0, 0], [0, 0]])])
        operations = [c["id"] for c in game.operations]
        cases = ((operations[0], "B01", None, {}), ("builtin:multiply", "R01", "B01", {}),
                 (operations[1], "R02", "B01", {"axis": "row", "source": 0}),
                 (operations[2], "B01", None, {"i": 0, "j": 0, "delta": -1}),
                 (operations[3], "B01", None, {"factor": "L"}))
        state = game.to_dict()
        for op, a, b, parameters in cases:
            with self.subTest(operation=op), self.assertRaises(GameError):
                game.perform(op, a, b, **parameters)
            self.assertEqual(game.to_dict(), state)

    def test_eight_turns_allow_passing_carry_hands_and_draw_fewer(self):
        game = Game(seed=4)
        first_ops = {c["id"] for c in game.operations}
        for turn in range(1, 9):
            self.assertEqual(game.turn, turn)
            self.assertFalse(game.finished)
            game.end_turn()
        self.assertTrue(game.finished)
        self.assertEqual(game.turn, 8)
        self.assertTrue(first_ops <= {c["id"] for c in game.operations})
        self.assertEqual(len(game.operations), 24)
        self.assertEqual(sum(c.color == "red" for c in game.matrices), 24)
        self.assertEqual(len(game.last_draw["red"]), 3)
        with self.assertRaises(GameError):
            game.end_turn()
        with self.assertRaises(GameError):
            game.perform(game.operations[0]["id"], game.matrices[0].id)

    def test_recycling_only_discards_excludes_held_cards(self):
        # All but one operation are held. The single discarded card can recycle
        # once, but drawing it cannot manufacture two additional copies.
        game = Game(seed=1)
        state = game.to_dict()
        transpose = next(c["id"] for c in DECK["operations"] if c["code"] == "transpose")
        state["operations"] = [i for i in game._ops if i != transpose]
        state["op_draw"], state["op_discard"] = [], [transpose]
        state["matrices"] += [{"id": c["id"], "color": "red", "values": c["matrix"]}
                              for c in DECK["red"] if c["id"] not in
                              {m["id"] for m in state["matrices"]}]
        state["red_draw"], state["red_discard"] = [], []
        game = Game.from_dict(state)
        game.end_turn()
        self.assertEqual(game.last_draw, {"operations": [transpose], "red": []})
        self.assertEqual(len({c["id"] for c in game.operations}), 90)
        red = next(c for c in game.matrices if c.color == "red")
        game.perform(transpose, red.id)
        game.end_turn()
        self.assertEqual(game.last_draw, {"operations": [transpose], "red": [red.id]})
        self.assertEqual(len({c.id for c in game.matrices}), len(game.matrices))

    def test_roundtrip_preserves_exact_values_history_rng_and_dedupe(self):
        game = hand(["inverse", "transpose"], [("B01", "blue", [[2, 0], [0, 3]])])
        result = game.perform(game.operations[0]["id"], "B01")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            game.save(path)
            restored = Game.load(path)
        self.assertEqual(restored.to_dict(), game.to_dict())
        self.assertEqual(restored.get_matrix(result["result"].id).values[1][1], Fraction(1, 3))
        for _ in range(7):
            game.end_turn(); restored.end_turn()
            self.assertEqual(restored.to_dict(), game.to_dict())
        bad = game.to_dict()
        bad["deck"]["sha256"] = "wrong"
        with self.assertRaisesRegex(GameError, "different deck"):
            Game.from_dict(bad)

    def test_saved_history_and_generated_ids_must_be_coherent(self):
        game = hand(["transpose", "transpose"],
                    [("B01", "blue", [[2, 0], [0, 2]]),
                     ("R01", "red", [[1, 0], [0, 1]])])
        game.perform(game.operations[0]["id"], "R01")
        original = game.to_dict()
        mutations = (
            lambda s: s.update(next_result=1),
            lambda s: s.update(score=7),
            lambda s: s["history"][0].pop("operation_title"),
            lambda s: s["history"][0].update(parameters=[]),
            lambda s: s["history"][0].update(result=[[0, 0], [0, 0]]),
            lambda s: s["history"][0].update(scored=1),
            lambda s: s["history"][0].update(turn=9),
            lambda s: s["history"][0].update(a_id="G0002"),
            lambda s: s["matrices"][0].update(id="R02"),
            lambda s: s["matrices"][-1].update(id="G0000"),
            lambda s: s["matrices"][-1].update(id="B02"),
            lambda s: s.update(seen=[s["seen"][0]]),
            lambda s: s["last_draw"].update(red=["R99"]),
            lambda s: s.update(op_draw="O01"),
        )
        # Both retained blue values must appear; choose the omitted result
        # explicitly rather than depending on the sorted canonical ordering.
        starting_key = json.dumps([[2, 0], [0, 2]], separators=(",", ":"))
        for mutate in mutations:
            state = deepcopy(original)
            mutate(state)
            if state.get("seen") != original["seen"]:
                state["seen"] = [starting_key]
            with self.subTest(state=state), self.assertRaises(GameError):
                Game.from_dict(state)
        restored = Game.from_dict(json.loads(json.dumps(original)))
        duplicate = restored.perform(restored.operations[0]["id"], "G0001")
        self.assertFalse(duplicate["scored"])
        self.assertEqual(restored.score, 1)

    def test_atomic_save_creates_parent_and_preserves_old_file_on_failure(self):
        game = Game(seed=3)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "nested" / "session.json"
            game.save(destination)
            old = destination.read_bytes()
            game.end_turn()
            with patch("digital.game.os.replace", side_effect=OSError("write interrupted")):
                with self.assertRaises(OSError):
                    game.save(destination)
            self.assertEqual(destination.read_bytes(), old)
            self.assertEqual(list(destination.parent.iterdir()), [destination])
            game.save(destination)
            self.assertEqual(Game.load(destination).to_dict(), game.to_dict())


if __name__ == "__main__":
    unittest.main()
