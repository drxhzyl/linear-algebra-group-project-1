"""Exact, transactional solo sessions; no UI or implicit filesystem writes."""

from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import random
import re
import tempfile

import matrix as maths
from card_layout import OP_COPY


DECK_PATH = Path(__file__).resolve().parents[1] / "expansion_split/generated/deck.json"
REMOVED_OPERATION_CODES = frozenset({"add", "multiply"})
BUILTIN_TURN_LIMIT = 2
# Extra digital copies keep the original physical IDs and saved histories intact.
BOOSTED_OPERATION_COUNTS = {"lu": 5, "inverse": 5, "negate": 4, "double": 4,
                            "replace_vector": 4, "shift_plus": 4, "shift_minus": 4}
BUILTIN_OPERATIONS = {
    f"builtin:{code}": {"id": f"builtin:{code}", "kind": "operation", "code": code,
                        "name": OP_COPY[code][0], "rule": OP_COPY[code][1], "builtin": True}
    for code in ("add", "multiply")
}
BINARY_CODES = frozenset({"add", "subtract", "multiply", "add_vector",
                          "append_vector", "replace_vector"})
Matrix = list[list[Fraction]]
_NUMBER = re.compile(r"[+-]?\d{1,80}(?:/[+-]?\d{1,80})?", re.ASCII)


class GameError(ValueError):
    """An action is unavailable or its mathematical parameters are invalid."""


class AnswerError(GameError):
    """A student answer was rejected without committing the action."""


def parse_answer(value) -> Matrix:
    """Read 2–4 by 2–4 integers/fractions; never evaluate code.

    Accept nested lists (including Fraction entries), JSON nested lists, or
    newline/semicolon rows with comma/space columns. Limit input to 4096 chars
    and each integer part to 80 digits. Decimal/exponent notation is excluded.
    """
    try:
        if isinstance(value, str):
            if len(value) > 4096:
                raise ValueError
            text = value.strip()
            if text.startswith("["):
                value = json.loads(text)
            else:
                rows = re.split(r"[;\n]", text)
                if any(not row.strip() for row in rows):
                    raise ValueError
                value = [re.split(r"[\s,]+", row.strip()) for row in rows]
        if not isinstance(value, list) or not 2 <= len(value) <= 4:
            raise ValueError
        if any(not isinstance(row, list) or not 2 <= len(row) <= 4 for row in value):
            raise ValueError
        if len({len(row) for row in value}) != 1:
            raise ValueError
        result = []
        for row in value:
            parsed = []
            for x in row:
                if isinstance(x, bool) or not isinstance(x, (int, str, Fraction)):
                    raise ValueError
                token = str(x).strip()
                if not _NUMBER.fullmatch(token):
                    raise ValueError
                parsed.append(Fraction(token))
            result.append(parsed)
        return result
    except (ValueError, TypeError, ZeroDivisionError, OverflowError, RecursionError) as exc:
        raise AnswerError("Enter a rectangular 2–4 by 2–4 matrix using integers or fractions.") from exc


@dataclass
class MatrixCard:
    id: str
    color: str
    values: Matrix

    def to_dict(self):
        return {"id": self.id, "color": self.color, "values": maths.dump(self.values)}


def operation_parameters(code):
    """Required parameter names for the interface; indices are zero based."""
    if code in {"add_vector", "replace_vector", "combine_vectors"}:
        return ("axis", "source", "target") + (("delta",) if code == "combine_vectors" else ())
    if code == "append_vector":
        return ("axis", "source")
    if code == "swap":
        return ("axis", "i", "j")
    if code in {"entry_plus", "entry_minus", "entry_zero", "entry_tweak"}:
        return ("i", "j") + (("delta",) if code == "entry_tweak" else ())
    return ("factor",) if code == "lu" else ()


def _key(values):
    return json.dumps(maths.dump(values), separators=(",", ":"))


def _deck():
    raw = DECK_PATH.read_bytes()
    deck = json.loads(raw)
    for card in deck["operations"]:
        card["name"], card["rule"] = OP_COPY[card["code"]]
    return deck, hashlib.sha256(raw).hexdigest()


