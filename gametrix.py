#!/usr/bin/env python3
"""A card lab, not an automated player: generate, deal, calculate, and log."""

import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys

import matrix as mx

ROOT = Path(__file__).resolve().parent
SOURCE_URL = "https://docs.google.com/document/d/1TayTRdpVcd7jJ-ECnDpQCo00H_E-_xt34AwFM1chSH0"
OPS = [
    ("add", "Add a Matrix", 5, "A + B; identical shapes."),
    ("subtract", "Subtract a Matrix", 5, "A - B; identical shapes."),
    ("multiply", "Right Multiply", 5, "(m x n)(n x p) becomes m x p."),
    ("add_vector", "Add to a Row or Column", 5, "Add a matching red row/column to an existing one. Shape stays unchanged."),
    ("append_vector", "Append a Row or Column", 4, "Append a matching red row at the bottom, or column on the right. Maximum dimension 4."),
    ("replace_vector", "Replace a Row or Column", 2, "Replace an existing row/column using a matching red vector."),
    ("transpose", "Transpose", 3, "A becomes its transpose; m x n becomes n x m."),
    ("swap", "Interchange", 3, "Swap two existing rows or two existing columns."),
    ("shift_plus", "Add 1 to Every Entry", 2, "Add 1 to every entry; shape unchanged."),
    ("shift_minus", "Subtract 1 from Every Entry", 2, "Subtract 1 from every entry; shape unchanged."),
    ("negate", "Multiply by -1", 1, "Negate every entry."),
    ("double", "Multiply by 2", 1, "Double every entry."),
    ("inverse", "Inverse", 1, "Square and invertible only. Keep exact fractions."),
    ("lu", "LU Factorization", 1, "Square only. Unit-L Doolittle, no row swaps, first n-1 pivots nonzero. Choose L or U."),
]
RED_MATRIX_OPS = {"add", "subtract", "multiply", "add_vector", "append_vector", "replace_vector"}
RED_FUEL_OPS = {"entry_tweak", "entry_zero", "entry_plus", "entry_minus"}
RED_OPS = RED_MATRIX_OPS | RED_FUEL_OPS


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def number(value):
    return value.numerator if value.denominator == 1 else str(value)


def bounded(A, limit):
    return all(abs(x) <= limit for row in A for x in row)


def shear(n, i, j, coefficient):
    A = mx.identity(n)
    A[i][j] = coefficient
    return A


def elementary(rng, n, count):
    A = mx.identity(n)
    for _ in range(count):
        i, j = rng.sample(range(n), 2)
        A = mx.mul(A, shear(n, i, j, rng.choice([-1, 1])))
    if rng.random() < 0.5:
        i, j = rng.sample(range(n), 2)
        A = mx.swap(A, "row", i, j)
    return A


def low_rank(rng, m, n, rank):
    for _ in range(10000):
        X = mx.matrix([[rng.choice([-1, 0, 1]) for _ in range(rank)] for _ in range(m)])
        Y = mx.matrix([[rng.choice([-1, 0, 1]) for _ in range(n)] for _ in range(rank)])
        if mx.rank(X) == mx.rank(Y) == rank:
            A = mx.mul(X, Y)
            if bounded(A, 2):
                return A
    raise ValueError("Could not generate bounded low-rank matrix")


