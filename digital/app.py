"""A fixed-size Arcade card table over the independent solo rules model.

Cards are movable objects. TableLayout owns where they sit; Game owns what a
move means. Both calculation modes share this interface and the same rules.
"""
from dataclasses import dataclass
from copy import deepcopy
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import random
import time
from typing import Callable

import arcade
import arcade.gui as gui
from PIL import Image, ImageDraw

import matrix as maths
from card_layout import OBJECTIVE_COPY
from .card_faces import draw_card, matrix_cell_rects, matrix_cell_at
from .game import (Game, GameError, AnswerError, MatrixCard, BINARY_CODES,
                   BUILTIN_OPERATIONS, BUILTIN_TURN_LIMIT, REMOVED_OPERATION_CODES, DECK_PATH,
                   operation_parameters, parse_answer)
from .table import TableLayout

WIDTH, HEIGHT = 1680, 1050
ROOT = Path(__file__).resolve().parents[1]
SAVE_DIR = Path(os.environ.get("GAMETRIX_SAVE_DIR", ROOT / "digital/saves"))
BG = (237, 236, 232)
PANEL = (250, 250, 247)
EDGE = (202, 207, 207)
TEXT = INK = (24, 35, 50)
MUTED = (99, 112, 133)
BLUE = (36, 92, 255)
RED = (220, 62, 52)
GREEN = (0, 139, 104)
YELLOW = (255, 196, 0)
VIOLET = (121, 83, 200)
WHITE = (255, 255, 255)
FONT = "Arial"
MODE_NAMES = {"auto": "Computer calculates", "student": "Student calculates"}
CARD_W, CARD_H = 180, 180 * 88 / 63
DEFAULT_PARAMS = {"axis": "row", "source": 0, "target": 1, "i": 0, "j": 1, "factor": "L", "delta": 1}
CHECK_NAMES = {
    "shape": "Allowed dimensions", "symmetric": "Symmetric", "invertible": "Invertible",
    "non_diagonal": "Not diagonal", "identity": "Required identity", "diagonal": "Diagonal",
    "nonzero_diagonal": "Nonzero diagonal", "three_distinct_diagonal_values": "3 distinct diagonal values",
    "row_sums_one": "Each row sums to 1", "column_sums_one": "Each column sums to 1",
    "negative_entry": "Has a negative entry", "skew_symmetric": "Transpose equals negative",
    "nonzero": "Not the zero matrix", "involution": "A squared equals identity",
    "determinant_one": "Determinant is 1", "two_nonzeros_per_row": "2+ nonzeros in each row",
    "two_nonzeros_per_column": "2+ nonzeros in each column", "rank_two": "Rank is 2",
    "idempotent": "A squared equals A", "cube_zero": "A cubed is zero",
    "square_nonzero": "A squared is nonzero", "cube_identity": "A cubed equals identity",
    "not_signed_permutation": "Not a signed permutation", "nonzero_vectors": "Nonzero vectors",
    "orthogonal_vectors": "Pairwise orthogonal vectors", "no_zero_rows": "No zero rows",
    "no_zero_columns": "No zero columns", "row_sums_zero": "Each row sums to 0",
    "row_sums_n": "Row sums equal column count", "column_sums_m": "Column sums equal row count",
}


def rectangle(x, y, w, h, fill, border=None, thickness=1):
    rect = arcade.LBWH(x, y, w, h)
    arcade.draw_rect_filled(rect, fill)
    if border:
        arcade.draw_rect_outline(rect, border, thickness)


@lru_cache(maxsize=128)
def _panel_texture(w, h, fill, border, radius):
    image = Image.new("RGBA", (w * 2 + 2, h * 2 + 2))
    ImageDraw.Draw(image).rounded_rectangle((1, 1, w * 2, h * 2), radius=radius * 2,
                                           fill=fill, outline=border, width=2)
    return arcade.Texture(image)


def panel(x, y, w, h, fill=PANEL, border=EDGE, radius=14, shadow=False):
    if shadow:
        panel(x + 2, y - 5, w, h, (24, 35, 50, 19), None, radius)
    arcade.draw_texture_rect(_panel_texture(round(w), round(h), tuple(fill),
                                           tuple(border) if border else None, radius), arcade.LBWH(x, y, w, h))


@lru_cache(maxsize=1024)
def _label(value, x, y, color, size, width, bold, align):
    return arcade.Text(value, x, y, color, size, width=int(width) if width else None,
                       font_name=FONT, bold=bold, anchor_y="top", align=align, multiline=bool(width))


def label(value, x, y, color=TEXT, size=12, width=None, bold=False, align="left"):
    _label(str(value), x, y, tuple(color), size, width, bold, align).draw()


def short(value, length=110):
    value = str(value)
    return value if len(value) <= length else value[:length - 1] + "…"


def inside(x, y, rect):
    rx, ry, w, h = rect
    return rx <= x <= rx + w and ry <= y <= ry + h


def matrix_text(values):
    return "\n".join("    ".join(str(x) for x in row) for row in values)


def field_options(**options):
    styles = {name: gui.UIInputText.UIStyle(bg=WHITE, border=BLUE if name in ("hover", "press") else EDGE,
                                          border_width=1) for name in ("normal", "hover", "press", "disabled", "invalid")}
    return dict(text_color=TEXT, caret_color=BLUE, font_name=FONT, style=styles, **options)


def settings_text(code, params):
    names = {"axis": "Use", "source": "From", "target": "To", "factor": "Keep factor",
             "i": "First" if code == "swap" else "Row", "j": "Second" if code == "swap" else "Column", "delta": "Change"}
    parts = []
    for key in operation_parameters(code):
        value = params[key]
        if key in ("i", "j", "source", "target"):
            value += 1
        elif key == "axis":
            value = "rows" if value == "row" else "columns"
        elif key == "delta":
            value = "add" if value == 1 else "subtract"
        parts.append(f"{names[key]}: {value}")
    return "   ·   ".join(parts) or "No extra settings"


@dataclass
class Button:
    x: float
    y: float
    w: float
    h: float
    text: str
    action: Callable
    selected: bool = False
    enabled: bool = True
    accent: tuple = INK
    size: int = 12

    def contains(self, x, y):
        return inside(x, y, (self.x, self.y, self.w, self.h))

    def draw(self, mouse):
        hover = self.contains(*mouse) and self.enabled
        fill = self.accent if self.selected else ((232, 236, 242) if hover else PANEL)
        ink = (INK if self.accent == YELLOW else WHITE) if self.selected else TEXT
        if not self.enabled:
            fill, ink = (231, 232, 229), (150, 156, 164)
        panel(self.x, self.y, self.w, self.h, fill, self.accent if hover else EDGE, 8)
        label(self.text, self.x + 8, self.y + self.h / 2 + self.size * .65,
              ink, self.size, self.w - 16, bold=self.selected, align="center")


