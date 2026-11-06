"""Replay experiment logs and report card-use proportions; never choose moves."""

import argparse
from collections import Counter
import statistics

import gametrix as g

SINGLE_ENTRY = {"entry_tweak", "entry_plus", "entry_minus", "entry_zero"}
ADDED = SINGLE_ENTRY | {"combine_vectors"}


def summarize(roots):
    rows = []
    for root in roots:
        manifest = g.read_json(root/"manifest.json")
        for case in manifest["cases"]:
            path = root/"playtests"/(case["name"] + ".json")
            s, deck = g.load_session(path)
            g.audit_session(s, deck)
            for key in ("blue", "seed"):
                if s[key] != case[key]:
                    raise ValueError(f"Manifest mismatch: {path}: {key}")
            if s["objective"]["id"] != case["objective"]:
                raise ValueError(f"Manifest objective mismatch: {path}")
            budget = s["student_budget"]
            plans = Counter(p["turn"] for p in budget["plans"])
            previews = Counter(p["turn"] for p in budget["previews"])
            if max(plans.values(), default=0) > 2 or max(previews.values(), default=0) > 1 or len(budget["previews"]) > 6:
                raise ValueError(f"Calculation budget violated: {path}")
            plays = [h for h in s["history"] if h["type"] == "play"]
            counts = Counter(h["code"] for h in plays)
            simple = sum(counts[code] for code in SINGLE_ENTRY)
            added = sum(counts[code] for code in ADDED)
            values = [x for h in plays for row in g.mx.matrix(h["after"]) for x in row]
            rows.append({**case, "file": str(path), "status": s["status"], "moves": s["moves"],
                         "turns": s["turn"], "previews": len(budget["previews"]), "candidates": len(budget["plans"]),
                         "operation_counts": dict(counts), "single_entry_plays": simple, "added_plays": added,
                         "original_plays": len(plays)-added,
                         "single_entry_share": simple/len(plays) if plays else None,
                         "added_share": added/len(plays) if plays else None,
                         "red_used_as_fuel": simple,
                         "red_used_as_matrix_or_vector": sum(h["red"] is not None and h["code"] not in SINGLE_ENTRY for h in plays),
                         "stall_plays": sum(h["note"].startswith("[stall]") for h in plays),
                         "no_op_plays": sum(not h["changed"] for h in plays),
                         "largest_absolute_result_entry": g.number(max(map(abs, values))) if values else None,
                         "largest_result_denominator": max((x.denominator for x in values), default=1),
                         "replay_verified": True, "count_budget_verified": True,
                         "reason": s.get("stop_reason", "")})

    def stats(group):
        wins = [r for r in group if r["status"] == "won"]
        moves = sum(r["moves"] for r in group)
        winning_moves = sum(r["moves"] for r in wins)
        return {"episodes": len(group), "wins": len(wins), "in_progress": sum(r["status"] == "active" for r in group),
                "statuses": dict(Counter(r["status"] for r in group)), "moves": moves,
                "mean_moves_among_wins": statistics.mean(r["moves"] for r in wins) if wins else None,
                "mean_turns_among_wins": statistics.mean(r["turns"] for r in wins) if wins else None,
                "previews": sum(r["previews"] for r in group),
                "single_entry_plays": sum(r["single_entry_plays"] for r in group),
                "single_entry_share": sum(r["single_entry_plays"] for r in group)/moves if moves else None,
                "added_share": sum(r["added_plays"] for r in group)/moves if moves else None,
                "original_share": sum(r["original_plays"] for r in group)/moves if moves else None,
                "single_entry_share_among_wins": sum(r["single_entry_plays"] for r in wins)/winning_moves if winning_moves else None,
                "added_share_among_wins": sum(r["added_plays"] for r in wins)/winning_moves if winning_moves else None,
                "episodes_above_80_percent_single_entry": [r["name"] for r in group if (r["single_entry_share"] or 0) > .8],
                "stall_plays": sum(r["stall_plays"] for r in group),
                "no_op_plays": sum(r["no_op_plays"] for r in group)}

    return {"kind": "gametrix-expansion-comparison", "dependency_threshold": .8,
            "definition": "Single-entry share counts committed entry ±1/zero plays; added share also includes internal vector combinations. Ratios are weighted by plays, not averaged per game.",
            "by_arm": {arm: stats([r for r in rows if r["arm"] == arm]) for arm in sorted({r["arm"] for r in rows})},
            "cases": rows,
            "caveat": "Six selected cases per arm, independent fresh agents, no claim about human rates or shortest solutions. Winning means exclude caps. Purpose labels are self-reported, not proof of progress."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", type=g.Path, nargs="+", help="Experiment folders containing manifest.json and playtests/")
    parser.add_argument("--out", type=g.Path, required=True)
    args = parser.parse_args()
    report = summarize(args.roots)
    g.write_json(args.out, report)
    print(g.json.dumps(report["by_arm"], indent=2, ensure_ascii=False))