def generate_deck(seed=20261028, blue_count=12):
    rng = random.Random(seed)
    objectives = read_json(ROOT / "objectives.json")
    red, used = [], set()

    def put(A, family, pair=None):
        key = json.dumps(mx.dump(A))
        if key in used:
            return False
        used.add(key)
        red.append({"id": f"R{len(red)+1:02d}", "kind": "red", "family": family,
                    "matrix": mx.dump(A), "shape": list(mx.shape(A)),
                    "rank": mx.rank(A), "pair": pair})
        return True

    for n in (2, 3, 4):
        for sign in (1, -1):
            put(mx.scale(mx.identity(n), sign), "signed_identity")
    for i, j in rng.sample([(i, j) for i in range(3) for j in range(3) if i != j], 2):
        for sign in (1, -1):
            put(shear(3, i, j, sign), "elementary")
    for _ in range(2):
        for attempt in range(10000):
            A = elementary(rng, 3, 2)
            if rng.random() < 0.5:
                D = mx.identity(3)
                k = rng.randrange(3)
                D[k][k] = 2
                A = mx.mul(A, D)
            if bounded(A, 2) and abs(mx.det(A)) in (1, 2) and put(A, "invertible_mixer"):
                break
        else:
            raise ValueError("Could not generate distinct square mixer")
    for rank in (1, 2):
        for _ in range(10000):
            if put(low_rank(rng, 3, 3, rank), f"rank_{rank}_correction"):
                break
        else:
            raise ValueError("Could not generate distinct square correction")
    for m, n, count, full_count in [(2, 3, 3, 2), (3, 4, 3, 2), (2, 4, 2, 1)]:
        for k in range(count):
            for attempt in range(10000):
                if k < full_count:
                    A = [row + [rng.choice([-1, 0, 1]) for _ in range(n-m)]
                         for row in mx.identity(m)]
                    A = mx.mul(elementary(rng, m, 1), A)
                    A = mx.mul(A, elementary(rng, n, 1))
                    family = "full_rank_rectangle"
                else:
                    A = low_rank(rng, m, n, 2 if m == 3 else 1)
                    family = "low_rank_rectangle"
                if not bounded(A, 2):
                    continue
                B = mx.transpose(A)
                if json.dumps(mx.dump(A)) in used or json.dumps(mx.dump(B)) in used:
                    continue
                pair = f"{m}x{n}-{k+1}"
                put(A, family, pair)
                put(B, family, pair)
                break
            else:
                raise ValueError("Could not generate distinct rectangular pair")
    operations = []
    for code, name, copies, rule in OPS:
        for _ in range(copies):
            operations.append({"id": f"O{len(operations)+1:02d}", "kind": "operation",
                               "code": code, "name": name, "rule": rule})
    blue, seen_blue, attempts = [], set(), 0
    while len(blue) < blue_count and attempts < 100000:
        attempts += 1
        diagonal = [rng.choice([-3, -2, -1, 1, 2, 3]) for _ in range(3)]
        determinant = math.prod(diagonal)
        # Warm-up determinant variants are supported, so avoid an initial win.
        if abs(determinant) not in (3, 4, 6):
            continue
        D = mx.identity(3)
        for i, x in enumerate(diagonal):
            D[i][i] = x
        A = mx.mul(mx.mul(elementary(rng, 3, rng.randint(1, 3)), D),
                   elementary(rng, 3, rng.randint(1, 3)))
        key = json.dumps(mx.dump(A))
        if key in seen_blue or not bounded(A, 3):
            continue
        if any(mx.check(o["id"], A)["won"] for o in objectives):
            continue
        if any(mx.check(f"W{i:02d}", A)["won"] for i in range(1, 6)):
            continue
        seen_blue.add(key)
        blue.append({"id": f"B{len(blue)+1:02d}", "kind": "blue", "matrix": mx.dump(A),
                     "shape": [3, 3], "determinant": number(mx.det(A)),
                     "validation": "initial-goal checks passed; reachability not certified"})
    if len(blue) != blue_count:
        raise ValueError(f"Only generated {len(blue)} blue candidates after {attempts} attempts")
    expected = {(2, 2): 2, (2, 3): 3, (2, 4): 2, (3, 2): 3, (3, 3): 10,
                (3, 4): 3, (4, 2): 2, (4, 3): 3, (4, 4): 2}
    actual = collections.Counter(tuple(c["shape"]) for c in red)
    assert actual == expected and len(operations) == 40
    return {"kind": "gametrix-deck", "version": 1, "seed": seed, "source": SOURCE_URL,
            "rules_sha256": hashlib.sha256((ROOT/"rules_source.txt").read_bytes()).hexdigest(),
            "turn_rule": "Draw 3 operations and 5 red cards each turn; retain all unused cards; play at least one operation before end-turn; multiple plays allowed.",
            "status": "provisional: not universally certified or balance-tested",
            "generation_attempts": attempts, "blue": blue, "red": red,
            "operations": operations, "objectives": objectives}


def printable(deck):
    from card_layout import ensure_art, printable as render_printable
    ensure_art(deck)
    return render_printable(deck)


def deck_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lookup(deck, collection, card_id):
    for card in deck[collection]:
        if card["id"] == card_id:
            return card
    raise ValueError(f"Unknown {collection} card: {card_id}")


def shuffled(ids, seed, name, cycle):
    ids = list(ids)
    random.Random(f"{seed}:{name}:{cycle}").shuffle(ids)
    return ids