class Screen(arcade.View):
    def __init__(self):
        super().__init__(background_color=BG)
        self.buttons = []
        self.mouse = (-1, -1)
        self.inputs = gui.UIManager()

    def button(self, x, y, w, h, text, action, **kwargs):
        result = Button(x, y, w, h, text, action, **kwargs)
        self.buttons.append(result)
        return result

    def on_show_view(self):
        self.inputs.enable()

    def on_hide_view(self):
        self.inputs.disable()

    def on_mouse_motion(self, x, y, dx, dy):
        self.mouse = x, y

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            for item in reversed(self.buttons):
                if item.enabled and item.contains(x, y):
                    item.action()
                    return True
        return False

    def draw_controls(self):
        for item in self.buttons:
            item.draw(self.mouse)
        self.inputs.draw()


class Menu(Screen):
    def __init__(self, mode="auto"):
        super().__init__()
        self.mode = mode
        self.deck = json.loads(DECK_PATH.read_text())
        self.goals = self.deck["objectives"]
        self.goal_index = 0
        self.random_goal = True
        self.seed = gui.UIInputText(**field_options(x=160, y=302, width=264, height=43,
                                                  text=str(random.randrange(1, 1000000)), font_size=18))
        self.inputs.add(self.seed)
        self.error = ""
        self.rebuild()

    def rebuild(self):
        self.buttons.clear()
        for i, mode in enumerate(("auto", "student")):
            self.button(160 + i * 287, 710, 270, 58, MODE_NAMES[mode], lambda m=mode: self.set_mode(m),
                        selected=self.mode == mode, accent=BLUE, size=16)
        self.button(980, 244, 56, 40, "←", lambda: self.change_goal(-1))
        self.button(1380, 244, 56, 40, "→", lambda: self.change_goal(1))
        self.button(1080, 244, 260, 40, "Random objective", self.shuffle_goal,
                    selected=self.random_goal, accent=GREEN)
        self.button(442, 302, 157, 43, "Random seed", self.random_seed)
        self.button(160, 195, 264, 58, "Start new game", self.start, selected=True, accent=GREEN, size=17)
        self.button(442, 195, 275, 58, "Continue saved game", self.resume,
                    enabled=(SAVE_DIR / f"{self.mode}.json").exists(), size=15)

    def set_mode(self, mode):
        self.mode, self.error = mode, ""
        self.rebuild()

    def change_goal(self, delta):
        self.goal_index = (self.current_goal_index() + delta) % len(self.goals)
        self.random_goal = False
        self.rebuild()

    def current_goal_index(self):
        if self.random_goal:
            seed = self.seed.text.strip()
            try:
                seed = str(int(seed))
            except ValueError:
                pass
            return random.Random(f"objective:{seed}").randrange(len(self.goals))
        return self.goal_index

    def shuffle_goal(self):
        self.random_goal = True
        self.random_seed()
        self.rebuild()

    def random_seed(self):
        self.seed.text = str(random.randrange(1, 1000000))

    def start(self):
        try:
            if len(self.seed.text) > 18:
                raise ValueError("Enter a whole-number seed of at most 18 digits.")
            game = Game(self.mode, self.goals[self.current_goal_index()]["id"], int(self.seed.text.strip()))
            board = Board(game)
            path = SAVE_DIR / f"{self.mode}.json"
            if path.exists():
                path.with_suffix(".previous.json").write_bytes(path.read_bytes())
            board.save()
            self.window.show_view(board)
        except (ValueError, OSError) as exc:
            self.error = str(exc) or "Enter a whole-number seed."

    def resume(self):
        try:
            data = json.loads((SAVE_DIR / f"{self.mode}.json").read_text())
            board = Board(Game.from_dict(data), data.get("ui_state"))
            self.window.show_view(Summary(board) if board.game.finished else board)
        except (ValueError, OSError) as exc:
            self.error = str(exc)

    def on_draw(self):
        self.clear()
        label("[ × ]", 157, 955, BLUE, 42)
        label("GameTrix", 288, 950, TEXT, 40, bold=True)
        label("Matrix cards. Eight turns.", 160, 861, TEXT, 28)
        label("DEAL SEED", 160, 385, MUTED, 11, bold=True)
        panel(858, 196, 674, 729, (226, 231, 223), None, 26)
        label("YOUR OBJECTIVE", 908, 875, GREEN, 12, bold=True)
        goal_index = self.current_goal_index()
        goal = self.goals[goal_index]
        draw_card(goal, "objective", 1054, 357, 290, 290 * 88 / 63, raised=True)
        label(f"{goal_index + 1} / {len(self.goals)}", 1090, 318, MUTED, 13, width=235, align="center")
        if self.error:
            label(self.error, 160, 112, RED, 13, width=1300)
        self.draw_controls()


