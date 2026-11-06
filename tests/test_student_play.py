import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import gametrix as g


class StudentBudgetTests(unittest.TestCase):
    def test_fixed_horizon_cannot_stop_after_playing_when_next_draw_is_available(self):
        with tempfile.TemporaryDirectory() as folder:
            deck = g.generate_deck()
            deck["operations"] = [c for c in deck["operations"] if c["code"] == "negate"]
            deck_path = Path(folder)/"deck.json"
            path = Path(folder)/"case.json"
            g.write_json(deck_path, deck)
            s = g.new_session(deck_path, 1, "C11", "B01", "draw", "test", 8, 16)
            s["student_budget"] = {"fixed_horizon": True, "plans": [], "previews": []}
            g.play(s, deck, deck["operations"][0]["id"], None, {})
            self.assertEqual(s["operation_hand"], [])
            g.write_json(path, s)
            stop = subprocess.run([sys.executable, str(g.ROOT/"student_play.py"), "stop",
                                   str(path), "--note", "No remaining operation"], capture_output=True, text=True)
            self.assertEqual(stop.returncode, 2)
            self.assertEqual(g.read_json(path), s)
            end = subprocess.run([sys.executable, str(g.ROOT/"student_play.py"), "end-turn",
                                  str(path)], capture_output=True, text=True)
            self.assertEqual(end.returncode, 0)
            replay = g.read_json(path)
            self.assertEqual(replay["turn"], 2)
            self.assertEqual(len(replay["operation_hand"]), 1)
            self.assertTrue(g.audit_session(replay, deck))

    def test_preview_and_candidate_budgets_and_no_free_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            deck = Path(folder)/"deck.json"
            g.write_json(deck, g.generate_deck())
            path = Path(folder)/"case.json"
            s = g.new_session(deck, 1, "C11", "B01", "open", "test", 8, 16)
            s["student_budget"] = {"plans": [], "previews": []}
            g.write_json(path, s)

            def call(command, *args):
                proc = subprocess.run([sys.executable, str(g.ROOT/"student_play.py"), command,
                                       str(path), *args], capture_output=True, text=True)
                return proc.returncode, json.loads(proc.stdout)

            self.assertNotEqual(call("stop", "--note", "No thought yet")[0], 0)
            for operation in ("O27", "O28"):
                self.assertEqual(call("plan", "--operation", operation, "--note", "Transpose")[0], 0)
            self.assertNotEqual(call("plan", "--operation", "O29", "--note", "Third candidate")[0], 0)
            code, visible = call("preview", "--plan", "1")
            self.assertEqual(code, 0)
            self.assertNotIn("facts", visible)
            self.assertNotIn("check", visible)
            self.assertNotEqual(call("preview", "--plan", "2")[0], 0)
            self.assertEqual(call("play", "--plan", "1")[0], 0)
            self.assertNotEqual(call("play", "--plan", "2")[0], 0)  # stale matrix
            self.assertEqual(call("end-turn")[0], 0)
            replay = g.read_json(path)
            self.assertTrue(g.audit_session(replay, g.read_json(deck)))
            self.assertEqual(len(replay["student_budget"]["previews"]), 1)


if __name__ == "__main__":
    unittest.main()