def deal(s, name, count):
    drawn = []
    for _ in range(count):
        if not s[f"{name}_draw"] and s[f"{name}_discard"]:
            s[f"{name}_cycles"] += 1
            s[f"{name}_draw"] = shuffled(s[f"{name}_discard"], s["seed"], name, s[f"{name}_cycles"])
            s[f"{name}_discard"] = []
        if not s[f"{name}_draw"]:
            break
        card = s[f"{name}_draw"].pop(0)
        s[f"{name}_hand"].append(card)
        drawn.append(card)
    return drawn


def inventory_check(s, deck):
    for name, collection in [("operation", "operations"), ("red", "red")]:
        ids = s[f"{name}_draw"] + s[f"{name}_hand"] + s[f"{name}_discard"]
        if len(ids) != len(set(ids)) or set(ids) != {c["id"] for c in deck[collection]}:
            raise ValueError(f"Corrupt {name} inventory")


def new_session(deck_path, seed, objective_id, blue_id, mode, player, turn_cap, move_cap=20):
    path = Path(deck_path).resolve()
    deck = read_json(path)
    objective = lookup(deck, "objectives", objective_id)
    blue = lookup(deck, "blue", blue_id)
    s = {"kind": "gametrix-session", "version": 1, "deck": str(path), "deck_sha256": deck_hash(path),
         "seed": seed, "objective": objective, "blue": blue_id, "current": blue["matrix"],
         "mode": mode, "player": player, "turn_cap": turn_cap, "move_cap": move_cap,
         "turn": 1, "turn_operations": 0, "moves": 0, "status": "active", "history": []}
    for name, collection in [("operation", "operations"), ("red", "red")]:
        ids = [c["id"] for c in deck[collection]]
        s[f"{name}_draw"] = shuffled(ids, seed, name, 0) if mode == "draw" else []
        s[f"{name}_hand"] = [] if mode == "draw" else ids[:]
        s[f"{name}_discard"] = []
        s[f"{name}_cycles"] = 0
    if mode == "draw":
        deal(s, "operation", 3)
        deal(s, "red", 5)
    if mx.check(objective_id, mx.matrix(s["current"]))["won"]:
        raise ValueError("Starting matrix already wins this objective")
    inventory_check(s, deck)
    return s


def load_session(path):
    s = read_json(path)
    if s.get("kind") != "gametrix-session" or deck_hash(s["deck"]) != s["deck_sha256"]:
        raise ValueError("Wrong session format or deck changed since session began")
    deck = read_json(s["deck"])
    inventory_check(s, deck)
    return s, deck


def facts(A):
    m, n = mx.shape(A)
    return {"shape": [m, n], "rank": mx.rank(A),
            "determinant": number(mx.det(A)) if m == n else None,
            "row_sums": [number(sum(r)) for r in A],
            "column_sums": [number(sum(r)) for r in mx.transpose(A)]}


def apply(A, code, B=None, axis="row", source=None, target=None, i=None, j=None, factor="L", exponent=2, delta=1):
    """Calculate a move; B is only a presence marker for red-fuel operations."""
    if code in RED_OPS and B is None:
        raise ValueError("This operation requires a red matrix")
    if code == "add": result = mx.add(A, B)
    elif code == "subtract": result = mx.sub(A, B)
    elif code == "multiply": result = mx.mul(A, B)
    elif code == "transpose": result = mx.transpose(A)
    elif code == "inverse": result = mx.inverse(A)
    elif code == "shift_plus": result = mx.shift(A, 1)
    elif code == "shift_minus": result = mx.shift(A, -1)
    elif code == "negate": result = mx.scale(A, -1)
    elif code == "double": result = mx.scale(A, 2)
    elif code == "lu": result = mx.lu(A)[0 if factor == "L" else 1]
    elif code == "swap": result = mx.swap(A, axis, i, j)
    elif code == "entry_tweak": result = mx.entry_tweak(A, i, j, delta)
    elif code == "entry_plus": result = mx.entry_tweak(A, i, j, 1)
    elif code == "entry_minus": result = mx.entry_tweak(A, i, j, -1)
    elif code == "entry_zero": result = mx.entry_zero(A, i, j)
    elif code == "combine_vectors": result = mx.combine_vectors(A, axis, source, target, delta)
    elif code in {"add_vector", "append_vector", "replace_vector"}:
        result = mx.vector_op(A, B, axis, source, target, code.split("_")[0])
    elif code == "power":
        if not 0 <= exponent <= 8 or mx.shape(A)[0] != mx.shape(A)[1]:
            raise ValueError("Power requires a square matrix and exponent 0..8")
        result = mx.identity(len(A))
        for _ in range(exponent): result = mx.mul(result, A)
    else: raise ValueError(f"Unknown operation: {code}")
    if any(not 2 <= k <= 4 for k in mx.shape(result)):
        raise ValueError("Playable dimensions must remain 2..4")
    return result