class Board(Screen):
    TABLE_RECT = (22, 330, 1036, 700)
    TABLE_BOUNDS = (40, 348, 1000, 566)
    HAND_RECT = (22, 18, 1636, 300)
    HAND_CLIP = (36, 32, 1608, 267)
    OBJECTIVE_RECT = (40, 763, CARD_W, CARD_H)
    SLOT_W = 174
    SLOT_H = SLOT_W * 88 / 63
    SLOT_BOXES = {"A": (1092, 739, SLOT_W, SLOT_H),
                  "operation": (1286, 739, SLOT_W, SLOT_H),
                  "B": (1480, 739, SLOT_W, SLOT_H),
                  "remove": (1092, 346, SLOT_W, SLOT_H)}
    RESULT_RECT = (1280, 346, 224, 224 * 88 / 63)
    HAND_STEP = CARD_W + 22
    RESULT_ID = "__preview__"

    def __init__(self, game, ui_state=None):
        super().__init__()
        self.game = game
        self.layout = TableLayout(game)
        self.params = dict(DEFAULT_PARAMS)
        self.builtin_id = None
        self.hand_scroll = self.hand_target = 0.0
        self.selected_id = None
        self.status, self.status_color = "", MUTED
        self.save_warning = ""
        self.drag = None
        self.scrolling = False
        self.last_click = (None, 0.0)
        self.hover_id = None
        self.result_cell = None
        self.fields = []
        self.preview_action = self.preview_values = self.preview_card = None
        self.preview_signature = None
        self.preview_error = ""
        self.preview_verified = False
        self.draft_dirty = False
        self.save_delay = 0.0
        if ui_state is not None:
            try:
                layout_data = deepcopy(ui_state["layout"])
                retired = {c["id"]: c["code"] for c in game._deck["operations"]
                           if c["code"] in REMOVED_OPERATION_CODES}
                layout_data["hand"] = [cid for cid in layout_data["hand"] if cid not in retired]
                layout_data["table"] = {cid: pos for cid, pos in layout_data["table"].items() if cid not in retired}
                old_op = layout_data["slots"].get("operation")
                if old_op in retired:
                    self.builtin_id = "builtin:" + retired[old_op]
                    layout_data["slots"]["operation"] = None
                self.layout = TableLayout.from_dict(game, layout_data)
                params = ui_state.get("params", {})
                for key, default in DEFAULT_PARAMS.items():
                    value = params.get(key, default)
                    if key in ("source", "target", "i", "j"):
                        self.params[key] = value if type(value) is int and 0 <= value < 4 else default
                    elif key == "axis":
                        self.params[key] = value if value in ("row", "column") else default
                    elif key == "factor":
                        self.params[key] = value if value in ("L", "U") else default
                    elif key == "delta":
                        self.params[key] = value if type(value) is int and value in (-1, 1) else default
                builtin = ui_state.get("builtin_id", self.builtin_id)
                self.builtin_id = builtin if isinstance(builtin, str) and builtin in BUILTIN_OPERATIONS else None
                scroll = ui_state.get("hand_scroll", ui_state.get("hand_page", 0) * 9 * self.HAND_STEP)
                if type(scroll) in (int, float) and math.isfinite(scroll):
                    self.hand_scroll = self.hand_target = max(0.0, scroll)
                for cid, (x, y) in list(self.layout.table.items()):
                    self.layout.table[cid] = self.clamped_position(x, y)
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
                self.layout = TableLayout(game)
                self.status = "Card positions reset."
        self.rebuild()
        if isinstance(ui_state, dict) and self.fields:
            draft = ui_state.get("draft", {})
            if isinstance(draft, dict) and draft.get("action") == self.preview_action:
                entries = draft.get("entries")
                if (isinstance(entries, list) and len(entries) == len(self.fields)
                        and all(isinstance(value, str) and len(value) <= 164 for value in entries)):
                    for field, value in zip(self.fields, entries):
                        field.text = value

    def save(self):
        try:
            state = {"layout": self.layout.to_dict(), "params": dict(self.params),
                     "hand_scroll": self.hand_target, "builtin_id": self.builtin_id}
            if self.fields:
                state["draft"] = {"action": self.preview_action,
                                  "entries": [field.text for field in self.fields]}
            self.game.save(SAVE_DIR / f"{self.game.mode}.json", ui_state=state)
            self.save_warning = ""
            self.draft_dirty = False
            return True
        except OSError as exc:
            self.save_warning = f"Could not save: {exc}"
            return False

    def op(self):
        cid = self.layout.slots["operation"]
        return self.layout.card(cid) if cid else BUILTIN_OPERATIONS.get(self.builtin_id)

    def selected_card(self, slot):
        cid = self.layout.slots[slot]
        return self.layout.card(cid) if cid else None

    def max_scroll(self):
        return max(0, len(self.layout.hand) * self.HAND_STEP - 22 - self.HAND_CLIP[2])

    def hand_rects(self):
        span = len(self.layout.hand) * self.HAND_STEP - 22
        start = self.HAND_CLIP[0] + max(0, (self.HAND_CLIP[2] - span) / 2) - self.hand_scroll
        return [(cid, (start + i * self.HAND_STEP,
                       38 + (10 if self.hover_id == cid and not self.drag else 0), CARD_W, CARD_H))
                for i, cid in enumerate(self.layout.hand)]

    def card_rects(self):
        cards = self.hand_rects()
        cards.extend((cid, (*position, CARD_W, CARD_H)) for cid, position in self.layout.table.items())
        cards.extend((cid, self.SLOT_BOXES[slot]) for slot, cid in self.layout.slots.items() if cid)
        return cards

    def card_at(self, x, y):
        for cid, rect in reversed(self.card_rects()):
            if cid in self.layout.hand:
                if not inside(x, y, self.HAND_CLIP):
                    continue
                rect = (rect[0], 38, rect[2], CARD_H + 10)
            if inside(x, y, rect):
                return cid, rect
        return None

    def clamped_position(self, x, y):
        bx, by, bw, bh = self.TABLE_BOUNDS
        x = max(bx, min(x, bx + bw - CARD_W))
        y = max(by, min(y, by + bh - CARD_H))
        ox, oy, ow, _ = self.OBJECTIVE_RECT
        if x < ox + ow + 16 and y + CARD_H > oy - 16:
            y = oy - CARD_H - 16
        return x, y

    def scroll_hand(self, amount):
        self.hand_target = max(0.0, min(self.max_scroll(), self.hand_target + amount))
        self.hover_id = None
        self.draft_dirty, self.save_delay = True, 0.7

    def reveal_hand_card(self, cid):
        if cid not in self.layout.hand:
            return
        index = self.layout.hand.index(cid)
        left, right = index * self.HAND_STEP, index * self.HAND_STEP + CARD_W
        if left < self.hand_target:
            self.hand_target = left
        elif right > self.hand_target + self.HAND_CLIP[2]:
            self.hand_target = right - self.HAND_CLIP[2]
        self.hand_target = max(0, min(self.max_scroll(), self.hand_target))

    def index_limit(self, key):
        A, B = self.selected_card("A"), self.selected_card("B")
        if not A:
            return 4
        code = self.op()["code"] if self.op() else ""
        if code.startswith("entry_"):
            return maths.shape(A.values)[0 if key == "i" else 1]
        source = B if key == "source" and code in BINARY_CODES else A
        return maths.shape(source.values)[0 if self.params["axis"] == "row" else 1] if source else 4

    def step_index(self, key, delta):
        self.params[key] = (self.params[key] + delta) % self.index_limit(key)
        self.rebuild()
        self.save()

    def toggle(self, key, choices):
        self.params[key] = choices[(choices.index(self.params[key]) + 1) % len(choices)]
        self.rebuild()
        self.save()

    def stepper(self, x, y, key, title):
        self.button(x, y, 26, 30, "−", lambda: self.step_index(key, -1))
        self.button(x + 26, y, 82, 30, f"{title} {self.params[key] + 1}", lambda: None, size=11)
        self.button(x + 108, y, 26, 30, "+", lambda: self.step_index(key, 1))

    def choose_builtin(self, operation_id):
        if not self.game.builtin_remaining(operation_id):
            return
        old = self.layout.slots["operation"]
        if old:
            self.layout.move_to_hand(old)
        self.builtin_id = None if self.builtin_id == operation_id and not old else operation_id
        self.params = dict(DEFAULT_PARAMS)
        self.rebuild()
        self.save()

    def rebuild(self):
        self.hand_target = max(0, min(self.max_scroll(), self.hand_target))
        self.hand_scroll = max(0, min(self.max_scroll(), self.hand_scroll))
        self.buttons.clear()
        self.button(680, 977, 112, 33, "Menu", self.menu)
        self.button(802, 977, 112, 33, "History", lambda: self.window.show_view(History(self)))
        self.button(924, 977, 110, 33, "Help", lambda: self.window.show_view(Help(self)))
        self.button(854, 931, 180, 34, "Finish game" if self.game.turn == 8 else "End turn", self.confirm_end,
                    selected=True, accent=INK, enabled=not self.game.finished)
        self.button(1092, 704, 132, 28, "Clear slots", self.clear_slots,
                    enabled=any(self.layout.slots[s] for s in TableLayout.ACTION_SLOTS)
                            or self.builtin_id is not None, size=11)
        for x, width, operation_id, title in ((1252, 118, "builtin:add", "+ Add"),
                                             (1380, 160, "builtin:multiply", "× Multiply")):
            remaining = self.game.builtin_remaining(operation_id)
            self.button(x, 704, width, 28, f"{title}  {remaining}/{BUILTIN_TURN_LIMIT}",
                        lambda oid=operation_id: self.choose_builtin(oid),
                        selected=self.builtin_id == operation_id and not self.layout.slots["operation"],
                        enabled=remaining > 0, accent=GREEN, size=11)
        op = self.op()
        if op:
            parameters = operation_parameters(op["code"])
            for key in ("source", "target", "i", "j"):
                self.params[key] = min(self.params[key], self.index_limit(key) - 1)
            if "axis" in parameters:
                self.button(1092, 666, 110, 30, "Rows" if self.params["axis"] == "row" else "Columns",
                            lambda: self.toggle("axis", ["row", "column"]), selected=True, accent=BLUE, size=11)
            if "source" in parameters:
                self.stepper(1213, 666, "source", "From")
            if "target" in parameters:
                self.stepper(1358, 666, "target", "To")
            if "i" in parameters:
                self.stepper(1213 if "axis" in parameters else 1092, 666, "i", "First" if "axis" in parameters else "Row")
                self.stepper(1358 if "axis" in parameters else 1237, 666, "j", "Second" if "axis" in parameters else "Col")
            if "delta" in parameters:
                self.button(1503, 666, 151, 30, "+1" if self.params["delta"] == 1 else "−1",
                            lambda: self.toggle("delta", [1, -1]), size=13)
            if "factor" in parameters:
                self.button(1092, 666, 134, 30, f"Factor {self.params['factor']}", lambda: self.toggle("factor", ["L", "U"]), size=11)
        self.refresh_preview()
        self.button(1518, 353, 124, 38, "Take result", self.take_result, selected=True, accent=GREEN,
                    enabled=self.preview_card is not None and not self.game.finished, size=12)
        if self.game.mode == "student":
            self.button(1518, 403, 124, 34, "Check", self.verify_preview, enabled=self.preview_card is not None, size=12)

    def clear_slots(self):
        for cid in [self.layout.slots[s] for s in TableLayout.ACTION_SLOTS]:
            if cid:
                self.layout.move_to_hand(cid)
        self.builtin_id = None
        self.params = dict(DEFAULT_PARAMS)
        self.status = ""
        self.rebuild()
        self.save()

    def place_in_remove_slot(self, card_id):
        """Keep the newest card retrievable; permanently remove its predecessor."""
        self.layout.card(card_id)
        previous = self.layout.slots["remove"]
        if previous == card_id:
            return
        if previous is not None:
            self.game.remove_card(previous)
            self.layout.sync(self.game)
        self.layout.place_slot(card_id, "remove")

    def inspect_selected(self):
        if self.selected_id and self.selected_id in self.layout._cards:
            self.window.show_view(Inspect(self, self.layout.card(self.selected_id), self.layout.kind(self.selected_id)))

    def menu(self):
        if self.save():
            self.window.show_view(Menu(self.game.mode))

    def selected_action(self):
        op = self.op()
        if not op:
            raise GameError("Choose an operation.")
        if not self.layout.slots["A"]:
            raise GameError("A is empty.")
        binary = op["code"] in BINARY_CODES
        if binary and not self.layout.slots["B"]:
            raise GameError("B is empty.")
        if not binary and self.layout.slots["B"]:
            raise GameError("This operation uses only A.")
        return {"operation_id": op["id"], "a_id": self.layout.slots["A"], "b_id": self.layout.slots["B"],
                **{key: self.params[key] for key in operation_parameters(op["code"])}}

    def refresh_preview(self):
        action = None
        error = ""
        try:
            action = self.selected_action()
        except GameError as exc:
            if self.op() and self.layout.slots["A"] and self.layout.slots["B"]:
                error = str(exc)
        signature = (self.game.turn, len(self.game.history), tuple(sorted(action.items())) if action else None)
        if signature == self.preview_signature:
            return
        self.preview_signature = signature
        for field in self.fields:
            self.inputs.remove(field)
        self.fields.clear()
        self.preview_action = self.preview_values = self.preview_card = None
        self.preview_error, self.preview_verified = error, False
        self.result_cell = None
        if action is None or self.game.finished:
            return
        try:
            values = self.game.calculate(**action)
        except GameError as exc:
            self.preview_error = str(exc)
            return
        self.preview_action, self.preview_values = action, values
        self.preview_card = MatrixCard("G…", "blue", values)
        if self.game.mode == "student":
            rows, cols = maths.shape(values)
            for row in matrix_cell_rects(rows, cols, *self.RESULT_RECT):
                for x, y, w, h in row:
                    field = InlineAnswerInput(self, len(self.fields), **field_options(
                        x=x + 2, y=y + 2, width=w - 4, height=h - 4, text="", font_size=13))
                    self.fields.append(field)
                    self.inputs.add(field)

    def answer_edited(self):
        self.preview_verified = False
        self.preview_error = ""
        self.draft_dirty, self.save_delay = True, 0.7

    def answer(self):
        rows, cols = maths.shape(self.preview_values)
        return [[self.fields[i * cols + j].text for j in range(cols)] for i in range(rows)]

    def verify_preview(self):
        if not self.preview_card:
            return False
        if self.game.mode == "auto":
            return True
        try:
            if parse_answer(self.answer()) != self.game.calculate(**self.preview_action):
                raise AnswerError("Not quite. Try again.")
        except GameError as exc:
            self.preview_error, self.preview_verified = str(exc), False
            return False
        self.preview_error, self.preview_verified = "", True
        self.save()
        return True

    def blur_fields(self):
        for field in self.fields:
            field.deactivate()

    def take_result(self, destination=None, position=None):
        if not self.preview_card or self.game.finished:
            return None
        if destination == "operation":
            return None
        if not self.verify_preview():
            return None
        action = dict(self.preview_action)
        submitted = self.answer() if self.game.mode == "student" else None
        try:
            outcome = self.game.perform(**action, answer=submitted)
        except GameError as exc:
            self.preview_error = str(exc)
            return None
        self.layout.sync(self.game)
        cid = outcome["result"].id
        if destination in ("A", "B"):
            self.layout.place_slot(cid, destination)
        elif destination == "remove":
            self.place_in_remove_slot(cid)
        elif destination == "table":
            self.layout.move_to_table(cid, *self.clamped_position(*position))
        self.selected_id = cid
        self.reveal_hand_card(cid)
        self.status, self.status_color = ("+1 point", GREEN) if outcome["scored"] else ("", MUTED)
        self.rebuild()
        self.save()
        return outcome

    def confirm_end(self):
        final = self.game.turn == 8
        self.window.show_view(Confirm(self, "Finish this game?" if final else "End this turn?",
                                     "Untaken results are not played.", self.end_turn))

    def end_turn(self):
        self.game.end_turn()
        self.layout.sync(self.game)
        self.hand_target = self.max_scroll()
        self.status = ""
        self.rebuild()
        self.save()
        if self.game.finished:
            self.window.show_view(Summary(self))
        elif self.window.current_view is not self:
            self.window.show_view(self)

    def highlight_cells(self, slot):
        card, op = self.selected_card(slot), self.op()
        if not card or not op:
            return {}
        rows, cols = maths.shape(card.values)
        source, target = (255, 191, 35, 70), (36, 130, 255, 65)
        cells = {}
        def vector(index, color):
            cells.update({(i, j): color for i in range(rows) for j in range(cols)
                          if (i if self.params["axis"] == "row" else j) == index})
        code = op["code"]
        if code.startswith("entry_") and slot == "A":
            cells[(self.params["i"], self.params["j"])] = target
        elif code in ("add_vector", "replace_vector", "append_vector"):
            if slot == "B":
                vector(self.params["source"], source)
            elif code != "append_vector":
                vector(self.params["target"], target)
        elif code == "combine_vectors" and slot == "A":
            vector(self.params["source"], source)
            vector(self.params["target"], target)
        elif code == "swap" and slot == "A":
            vector(self.params["i"], source)
            vector(self.params["j"], target)
        elif code == "multiply" and self.result_cell is not None:
            ri, rj = self.result_cell
            cells = {(i, j): target if slot == "A" else source for i in range(rows) for j in range(cols)
                     if (i == ri if slot == "A" else j == rj)}
        elif code in ("add", "subtract") and self.result_cell is not None:
            cells[self.result_cell] = target if slot == "A" else source
        elif slot == "A" or code in BINARY_CODES:
            cells = {(i, j): target if slot == "A" else source for i in range(rows) for j in range(cols)}
        return cells

    def select_matrix_cell(self, cid, x, y):
        slot = next((name for name in ("A", "B") if self.layout.slots[name] == cid), None)
        op = self.op()
        if not slot or not op:
            return
        card = self.selected_card(slot)
        cell = matrix_cell_at(*maths.shape(card.values), self.SLOT_BOXES[slot], x, y)
        if cell is None:
            return
        i, j = cell
        code = op["code"]
        if code.startswith("entry_") and slot == "A":
            self.params.update(i=i, j=j)
        elif code in ("add_vector", "replace_vector", "append_vector", "combine_vectors"):
            index = i if self.params["axis"] == "row" else j
            key = "source" if slot == "B" else "target"
            if key in operation_parameters(code):
                self.params[key] = index
        else:
            return
        self.rebuild()
        self.save()

    def on_mouse_motion(self, x, y, dx, dy):
        super().on_mouse_motion(x, y, dx, dy)
        hit = self.card_at(x, y)
        self.hover_id = hit[0] if hit else None
        active = next((field for field in self.fields if field.active), None)
        if active:
            self.result_cell = divmod(active.index, maths.shape(self.preview_values)[1])
        else:
            self.result_cell = (matrix_cell_at(*maths.shape(self.preview_values), self.RESULT_RECT, x, y)
                                if self.preview_values else None)

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT and self.max_scroll() and inside(x, y, (36, 18, 1608, 12)):
            self.scrolling = True
            self.set_scroll_from_pointer(x)
            return True
        if inside(x, y, self.OBJECTIVE_RECT):
            self.window.show_view(Inspect(self, self.game.objective, "objective"))
            return True
        for item in reversed(self.buttons):
            if item.enabled and item.contains(x, y) and button == arcade.MOUSE_BUTTON_LEFT:
                item.action()
                return True
        if self.preview_card and inside(x, y, self.RESULT_RECT):
            if button == arcade.MOUSE_BUTTON_LEFT:
                if any(inside(x, y, (field.left, field.bottom, field.width, field.height)) for field in self.fields):
                    return False
                self.blur_fields()
                self.drag = {"id": self.RESULT_ID, "start": (x, y),
                             "offset": (x - self.RESULT_RECT[0], y - self.RESULT_RECT[1]),
                             "position": self.RESULT_RECT[:2], "moved": False}
                return True
            return False
        hit = self.card_at(x, y)
        if hit and button in (arcade.MOUSE_BUTTON_LEFT, arcade.MOUSE_BUTTON_RIGHT):
            cid, rect = hit
            self.selected_id = cid
            self.blur_fields()
            if button == arcade.MOUSE_BUTTON_RIGHT:
                self.window.show_view(Inspect(self, self.layout.card(cid), self.layout.kind(cid)))
                return True
            now = time.monotonic()
            if self.last_click[0] == cid and now - self.last_click[1] < .32:
                self.last_click = (None, 0)
                self.window.show_view(Inspect(self, self.layout.card(cid), self.layout.kind(cid)))
                return True
            self.last_click = (cid, now)
            if cid in self.layout.table:
                self.layout.bring_to_front(cid)
            self.drag = {"id": cid, "start": (x, y), "offset": (x - rect[0], y - rect[1]),
                         "position": (rect[0], rect[1]), "moved": False}
            return True
        return False

    def set_scroll_from_pointer(self, x):
        self.hand_target = max(0, min(1, (x - 36) / 1608)) * self.max_scroll()
        self.hand_scroll = self.hand_target
        self.draft_dirty, self.save_delay = True, 0.7

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.mouse = x, y
        if self.scrolling:
            self.set_scroll_from_pointer(x)
            return True
        if self.drag:
            sx, sy = self.drag["start"]
            if math.hypot(x - sx, y - sy) > 5:
                self.drag["moved"] = True
            ox, oy = self.drag["offset"]
            self.drag["position"] = (x - ox, y - oy)
            return True

    def on_mouse_release(self, x, y, button, modifiers):
        if self.scrolling:
            self.scrolling = False
            self.save()
            return True
        if not self.drag:
            return
        drag, self.drag = self.drag, None
        cid = drag["id"]
        if drag["moved"]:
            self.last_click = (None, 0.0)
            slot = next((name for name, rect in self.SLOT_BOXES.items() if inside(x, y, rect)), None)
            if cid == self.RESULT_ID:
                if slot in ("A", "B", "remove"):
                    self.take_result(slot)
                elif inside(x, y, self.TABLE_RECT):
                    self.take_result("table", drag["position"])
                elif inside(x, y, self.HAND_RECT):
                    self.take_result("hand")
                return True
            previous_op = self.layout.slots["operation"]
            try:
                if slot == "remove":
                    self.place_in_remove_slot(cid)
                elif slot:
                    self.layout.place_slot(cid, slot)
                    if slot == "operation":
                        self.builtin_id = None
                elif inside(x, y, self.TABLE_RECT):
                    self.layout.move_to_table(cid, *self.clamped_position(*drag["position"]))
                elif inside(x, y, self.HAND_RECT):
                    before = next((key for key, rect in self.hand_rects()
                                   if key != cid and x < rect[0] + CARD_W / 2), None)
                    self.layout.move_to_hand(cid)
                    if before:
                        self.layout.hand.remove(cid)
                        self.layout.hand.insert(self.layout.hand.index(before), cid)
                if self.layout.slots["operation"] != previous_op:
                    self.params = dict(DEFAULT_PARAMS)
                self.status = ""
            except ValueError:
                self.status, self.status_color = "That card does not fit this slot.", RED
        elif cid != self.RESULT_ID:
            self.select_matrix_cell(cid, x, y)
        self.hover_id = None
        self.rebuild()
        self.save()
        return True

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if inside(x, y, self.HAND_RECT):
            self.scroll_hand((scroll_x - scroll_y) * 48)

    def on_update(self, delta_time):
        if self.drag and inside(*self.mouse, self.HAND_RECT):
            if self.mouse[0] < 95:
                self.scroll_hand(-450 * delta_time)
            elif self.mouse[0] > WIDTH - 95:
                self.scroll_hand(450 * delta_time)
        delta = self.hand_target - self.hand_scroll
        self.hand_scroll += delta * min(1, delta_time * 15)
        if abs(delta) < .2:
            self.hand_scroll = self.hand_target
        if self.draft_dirty:
            self.save_delay -= delta_time
            if self.save_delay <= 0:
                self.save()

    def on_key_press(self, symbol, modifiers):
        if any(field.active for field in self.fields):
            return
        if symbol == arcade.key.F1:
            self.window.show_view(Help(self))
        elif symbol == arcade.key.ESCAPE:
            self.drag = None
        elif symbol == arcade.key.I:
            self.inspect_selected()
        elif symbol in (arcade.key.DELETE, arcade.key.BACKSPACE) and self.selected_id in self.layout._cards:
            self.layout.move_to_hand(self.selected_id)
            self.reveal_hand_card(self.selected_id)
            self.rebuild()
            self.save()

    def draw_preview(self, rect, *, dragging=False):
        if not self.preview_card:
            return
        manual = self.game.mode == "student"
        draw_card(self.preview_card, "blue", *rect, raised=dragging,
                  selected=self.preview_verified, blank=manual,
                  highlights={self.result_cell: (36, 130, 255, 45)} if self.result_cell else None)
        if manual and dragging:
            rows, cols = maths.shape(self.preview_values)
            for i, row in enumerate(matrix_cell_rects(rows, cols, *rect)):
                for j, (x, y, w, h) in enumerate(row):
                    label(self.fields[i * cols + j].text, x, y + h / 2 + 8, TEXT, 12, w, align="center")

    def on_draw(self):
        self.clear()
        panel(*self.TABLE_RECT, fill=(225, 231, 221), border=(201, 209, 197), radius=20)
        label("GameTrix", 246, 1008, TEXT, 26, bold=True)
        label(f"Turn {self.game.turn} / 8", 246, 958, TEXT, 15, bold=True)
        label(f"Score {self.game.score}", 395, 958, GREEN, 15, bold=True)
        label("Auto" if self.game.mode == "auto" else "Manual", 499, 1000, MUTED, 12)
        panel(*self.HAND_RECT, fill=(247, 246, 241), border=(215, 216, 207), radius=18)
        label(f"Hand  {len(self.layout.hand)}", 42, 312, MUTED, 10, bold=True)
        panel(1076, 330, 582, 700, fill=(246, 247, 245), border=(211, 216, 211), radius=20)
        for slot, rect in self.SLOT_BOXES.items():
            target = self.drag and self.drag["moved"] and inside(*self.mouse, rect)
            removal = slot == "remove"
            panel(*rect, fill=(243, 234, 230) if removal else (232, 236, 230),
                  border=(RED if removal else GREEN) if target else (195, 203, 194), radius=10)
            label("Remove card" if removal else "Operation" if slot == "operation" else slot,
                  rect[0], 630 if removal else 1010,
                  MUTED, 12, rect[2], bold=True, align="center")
            if removal:
                label("Replace to remove previous", rect[0], 608, MUTED, 10, rect[2], align="center")
                if not self.layout.slots["remove"]:
                    label("Drop a card here.\nRetrieve it before replacing.",
                          rect[0] + 12, 492, MUTED, 11, rect[2] - 24, align="center")
        if self.builtin_id and not self.layout.slots["operation"]:
            remaining = self.game.builtin_remaining(self.builtin_id)
            reusable = dict(BUILTIN_OPERATIONS[self.builtin_id], id=f"{remaining}/{BUILTIN_TURN_LIMIT}")
            draw_card(reusable, "operation", *self.SLOT_BOXES["operation"])
        panel(*self.RESULT_RECT, fill=(232, 236, 230), border=(195, 203, 194), radius=12)
        label("Result", 1518, 625, TEXT, 12, bold=True)
        if self.preview_verified:
            label("✓ Ready", 1518, 598, GREEN, 12, width=124, bold=True)
        if self.preview_error:
            label(self.preview_error, 1518, 569, RED, 11, width=124)
        if self.status:
            label(self.status, 1518, 471, self.status_color, 11, width=124)
        moving_id = self.drag["id"] if self.drag and self.drag["moved"] else None
        old_scissor = self.window.ctx.scissor
        x, y, w, h = self.HAND_CLIP
        self.window.ctx.scissor = (x, y, w, h)
        try:
            for cid, rect in self.hand_rects():
                if cid != moving_id and rect[0] + CARD_W >= x and rect[0] <= x + w:
                    draw_card(self.layout.card(cid), self.layout.kind(cid), *rect,
                              raised=self.hover_id == cid, selected=cid == self.selected_id)
        finally:
            self.window.ctx.scissor = old_scissor
        if self.max_scroll():
            span = self.HAND_CLIP[2]
            thumb = span * span / (span + self.max_scroll())
            rectangle(36, 23, span, 4, (218, 222, 216))
            rectangle(36 + self.hand_scroll / self.max_scroll() * (span - thumb), 23, thumb, 4, (128, 148, 139))
        for cid, position in self.layout.table.items():
            if cid != moving_id:
                draw_card(self.layout.card(cid), self.layout.kind(cid), *position, CARD_W, CARD_H,
                          raised=self.hover_id == cid, selected=cid == self.selected_id)
        for slot, cid in self.layout.slots.items():
            if cid and cid != moving_id:
                draw_card(self.layout.card(cid), self.layout.kind(cid), *self.SLOT_BOXES[slot],
                          highlights=self.highlight_cells(slot) if slot in ("A", "B") else None,
                          raised=self.hover_id == cid, selected=cid == self.selected_id)
        draw_card(self.game.objective, "objective", *self.OBJECTIVE_RECT, raised=True)
        if moving_id != self.RESULT_ID:
            self.draw_preview(self.RESULT_RECT)
        for item in self.buttons:
            item.draw(self.mouse)
        if moving_id != self.RESULT_ID:
            self.inputs.draw()
        if moving_id:
            px, py = self.drag["position"]
            if moving_id == self.RESULT_ID:
                self.draw_preview((px, py, self.RESULT_RECT[2], self.RESULT_RECT[3]), dragging=True)
            else:
                draw_card(self.layout.card(moving_id), self.layout.kind(moving_id), px, py, CARD_W, CARD_H,
                          raised=True, selected=True)
        if self.save_warning:
            panel(246, 888, 788, 30, (255, 233, 229), None, 5)
            label(short(self.save_warning, 110), 258, 911, RED, 11, width=764)