def _digital_operations(original):
    operations = deepcopy(original)
    for code, target in BOOSTED_OPERATION_COUNTS.items():
        copies = [card for card in original.values() if card["code"] == code]
        for copy_number in range(len(copies) + 1, target + 1):
            card = dict(copies[0], id=f"{copies[0]['id']}x{copy_number}")
            operations[card["id"]] = card
    return operations


class Game:
    """Eight solo turns. Blue operands stay; red operands and dealt operations discard.

    Each successful action produces a new blue card. End-turn may be used with
    no plays. Unused hands carry over, and only discarded physical cards recycle.
    Addition and multiplication each allow two commits per turn without a card.
    """

    def __init__(self, mode="auto", objective_id="C01", seed=0, blue_id=None):
        if mode not in {"auto", "student"}:
            raise GameError("Mode must be 'auto' or 'student'.")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise GameError("Seed must be an integer.")
        self._deck, self._deck_hash = _deck()
        self._legacy_ops = {c["id"]: c for c in self._deck["operations"]}
        self._original_ops = {i: c for i, c in self._legacy_ops.items()
                              if c["code"] not in REMOVED_OPERATION_CODES}
        self._ops = _digital_operations(self._original_ops)
        self._reds = {c["id"]: c for c in self._deck["red"]}
        objectives = {c["id"]: c for c in self._deck["objectives"]}
        objective_id = objective_id.upper() if isinstance(objective_id, str) else ""
        objective_id = "C02+" if objective_id == "C02" else objective_id
        if objective_id not in objectives:
            raise GameError("Unknown objective card.")
        self.mode, self.seed = mode, seed
        self.objective = deepcopy(objectives[objective_id])
        self._rng = random.Random(seed)
        blues = {c["id"]: c for c in self._deck["blue"]}
        if blue_id is None:
            blue_id = self._rng.choice(list(blues))
        if blue_id not in blues:
            raise GameError("Unknown starting blue card.")
        start = blues[blue_id]
        self.matrices = [MatrixCard(blue_id, "blue", maths.matrix(start["matrix"]))]
        self.operations = []
        self._removed_operations, self._removed_matrices = [], []
        self.turn, self.finished, self.score = 1, False, 0
        self.history = []
        self._seen = {_key(self.matrices[0].values)}
        self._next_result = 1
        self._op_draw, self._red_draw = list(self._ops), list(self._reds)
        self._op_discard, self._red_discard = [], []
        self._rng.shuffle(self._op_draw)
        self._rng.shuffle(self._red_draw)
        self._draw_turn()

    def _active(self):
        if self.finished:
            raise GameError("The eight-turn game has finished.")

    def get_matrix(self, card_id):
        for card in self.matrices:
            if card.id == card_id:
                return card
        raise GameError("Choose a matrix card currently available.")

    def operation(self, operation_id):
        if isinstance(operation_id, str) and operation_id in BUILTIN_OPERATIONS:
            return deepcopy(BUILTIN_OPERATIONS[operation_id])
        for card in self.operations:
            if card["id"] == operation_id:
                return card
        raise GameError("Choose an operation card currently in your hand.")

    def builtin_remaining(self, operation_id):
        """Count committed uses, including physical add/multiply in old saves."""
        if operation_id not in BUILTIN_OPERATIONS:
            raise GameError("Choose a built-in operation.")
        if self.finished:
            return 0
        code = BUILTIN_OPERATIONS[operation_id]["code"]
        used = sum(record["turn"] == self.turn and record["operation_code"] == code
                   for record in self.history)
        return max(0, BUILTIN_TURN_LIMIT - used)

    def _draw(self, pile, discards, count):
        drawn = []
        for _ in range(count):
            if not pile:
                if not discards:
                    break
                pile.extend(discards)
                discards.clear()
                self._rng.shuffle(pile)
            drawn.append(pile.pop())
        return drawn

    def _draw_turn(self):
        op_ids = self._draw(self._op_draw, self._op_discard, 3)
        red_ids = self._draw(self._red_draw, self._red_discard, 3)
        self.operations.extend(deepcopy(self._ops[i]) for i in op_ids)
        self.matrices.extend(MatrixCard(i, "red", maths.matrix(self._reds[i]["matrix"]))
                             for i in red_ids)
        self.last_draw = {"operations": op_ids, "red": red_ids}

    def calculate(self, operation_id, a_id, b_id=None, **parameters) -> Matrix:
        """Validate and compute a proposed action without changing the session."""
        self._active()
        code = self.operation(operation_id)["code"]
        if operation_id in BUILTIN_OPERATIONS and not self.builtin_remaining(operation_id):
            raise GameError(f"{BUILTIN_OPERATIONS[operation_id]['name']}: both uses spent this turn. End the turn to reset.")
        A = self.get_matrix(a_id).values
        B = None
        if code in BINARY_CODES:
            if b_id is None:
                raise GameError("This operation needs two matrix cards.")
            if a_id == b_id:
                raise GameError("Choose two different physical matrix cards.")
            B = self.get_matrix(b_id).values
        elif b_id is not None:
            raise GameError("This operation uses one matrix card.")
        required = operation_parameters(code)
        missing = set(required) - parameters.keys()
        extra = parameters.keys() - set(required)
        if missing:
            raise GameError("Choose " + ", ".join(sorted(missing)) + ".")
        if extra:
            raise GameError("Unexpected operation parameters: " + ", ".join(sorted(extra)) + ".")
        p = parameters
        try:
            if code in {"add", "subtract", "multiply"}:
                result = {"add": maths.add, "subtract": maths.sub, "multiply": maths.mul}[code](A, B)
            elif code in {"add_vector", "append_vector", "replace_vector"}:
                result = maths.vector_op(A, B, p["axis"], p["source"], p.get("target"),
                                         code.split("_")[0])
            elif code == "transpose":
                result = maths.transpose(A)
            elif code == "swap":
                result = maths.swap(A, p["axis"], p["i"], p["j"])
            elif code in {"shift_plus", "shift_minus"}:
                result = maths.shift(A, 1 if code == "shift_plus" else -1)
            elif code in {"negate", "double"}:
                result = maths.scale(A, -1 if code == "negate" else 2)
            elif code == "inverse":
                result = maths.inverse(A)
            elif code == "lu":
                if p["factor"] not in ("L", "U"):
                    raise GameError("Choose factor L or U.")
                result = maths.lu(A)[p["factor"] == "U"]
            elif code in {"entry_plus", "entry_minus", "entry_tweak"}:
                delta = p["delta"] if code == "entry_tweak" else (1 if code == "entry_plus" else -1)
                result = maths.entry_tweak(A, p["i"], p["j"], delta)
            elif code == "entry_zero":
                result = maths.entry_zero(A, p["i"], p["j"])
            elif code == "combine_vectors":
                result = maths.combine_vectors(A, p["axis"], p["source"], p["target"], p["delta"])
            else:
                raise GameError("Unsupported operation card.")
            if not all(2 <= d <= 4 for d in maths.shape(result)):
                raise GameError("Results must have 2–4 rows and 2–4 columns.")
            return result
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise GameError(str(exc)) from exc

    def perform(self, operation_id, a_id, b_id=None, answer=None, **parameters):
        result = self.calculate(operation_id, a_id, b_id, **parameters)
        if self.mode == "student":
            submitted = parse_answer(answer)
            if submitted != result:
                raise AnswerError("Answer is incorrect. Try again.")
        operation = self.operation(operation_id)
        operands = [self.get_matrix(i) for i in (a_id, b_id) if i is not None]
        key = _key(result)
        scored = (key not in self._seen
                  and maths.check(self.objective["id"], result)["won"])
        self._seen.add(key)
        self.score += int(scored)
        new_card = MatrixCard(f"G{self._next_result:04d}", "blue", result)
        self._next_result += 1
        if operation_id not in BUILTIN_OPERATIONS:
            self.operations.remove(operation)
            self._op_discard.append(operation_id)
        for card in operands:
            if card.color == "red":
                self.matrices.remove(card)
                self._red_discard.append(card.id)
        self.matrices.append(new_card)
        message = "New objective result: +1 point." if scored else "Result recorded. No new point."
        self.history.append({"turn": self.turn, "operation_id": operation_id,
                             "operation_code": operation["code"], "operation_title": operation["name"],
                             "a_id": a_id, "b_id": b_id, "parameters": deepcopy(parameters),
                             "result_id": new_card.id, "result": maths.dump(result),
                             "scored": bool(scored), "score": self.score, "message": message})
        return {"result": new_card, "scored": bool(scored), "message": message}

    def end_turn(self):
        self._active()
        if self.turn == 8:
            self.finished = True
        else:
            self.turn += 1
            self._draw_turn()

    def remove_card(self, card_id):
        """Remove a live card from play permanently, retaining score/history."""
        self._active()
        for card in self.operations:
            if card["id"] == card_id:
                self.operations.remove(card)
                self._removed_operations.append(card_id)
                return
        card = self.get_matrix(card_id)
        self.matrices.remove(card)
        self._removed_matrices.append(card)

    def to_dict(self):
        """Return a detached JSON-safe snapshot with exact values and RNG state."""
        return deepcopy({"format": "gametrix-solo", "version": 4,
                         "deck": {"path": "expansion_split/generated/deck.json", "sha256": self._deck_hash},
                         "mode": self.mode, "seed": self.seed, "objective_id": self.objective["id"],
                         "turn": self.turn, "finished": self.finished, "score": self.score,
                         "operations": [c["id"] for c in self.operations],
                         "matrices": [c.to_dict() for c in self.matrices], "history": self.history,
                         "seen": sorted(self._seen), "next_result": self._next_result,
                         "op_draw": self._op_draw, "red_draw": self._red_draw,
                         "op_discard": self._op_discard, "red_discard": self._red_discard,
                         "removed_operations": self._removed_operations,
                         "removed_matrices": [c.to_dict() for c in self._removed_matrices],
                         "rng_state": self._rng.getstate(), "last_draw": self.last_draw})

    @classmethod
    def from_dict(cls, data):
        """Restore a validated snapshot, migrating old operation piles and rules."""
        try:
            data = deepcopy(data)
            if (not isinstance(data, dict) or data["format"] != "gametrix-solo"
                    or type(data["version"]) is not int or data["version"] not in (1, 2, 3, 4)):
                raise ValueError("Unsupported saved-game format.")
            game = cls(data["mode"], data["objective_id"], data["seed"])
            legacy = data["version"] == 1
            saved_ops = (game._legacy_ops if legacy else
                         game._original_ops if data["version"] == 2 else game._ops)
            if not isinstance(data["deck"], dict) or data["deck"]["sha256"] != game._deck_hash:
                raise ValueError("The saved game uses a different deck.")
            if data["deck"]["path"] != "expansion_split/generated/deck.json":
                raise ValueError("Invalid saved-game deck identification.")
            game.turn, game.finished, game.score = data["turn"], data["finished"], data["score"]
            if (type(game.turn) is not int or not 1 <= game.turn <= 8
                    or type(game.finished) is not bool or (game.finished and game.turn != 8)
                    or type(game.score) is not int or game.score < 0):
                raise ValueError("Invalid saved-game progress.")
            for name in ("operations", "matrices", "history", "seen", "op_draw", "red_draw",
                         "op_discard", "red_discard"):
                if not isinstance(data[name], list):
                    raise ValueError(f"Saved-game {name} must be a list.")
            def id_list(values, known):
                if (any(not isinstance(i, str) or i not in known for i in values)
                        or len(values) != len(set(values))):
                    raise ValueError("Invalid saved-game card IDs.")
            for name in ("operations", "op_draw", "op_discard"):
                id_list(data[name], saved_ops)
            for name in ("red_draw", "red_discard"):
                id_list(data[name], game._reds)
            removed_operations = data["removed_operations"] if data["version"] >= 4 else []
            removed_matrices = data["removed_matrices"] if data["version"] >= 4 else []
            if not isinstance(removed_operations, list) or not isinstance(removed_matrices, list):
                raise ValueError("Invalid saved-game removed cards.")
            id_list(removed_operations, saved_ops)
            def saved_matrix(values):
                result = maths.matrix(values)
                if not all(2 <= d <= 4 for d in maths.shape(result)):
                    raise ValueError("Invalid saved-game matrix dimensions.")
                return result
            if any(not isinstance(c, dict) for c in data["matrices"] + removed_matrices):
                raise ValueError("Invalid saved-game matrix records.")
            game.operations = [deepcopy(saved_ops[i]) for i in data["operations"]]
            game.matrices = [MatrixCard(c["id"], c["color"], saved_matrix(c["values"]))
                             for c in data["matrices"]]
            game._removed_operations = removed_operations
            game._removed_matrices = [MatrixCard(c["id"], c["color"], saved_matrix(c["values"]))
                                      for c in removed_matrices]
            all_matrices = game.matrices + game._removed_matrices
            blue_ids = {c["id"] for c in game._deck["blue"]}
            def result_number(card_id):
                if isinstance(card_id, str) and re.fullmatch(r"G[0-9]{4,}", card_id):
                    number = int(card_id[1:])
                    if number >= 1 and card_id == f"G{number:04d}":
                        return number
                return None
            for card in all_matrices:
                if (not isinstance(card.id, str) or card.color not in ("blue", "red")
                        or (card.color == "red" and card.id not in game._reds)
                        or (card.color == "blue" and card.id not in blue_ids
                            and result_number(card.id) is None)):
                    raise ValueError("Invalid saved-game matrix card ID or color.")
            if not any(c.color == "blue" and c.id in blue_ids for c in all_matrices):
                raise ValueError("The saved game has no starting blue card.")
            for name in ("op_draw", "red_draw", "op_discard", "red_discard"):
                setattr(game, "_" + name, data[name])
            op_ids = ([c["id"] for c in game.operations] + game._op_draw + game._op_discard
                      + game._removed_operations)
            red_ids = [c.id for c in all_matrices if c.color == "red"] + game._red_draw + game._red_discard
            if (len(op_ids) != len(set(op_ids)) or set(op_ids) != set(saved_ops)
                    or len(red_ids) != len(set(red_ids)) or set(red_ids) != set(game._reds)):
                raise ValueError("Invalid saved-game card piles.")
            ids = [c.id for c in all_matrices]
            if len(ids) != len(set(ids)):
                raise ValueError("Invalid saved-game matrix cards.")
            game.history, game.last_draw = data["history"], data["last_draw"]
            if any(not isinstance(key, str) for key in data["seen"]):
                raise ValueError("Invalid saved-game collected matrix values.")
            for key in data["seen"]:
                if _key(saved_matrix(json.loads(key))) != key:
                    raise ValueError("Saved-game collected matrix values must be canonical.")
            game._seen = set(data["seen"])
            if not {_key(c.values) for c in all_matrices if c.color == "blue"} <= game._seen:
                raise ValueError("Saved-game collected values omit an existing blue matrix.")
            game._next_result = data["next_result"]
            if type(game._next_result) is not int or game._next_result < 1:
                raise ValueError("Invalid saved-game result sequence.")
            generated = {c.id: c for c in all_matrices if result_number(c.id) is not None}
            if game._next_result != len(game.history) + 1 or len(generated) != len(game.history):
                raise ValueError("Invalid saved-game result sequence.")
            previous_turn, score = 1, 0
            known_inputs = blue_ids | set(game._reds)
            history_ops = (game._legacy_ops if legacy else
                           game._legacy_ops | saved_ops | BUILTIN_OPERATIONS)
            for number, record in enumerate(game.history, 1):
                if not isinstance(record, dict):
                    raise ValueError("Invalid saved-game history record.")
                op = history_ops[record["operation_id"]]
                code, params = op["code"], record["parameters"]
                if (record["operation_code"] != code or record["operation_title"] != op["name"]
                        or not isinstance(record["message"], str)
                        or type(record["turn"]) is not int
                        or not previous_turn <= record["turn"] <= game.turn
                        or type(record["scored"]) is not bool
                        or not isinstance(params, dict) or set(params) != set(operation_parameters(code))):
                    raise ValueError("Invalid saved-game history fields.")
                for name, value in params.items():
                    if ((name == "axis" and value not in ("row", "column"))
                            or (name == "factor" and value not in ("L", "U"))
                            or (name in ("i", "j", "source", "target")
                                and (type(value) is not int or not 0 <= value < 4))
                            or (name == "delta" and (type(value) is not int or value not in (-1, 1)))):
                        raise ValueError("Invalid saved-game history parameters.")
                a_id, b_id = record["a_id"], record["b_id"]
                if (not isinstance(a_id, str) or a_id not in known_inputs
                        or (code in BINARY_CODES and (not isinstance(b_id, str)
                            or b_id not in known_inputs or b_id == a_id))
                        or (code not in BINARY_CODES and b_id is not None)):
                    raise ValueError("Invalid saved-game history operands.")
                result_id = f"G{number:04d}"
                if (record["result_id"] != result_id or result_id not in generated
                        or saved_matrix(record["result"]) != generated[result_id].values):
                    raise ValueError("Invalid saved-game history result.")
                score += int(record["scored"])
                if type(record["score"]) is not int or record["score"] != score:
                    raise ValueError("Invalid saved-game history score.")
                known_inputs.add(result_id)
                previous_turn = record["turn"]
            if score != game.score:
                raise ValueError("Saved-game score does not match its history.")
            if not isinstance(game.last_draw, dict) or set(game.last_draw) != {"operations", "red"}:
                raise ValueError("Invalid saved-game last draw.")
            for name, known, limit in (("operations", saved_ops, 3),
                                       ("red", game._reds, 5 if legacy else 3)):
                drawn = game.last_draw[name]
                if not isinstance(drawn, list) or len(drawn) > limit:
                    raise ValueError("Invalid saved-game last draw cards.")
                id_list(drawn, known)
            def tuples(value):
                return tuple(tuples(x) for x in value) if isinstance(value, (tuple, list)) else value
            game._rng.setstate(tuples(data["rng_state"]))
            if legacy:
                # Validate the complete original partition before dropping only
                # retired operation cards. Matrix cards, results, history and RNG
                # survive unchanged; no replacement cards are drawn.
                game.operations = [c for c in game.operations if c["id"] in game._ops]
                game._op_draw = [i for i in game._op_draw if i in game._ops]
                game._op_discard = [i for i in game._op_discard if i in game._ops]
                game.last_draw["operations"] = [i for i in game.last_draw["operations"]
                                                 if i in game._ops]
                game.last_draw["red"] = game.last_draw["red"][:3]
            if data["version"] < 3:
                # Keep the current hand, discard and relative draw order. A
                # separate deterministic shuffle adds copies without changing
                # the saved RNG used for future draws/recycling.
                migration_rng = random.Random(f"digital-deck-v3:{game.seed}:{game.turn}")
                for card_id in sorted(game._ops.keys() - game._original_ops.keys()):
                    game._op_draw.insert(migration_rng.randrange(len(game._op_draw) + 1), card_id)
            return game
        except (KeyError, IndexError, TypeError, ValueError, AttributeError, OverflowError, RecursionError) as exc:
            raise GameError(f"Cannot restore saved game: {exc}") from exc

    def save(self, path, *, ui_state=None):
        """Explicitly write a complete snapshot, atomically replacing any old save."""
        snapshot = self.to_dict()
        if ui_state is not None:
            # Optional presentation data shares the atomic write, but is not
            # part of the rules model. The interface validates it on restore.
            snapshot["ui_state"] = ui_state
        payload = json.dumps(snapshot, indent=2)
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                             prefix=f".{destination.name}.", suffix=".tmp",
                                             delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @classmethod
    def load(cls, path):
        try:
            return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            raise GameError(f"Cannot load saved game: {exc}") from exc