def params(args):
    out = {k: getattr(args, k) for k in ("axis", "source", "target", "i", "j", "factor", "exponent")}
    out["delta"] = getattr(args, "delta", 1)
    return out


def advance(s):
    if s["turn_operations"] < 1:
        raise ValueError("At least one operation must be played before ending the turn")
    if s["turn"] >= s["turn_cap"]:
        s["status"] = "turn_limit"
        return {"operations": [], "red": []}
    s["turn"] += 1
    s["turn_operations"] = 0
    if s["mode"] == "draw":
        return {"operations": deal(s, "operation", 3), "red": deal(s, "red", 5)}
    if not s["operation_hand"]:
        s["status"] = "resource_exhausted"
    return {"operations": [], "red": []}


def play(s, deck, operation_id, red_id, arguments, note=""):
    if s["status"] != "active":
        raise ValueError("Session is not active")
    if operation_id not in s["operation_hand"]:
        raise ValueError("Operation card is not in hand")
    operation = lookup(deck, "operations", operation_id)
    if operation["code"] in RED_OPS:
        if red_id not in s["red_hand"]:
            raise ValueError("Required red card is not in hand")
        red = lookup(deck, "red", red_id)
        # Fuel consumes a physical red card regardless of its matrix or shape.
        B = True if operation["code"] in RED_FUEL_OPS else mx.matrix(red["matrix"])
    else:
        if red_id:
            raise ValueError("This operation does not consume a red card")
        B = None
    before = s["current"]
    result = mx.dump(apply(mx.matrix(before), operation["code"], B, **arguments))
    checked = mx.check(s["objective"]["id"], mx.matrix(result))
    # Calculate first; invalid plays leave the session and its inventories unchanged.
    s["operation_hand"].remove(operation_id)
    s["operation_discard"].append(operation_id)
    if red_id:
        s["red_hand"].remove(red_id)
        s["red_discard"].append(red_id)
    s["current"] = result
    s["moves"] += 1
    s["turn_operations"] += 1
    entry = {"type": "play", "turn": s["turn"], "operation": operation_id,
             "code": operation["code"], "red": red_id, "params": arguments,
             "before": before, "after": result, "changed": before != result,
             "check": checked, "note": note, "drawn": {"operations": [], "red": []}}
    if checked["won"]:
        s["status"] = "won"
    elif s["moves"] >= s["move_cap"]:
        s["status"] = "move_limit"
    s["history"].append(entry)
    inventory_check(s, deck)
    return entry


def show(s, deck, brief=False):
    out = {k: s[k] for k in ("mode", "player", "seed", "blue", "turn", "turn_operations", "moves", "status", "current")}
    out["objective"] = {k: s["objective"][k] for k in ("id", "name", "shape", "goal")}
    out["facts"] = facts(mx.matrix(s["current"]))
    out["check"] = mx.check(s["objective"]["id"], mx.matrix(s["current"]))
    out["remaining"] = {name: {part: len(s[f"{name}_{part}"]) for part in ("hand", "draw", "discard")}
                        for name in ("operation", "red")}
    if not brief:
        grouped = collections.defaultdict(list)
        for card_id in s["operation_hand"]:
            grouped[lookup(deck, "operations", card_id)["code"]].append(card_id)
        out["operation_hand"] = dict(grouped)
        out["red_hand"] = [{k: lookup(deck, "red", card_id)[k] for k in ("id", "shape", "matrix")}
                           for card_id in s["red_hand"]]
    return out