class Modal(Screen):
    """Keep the card table visible under a raised, dimmed overlay."""
    def __init__(self, previous, rect=(280, 190, 1120, 670)):
        super().__init__()
        self.previous, self.rect = previous, rect

    def background(self):
        self.previous.on_draw()
        rectangle(0, 0, WIDTH, HEIGHT, (24, 35, 50, 105))
        panel(*self.rect, fill=PANEL, border=(216, 219, 219), radius=22, shadow=True)

    def back(self):
        self.window.show_view(self.previous)

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ESCAPE:
            self.back()


class Inspect(Modal):
    def __init__(self, previous, card, kind=None):
        super().__init__(previous, (252, 106, 1176, 838))
        self.card = card
        self.kind = kind or card.color
        self.box = None
        if self.kind in ("blue", "red"):
            self.box = gui.UIInputText(**field_options(x=724, y=322, width=642, height=390,
                                                       text=matrix_text(card.values), multiline=True, font_size=19))
            self.inputs.add(self.box)
        self.button(724, 176, 286, 49, "Back to the table", self.back, selected=True, size=15)
        if self.box:
            self.button(1030, 176, 336, 49, "Restore original text", lambda: setattr(self.box, "text", matrix_text(self.card.values)))

    def on_draw(self):
        self.background()
        draw_card(self.card, self.kind, 302, 191, 366, 366 * 88 / 63, raised=True)
        label("Read the card", 302, 892, TEXT, 29, bold=True)
        if self.box:
            label("Exact values", 724, 833, TEXT, 23, bold=True)
            label("Select and copy the full values below.", 724, 788, MUTED, 14)
            label("Long values may be shortened on small cards. Editing this scratch field does not change your card.",
                  724, 755, MUTED, 12, width=630)
        elif self.kind == "operation":
            label(self.card["name"], 724, 826, TEXT, 25, width=635, bold=True)
            label(self.card["rule"], 724, 754, TEXT, 18, width=630)
            label("Place this card in the middle calculation slot. Add the matrix cards in A and, when needed, B.",
                  724, 476, MUTED, 15, width=620)
        else:
            label(self.card["name"], 724, 826, TEXT, 25, width=635, bold=True)
            label(OBJECTIVE_COPY[self.card["id"]], 724, 751, TEXT, 18, width=630)
            label(self.card["shape"], 724, 570, GREEN, 16, bold=True)
            label("Each different result that satisfies this objective earns one point. The example on the card illustrates the conditions.",
                  724, 499, MUTED, 15, width=620)
        self.draw_controls()


