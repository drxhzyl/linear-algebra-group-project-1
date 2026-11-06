"""A calculation-budget wrapper for fresh, intuition-first agent playtests."""

import argparse
import json

import gametrix as g
from diagnostics import usable_codes


def view(s, deck):
    visible = g.show(s, deck)
    # The player sees the working matrix, not free rank/determinant/goal diagnostics.
    visible.pop("facts")
    visible.pop("check")
    b = s["student_budget"]
    visible["budget"] = {
        "candidates_this_turn": sum(p["turn"] == s["turn"] for p in b["plans"]),
        "candidate_limit_per_turn": 2,
        "previews_this_turn": sum(p["turn"] == s["turn"] for p in b["previews"]),
        "preview_limit_per_turn": 1,
        "previews_total": len(b["previews"]), "preview_limit_total": 6,
        "fixed_horizon": b.get("fixed_horizon", False),
    }
    return visible


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start")
    start.add_argument("session", type=g.Path)
    start.add_argument("--seed", type=int, required=True)
    start.add_argument("--objective", required=True)
    start.add_argument("--blue", required=True)
    start.add_argument("--deck", type=g.Path, default=g.ROOT/"generated"/"deck.json")
    start.add_argument("--fixed-horizon", action="store_true")
    for command in ("show", "plan", "preview", "play", "end-turn", "stop"):
        p = sub.add_parser(command)
        p.add_argument("session", type=g.Path)
        if command == "plan":
            p.add_argument("--operation", required=True)
            g.action_options(p)
        if command in ("preview", "play"):
            p.add_argument("--plan", type=int, required=True)
        if command in ("plan", "stop"):
            p.add_argument("--note", required=True)
    args = parser.parse_args()
    if args.command == "start":
        if args.session.exists():
            raise ValueError("Session exists; use a new filename")
        s = g.new_session(args.deck, args.seed, args.objective, args.blue, "draw", "student", 8, 16)
        s["student_budget"] = {"protocol": "expansion_v1/PROTOCOL.md" if args.fixed_horizon else "student_tests/PROTOCOL.md", "plans": [], "previews": [],
                               "candidate_limit_per_turn": 2, "preview_limit_per_turn": 1, "preview_limit_total": 6,
                               "fixed_horizon": args.fixed_horizon}
        g.write_json(args.session, s)
        print(json.dumps(view(s, g.read_json(s["deck"])), indent=2, ensure_ascii=False))
        return
    s, deck = g.load_session(args.session)
    b = s["student_budget"]
    if args.command != "show" and s["status"] != "active":
        raise ValueError("Session has ended")
    result = None
    if args.command == "plan":
        if sum(p["turn"] == s["turn"] for p in b["plans"]) >= 2:
            raise ValueError("Two candidate plans already used this turn")
        if args.operation not in s["operation_hand"] or (args.red and args.red not in s["red_hand"]):
            raise ValueError("Proposed cards must be in hand")
        plan = {"id": len(b["plans"]) + 1, "turn": s["turn"], "at_move": s["moves"],
                "operation": args.operation, "red": args.red, "params": g.params(args),
                "note": args.note, "attempted": False}
        b["plans"].append(plan)
        result = {"plan_id": plan["id"], "note": plan["note"]}
    elif args.command in ("preview", "play"):
        plan = next((p for p in b["plans"] if p["id"] == args.plan), None)
        if plan is None or plan["turn"] != s["turn"] or plan["at_move"] != s["moves"] or plan["attempted"]:
            raise ValueError("Plan must be unused and refer to the current matrix and turn")
        if args.command == "preview":
            if len(b["previews"]) >= 6 or any(p["turn"] == s["turn"] for p in b["previews"]):
                raise ValueError("Calculation budget exhausted for this turn or session")
            record = {"turn": s["turn"], "plan": args.plan}
            b["previews"].append(record)  # Invalid calculations also spend the budget.
            try:
                op = g.lookup(deck, "operations", plan["operation"])
                B = g.mx.matrix(g.lookup(deck, "red", plan["red"])["matrix"]) if plan["red"] else None
                record["result"] = g.mx.dump(g.apply(g.mx.matrix(s["current"]), op["code"], B, **plan["params"]))
            except (ValueError, ZeroDivisionError) as exc:
                record["error"] = str(exc)
            result = record
        else:
            plan["attempted"] = True
            try:
                g.play(s, deck, plan["operation"], plan["red"], plan["params"], plan["note"])
            except (ValueError, ZeroDivisionError) as exc:
                plan["error"] = str(exc)
                result = {"error": str(exc), "candidate_spent": True}
    elif args.command == "end-turn":
        turn = s["turn"]
        drawn = g.advance(s)
        s["history"].append({"type": "end_turn", "turn": turn, "note": "student budget test", "drawn": drawn})
    elif args.command == "stop":
        reds = [g.lookup(deck, "red", cid) for cid in s["red_hand"]]
        usable = usable_codes(g.mx.matrix(s["current"]), reds)
        has_legal = any(g.lookup(deck, "operations", cid)["code"] in usable for cid in s["operation_hand"])
        played_turns = {h["turn"] for h in s["history"] if h["type"] == "play"}
        turn_plans = [p for p in b["plans"] if p["turn"] == s["turn"]]
        candidate_lock = len(turn_plans) >= 2 and all(p["attempted"] and "error" in p for p in turn_plans) and s["turn_operations"] == 0
        if b.get("fixed_horizon") and (s["turn_operations"] > 0 or (has_legal and not candidate_lock)):
            raise ValueError("Fixed-horizon experiment: continue to the turn cap; label unclear moves as [stall]")
        if has_legal and not candidate_lock and (len(played_turns) < 3 or not b["previews"]):
            raise ValueError("Before a planning stop, try three turns and at least one bounded preview")
        s["status"], s["stop_reason"] = "stopped", args.note
        s["history"].append({"type": "stop", "turn": s["turn"], "note": args.note})
    if args.command != "show":
        g.write_json(args.session, s)
    out = view(s, deck)
    if result is not None:
        out["action_result"] = result
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, ZeroDivisionError) as exc:
        print(json.dumps({"error": str(exc)}))
        raise SystemExit(2)