def audit_session(s, deck):
    """Replay the recorded choices, including deals and card consumption; no search."""
    replay = new_session(s["deck"], s["seed"], s["objective"]["id"], s["blue"],
                         s["mode"], s["player"], s["turn_cap"], s["move_cap"])
    for index, event in enumerate(s["history"]):
        if replay["status"] != "active":
            raise ValueError(f"Event {index}: action after session ended")
        if event["turn"] != replay["turn"]:
            raise ValueError(f"Event {index}: wrong turn")
        kind = event["type"]
        if kind == "play":
            actual = play(replay, deck, event["operation"], event["red"],
                          event["params"], event.get("note", ""))
            if actual != event:
                raise ValueError(f"Event {index}: move record differs from exact replay")
        elif kind == "end_turn":
            drawn = advance(replay)
            if drawn != event["drawn"]:
                raise ValueError(f"Event {index}: recorded draw differs from seeded replay")
        elif kind == "stop":
            replay["status"] = "stopped"
            replay["stop_reason"] = event.get("note", "")
        else:
            raise ValueError(f"Event {index}: unknown event type {kind}")
    for key in ("current", "turn", "turn_operations", "moves", "status", "objective"):
        if replay[key] != s[key]:
            raise ValueError(f"Final {key} differs from replay")
    if replay.get("stop_reason") != s.get("stop_reason"):
        raise ValueError("Final stop reason differs from replay")
    for name in ("operation", "red"):
        for part in ("hand", "draw", "discard", "cycles"):
            key = f"{name}_{part}"
            if replay[key] != s[key]:
                raise ValueError(f"Final {key} differs from replay")
    return True


def summarize(directory):
    episodes = []
    for path in sorted(Path(directory).rglob("*.json")):
        data = read_json(path)
        if data.get("kind") != "gametrix-session":
            continue
        data, deck = load_session(path)
        audit_session(data, deck)
        actual_win = mx.check(data["objective"]["id"], mx.matrix(data["current"]))["won"]
        states = [mx.matrix(lookup(deck, "blue", data["blue"])["matrix"])]
        states.extend(mx.matrix(h["after"]) for h in data["history"] if h["type"] == "play")
        entries = [x for A in states for row in A for x in row]
        episodes.append({"file": str(path), "player": data["player"], "objective": data["objective"]["id"],
                         "blue": data["blue"], "mode": data["mode"], "seed": data["seed"],
                         "status": data["status"], "win_rechecked": actual_win,
                         "moves": data["moves"], "turns": data["turn"],
                         "replay_verified": True,
                         "largest_absolute_entry": number(max(abs(x) for x in entries)),
                         "largest_denominator": max(x.denominator for x in entries),
                         "no_op_plays": sum(h["type"] == "play" and not h.get("changed", True) for h in data["history"]),
                         "reason": data.get("stop_reason", "")})
    def stats(rows):
        won = [r for r in rows if r["status"] == "won" and r["win_rechecked"]]
        return {"episodes": len(rows), "wins": len(won),
                "win_rate": len(won)/len(rows) if rows else None,
                "mean_moves_among_wins": statistics.mean(r["moves"] for r in won) if won else None,
                "median_moves_among_wins": statistics.median(r["moves"] for r in won) if won else None,
                "mean_turns_among_wins": statistics.mean(r["turns"] for r in won) if won else None,
                "unsolved_or_in_progress": len(rows)-len(won)}
    return {"kind": "gametrix-playtest-summary", "overall": stats(episodes),
            "by_mode": {mode: stats([r for r in episodes if r["mode"] == mode]) for mode in ("open", "draw")},
            "by_objective": {o: stats([r for r in episodes if r["objective"] == o])
                             for o in sorted({r["objective"] for r in episodes})},
            "caveat": "Small agent-selected sample. Open mode has no draw luck. Unsolved/limited runs are censored, not proofs of impossibility. Winning averages exclude unsolved runs.",
            "episodes": episodes}