class InlineAnswerInput(gui.UIInputText):
    def __init__(self, owner, index, **kwargs):
        self.owner, self.index = owner, index
        super().__init__(**kwargs)
        self.layout.content_valign = "center"
        self.doc.set_style(0, len(self.text), {"align": "center"})

    def activate(self):
        super().activate()
        if self.owner.preview_values:
            self.owner.result_cell = divmod(self.index, maths.shape(self.owner.preview_values)[1])

    def on_event(self, event):
        if self.active and isinstance(event, gui.UIKeyPressEvent):
            if event.symbol == arcade.key.TAB:
                self.deactivate()
                delta = -1 if event.modifiers & arcade.key.MOD_SHIFT else 1
                self.owner.fields[(self.index + delta) % len(self.owner.fields)].activate()
                return True
            if event.symbol in (arcade.key.ENTER, arcade.key.NUM_ENTER):
                self.owner.verify_preview()
                return True
            if event.symbol == arcade.key.ESCAPE:
                self.deactivate()
                return True
        before = self.text
        handled = super().on_event(event)
        if self.text != before:
            if len(self.text) > 164:
                self.text = before
            else:
                self.owner.answer_edited()
        return handled


class Confirm(Modal):
    def __init__(self, board, title, body, action):
        super().__init__(board, (470, 325, 740, 400))
        self.title, self.body = title, body
        self.button(516, 379, 301, 49, "Yes, continue", action, selected=True, size=15)
        self.button(837, 379, 325, 49, "Keep playing", self.back, size=15)

    def on_draw(self):
        self.background()
        label(self.title, 516, 674, TEXT, 28, bold=True)
        label(self.body, 516, 609, MUTED, 17, width=640)
        self.draw_controls()


class History(Modal):
    def __init__(self, board):
        super().__init__(board, (200, 120, 1280, 820))
        self.board, self.page = board, 0
        self.rebuild()

    def back(self):
        self.window.show_view(Summary(self.board) if self.board.game.finished else self.board)

    def rebuild(self):
        self.buttons.clear()
        self.button(246, 170, 264, 46, "Back to score" if self.board.game.finished else "Back to table",
                    self.back, selected=True)
        self.button(1240, 170, 86, 46, "←", lambda: self.change(-1), enabled=self.page > 0)
        self.button(1344, 170, 86, 46, "→", lambda: self.change(1), enabled=(self.page + 1) * 7 < len(self.board.game.history))
        for i, move in enumerate(list(reversed(self.board.game.history))[self.page * 7:(self.page + 1) * 7]):
            card = self.board.game.get_matrix(move["result_id"])
            self.button(1267, 704 - i * 63, 158, 38, "Read result", lambda c=card: self.window.show_view(Inspect(self, c)))

    def change(self, delta):
        self.page += delta
        self.rebuild()

    def on_draw(self):
        self.background()
        label("Move history", 246, 891, TEXT, 30, bold=True)
        label("Every successful result remains a blue card. Most recent first.", 246, 838, MUTED, 14)
        for i, move in enumerate(list(reversed(self.board.game.history))[self.page * 7:(self.page + 1) * 7]):
            y = 749 - i * 63
            panel(246, y - 47, 1184, 53, WHITE, EDGE, 8)
            label(f"Turn {move['turn']}", 260, y - 8, MUTED, 12)
            label(move["operation_title"], 358, y - 8, TEXT, 14, width=410)
            label(f"{move['a_id']}" + (f" · {move['b_id']}" if move["b_id"] else "") + f" → {move['result_id']}",
                  795, y - 8, MUTED, 12, width=310)
            label("+1" if move["scored"] else "0", 1174, y - 6, GREEN if move["scored"] else MUTED, 17, bold=True)
        if not self.board.game.history:
            label("No moves yet. Place cards in the calculation slots to begin.", 246, 746, MUTED, 18)
        self.draw_controls()