def action_options(p):
    p.add_argument("--red")
    p.add_argument("--axis", choices=["row", "column"], default="row")
    for name in ("source", "target", "i", "j"):
        p.add_argument("--"+name, type=int)
    p.add_argument("--factor", choices=["L", "U"], default="L")
    p.add_argument("--exponent", type=int, default=2)
    p.add_argument("--delta", type=int, choices=[-1, 1], default=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("generate")
    p.add_argument("--seed", type=int, default=20261028)
    p.add_argument("--out", type=Path, default=ROOT/"generated")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("start")
    p.add_argument("session", type=Path)
    p.add_argument("--deck", type=Path, default=ROOT/"generated"/"deck.json")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--objective", required=True)
    p.add_argument("--blue", required=True)
    p.add_argument("--mode", choices=["draw", "open"], default="draw")
    p.add_argument("--player", default="local")
    p.add_argument("--turn-cap", type=int, default=12)
    p.add_argument("--move-cap", type=int, default=20)
    for command in ("show", "end-turn", "stop"):
        p = sub.add_parser(command)
        p.add_argument("session", type=Path)
        p.add_argument("--note", default="")
        if command == "show": p.add_argument("--brief", action="store_true")
    p = sub.add_parser("play")
    p.add_argument("session", type=Path)
    p.add_argument("--operation", required=True)
    p.add_argument("--note", default="")
    action_options(p)
    p = sub.add_parser("calc")
    p.add_argument("--session", type=Path)
    p.add_argument("--matrix", help="JSON nested array")
    p.add_argument("--other", help="Second matrix as JSON")
    p.add_argument("--op", default="facts")
    p.add_argument("--objective")
    action_options(p)
    p = sub.add_parser("summary")
    p.add_argument("--directory", type=Path, default=ROOT/"playtests")
    p.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.command == "generate":
        if (args.out/"deck.json").exists() and not args.force:
            raise ValueError("Output deck exists; choose another directory or use --force")
        deck = generate_deck(args.seed)
        write_json(args.out/"deck.json", deck)
        from card_layout import write_collection
        write_collection(args.out, deck)
        out = {"directory": str(args.out), "seed": args.seed,
               "counts": {k: len(deck[k]) for k in ("blue", "red", "operations", "objectives")},
               "status": deck["status"], "blue_candidate_attempts": deck["generation_attempts"]}
        write_json(args.out/"generation_report.json", out)
    elif args.command == "start":
        if args.session.exists():
            raise ValueError("Session already exists; use a new filename")
        if args.turn_cap < 1 or args.move_cap < 1: raise ValueError("Harness caps must be positive")
        s = new_session(args.deck, args.seed, args.objective, args.blue, args.mode, args.player, args.turn_cap, args.move_cap)
        write_json(args.session, s)
        out = show(s, read_json(s["deck"]))
    elif args.command in ("show", "play", "end-turn", "stop"):
        s, deck = load_session(args.session)
        if args.command == "show":
            out = show(s, deck, args.brief)
        elif args.command == "play":
            entry = play(s, deck, args.operation, args.red, params(args), args.note)
            write_json(args.session, s)
            out = show(s, deck, True)
            out["last_move"] = entry
            out["new_operation_cards"] = [lookup(deck, "operations", x) for x in entry["drawn"]["operations"]]
            out["new_red_cards"] = [lookup(deck, "red", x) for x in entry["drawn"]["red"]]
        elif args.command == "end-turn":
            if s["status"] != "active": raise ValueError("Session is not active")
            turn = s["turn"]
            drawn = advance(s)
            s["history"].append({"type": "end_turn", "turn": turn, "note": args.note, "drawn": drawn})
            write_json(args.session, s)
            out = show(s, deck)
        else:
            if s["status"] != "active": raise ValueError("Only active sessions can be stopped")
            s["status"], s["stop_reason"] = "stopped", args.note
            s["history"].append({"type": "stop", "turn": s["turn"], "note": args.note})
            write_json(args.session, s)
            out = show(s, deck, True)
    elif args.command == "calc":
        s, deck = load_session(args.session) if args.session else (None, None)
        if args.matrix:
            A = mx.matrix(json.loads(args.matrix))
        elif s:
            A = mx.matrix(s["current"])
        else:
            raise ValueError("Provide --session or --matrix")
        B = mx.matrix(json.loads(args.other)) if args.other else None
        if args.red:
            if not deck: raise ValueError("--red requires --session")
            B = mx.matrix(lookup(deck, "red", args.red)["matrix"])
        goal = args.objective or (s["objective"]["id"] if s else None)
        if args.op == "facts":
            out = facts(A)
            if goal: out["check"] = mx.check(goal, A)
        elif args.op == "check":
            if not goal: raise ValueError("Provide --objective")
            out = mx.check(goal, A)
        else:
            result = apply(A, args.op, B, **params(args))
            out = {"result": mx.dump(result), "facts": facts(result)}
            if goal: out["check"] = mx.check(goal, result)
    else:
        out = summarize(args.directory)
        if args.out: write_json(args.out, out)
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, ZeroDivisionError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