class Summary(Modal):
    def __init__(self, board):
        super().__init__(board, (250, 170, 1180, 710))
        self.board = board
        self.button(302, 234, 283, 50, "Save & new game", self.new_game, selected=True, accent=GREEN, size=16)
        self.button(607, 234, 283, 50, "Review moves", lambda: self.window.show_view(History(board)), size=16)
        self.button(912, 234, 212, 50, "Retry save", board.save, size=14)

    def new_game(self):
        if self.board.save():
            self.window.show_view(Menu(self.board.game.mode))

    def on_key_press(self, symbol, modifiers):
        pass  # A finished table must not accept another move.

    def on_draw(self):
        self.background()
        game = self.board.game
        label("Eight turns complete", 302, 824, TEXT, 34, bold=True)
        label(MODE_NAMES[game.mode] + f"  ·  seed {game.seed}", 302, 768, MUTED, 14)
        draw_card(game.objective, "objective", 1078, 378, 238, 238 * 88 / 63, raised=True)
        label(str(game.score), 302, 689, GREEN, 92, bold=True)
        label("different qualifying matrices", 307, 560, GREEN, 17, bold=True)
        label(f"{len(game.history)} successful calculations", 307, 510, MUTED, 16)
        label(game.objective["name"], 307, 455, TEXT, 25, width=690, bold=True)
        label(OBJECTIVE_COPY[game.objective["id"]], 307, 410, MUTED, 14, width=680)
        label(short(self.board.save_warning, 145) if self.board.save_warning else "Your game and card arrangement are saved.",
              302, 324, RED if self.board.save_warning else MUTED, 12, width=1050)
        self.draw_controls()


class Help(Modal):
    def __init__(self, board):
        super().__init__(board, (246, 138, 1188, 774))
        self.button(298, 191, 289, 48, "Back to the table", self.back, selected=True, size=15)

    def on_draw(self):
        self.background()
        label("How to use the card table", 298, 862, TEXT, 30, bold=True)
        sections = [
            ("Cards", "Drag cards to arrange them or reorder your hand. Scroll with a wheel, trackpad, or the bottom bar. Double-click, right-click, or press I to inspect. Remove card holds one retrievable card; replacing it permanently removes the previous card from play."),
            ("Operations", "Place matrices in A and B and an operation in the middle. Add and Multiply each allow 2 uses per turn; their buttons show uses left. Only taking a result spends a use. Each input uses a different physical card; one-input operations use only A."),
            ("Highlights", "Choose rows, columns, entries, or L/U below the operation. Click a matrix entry to select a single-entry target, or a row/column target in A and source in B. Hover a result entry to follow its inputs for addition or multiplication."),
            ("Result", "A result stays a preview until you drag it out or choose Take result. In manual mode, write integers or exact fractions on the result card. Tab moves between cells; Enter or Check verifies without playing. Taking a correct result consumes red inputs and any operation card; blue inputs stay."),
            ("Eight turns", "Every new qualifying matrix earns one point; the starting matrix and repeats earn none. Each new turn deals 3 operations and up to 3 red matrices. Unused cards stay; used cards can recycle. An untaken result earns nothing and consumes nothing."),
        ]
        for i, (title, body) in enumerate(sections):
            y = 790 - i * 106
            label(f"0{i + 1}", 298, y, BLUE, 15, bold=True)
            label(title, 348, y, TEXT, 17, bold=True)
            label(body, 348, y - 30, MUTED, 13, width=1007)
        self.draw_controls()


def main(mode="auto"):
    screen_width, screen_height = arcade.get_display_size()
    window = arcade.Window(WIDTH, HEIGHT, "GameTrix — Card table", resizable=False,
                           update_rate=1 / 30, draw_rate=1 / 30, vsync=True,
                           antialiasing=True, center_window=False)
    # Logical window dimensions avoid Arcade's Retina framebuffer centering bug.
    window.set_location(max(0, (screen_width - WIDTH) // 2), max(35, (screen_height - HEIGHT) // 2))
    window.show_view(Menu(mode))
    arcade.run()
