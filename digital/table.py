"""Physical card placement, independent of game rules and drawing code."""

from collections import OrderedDict
import math
import random


class TableLayout:
    """Keep each live card in one hand, on the table, or in an action slot.

    Table insertion order is drawing order, with the final card on top.
    Coordinates are unrestricted finite numbers; the interface sets bounds.
    """

    ACTION_SLOTS = ("A", "operation", "B")
    SLOT_NAMES = (*ACTION_SLOTS, "remove")

    def __init__(self, game):
        self.hand: list[str] = []
        self.table: OrderedDict[str, tuple[float, float]] = OrderedDict()
        self.slots: dict[str, str | None] = dict.fromkeys(self.SLOT_NAMES)
        self._cards = {}
        self.sync(game)

    def sync(self, game):
        """Remove consumed cards and deal unseen cards into the mixed hand."""
        self._cards = {card["id"]: card for card in game.operations}
        self._cards.update((card.id, card) for card in game.matrices)
        self.hand[:] = [card_id for card_id in self.hand if card_id in self._cards]
        for card_id in list(self.table):
            if card_id not in self._cards:
                del self.table[card_id]
        for slot, card_id in self.slots.items():
            if card_id not in self._cards:
                self.slots[slot] = None
        placed = set(self.hand) | self.table.keys() | set(self.slots.values())
        new_cards = [card_id for card_id in self._cards if card_id not in placed]
        random.Random(f"{game.seed}:{game.turn}:layout").shuffle(new_cards)
        self.hand.extend(new_cards)

    def card(self, card_id):
        """Return the live operation dictionary or MatrixCard itself."""
        if not isinstance(card_id, str) or card_id not in self._cards:
            raise ValueError("Choose a live card.")
        return self._cards[card_id]

    def kind(self, card_id):
        card = self.card(card_id)
        return "operation" if isinstance(card, dict) else card.color

    def location(self, card_id):
        self.card(card_id)
        if card_id in self.hand:
            return "hand"
        if card_id in self.table:
            return "table"
        return next(slot for slot, occupant in self.slots.items() if occupant == card_id)

    def _detach(self, card_id):
        self.hand[:] = [other for other in self.hand if other != card_id]
        self.table.pop(card_id, None)
        for slot, occupant in self.slots.items():
            if occupant == card_id:
                self.slots[slot] = None

    def move_to_hand(self, card_id):
        self.card(card_id)
        self._detach(card_id)
        self.hand.append(card_id)

    @staticmethod
    def _coordinates(x, y):
        try:
            valid = all(type(value) in (int, float) and math.isfinite(value)
                        for value in (x, y))
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError("Table coordinates must be finite numbers.")
        return x, y

    def move_to_table(self, card_id, x, y):
        self.card(card_id)
        position = self._coordinates(x, y)
        self._detach(card_id)
        self.table[card_id] = position

    def _validate_slot(self, card_id, slot):
        if not isinstance(slot, str) or slot not in self.slots:
            raise ValueError("Choose slot A, operation, B, or remove.")
        kind = self.kind(card_id)
        if slot != "remove" and (slot == "operation") != (kind == "operation"):
            raise ValueError("Operation slots need operations; A and B need matrices.")

    def place_slot(self, card_id, slot):
        self._validate_slot(card_id, slot)
        previous = self.slots[slot]
        if previous == card_id:
            return
        if slot == "remove" and previous is not None:
            raise ValueError("Remove the previous card before replacing it.")
        self._detach(card_id)
        if previous is not None:
            self.move_to_hand(previous)
        self.slots[slot] = card_id

    def bring_to_front(self, card_id):
        self.card(card_id)
        if card_id not in self.table:
            raise ValueError("The card must be on the table.")
        self.table.move_to_end(card_id)

    def to_dict(self):
        """Return a detached JSON-safe snapshot, including table stacking order."""
        return {"hand": list(self.hand),
                "table": {card_id: list(position) for card_id, position in self.table.items()},
                "slots": dict(self.slots)}

    @classmethod
    def from_dict(cls, game, data):
        """Restore validated placements, putting any omitted live cards in hand."""
        layout = cls(game)
        if (not isinstance(data, dict) or not isinstance(data.get("hand"), list)
                or not isinstance(data.get("table"), dict)
                or not isinstance(data.get("slots"), dict)
                or set(data["slots"]) not in (set(cls.ACTION_SLOTS), set(cls.SLOT_NAMES))):
            raise ValueError("Invalid table layout zones.")
        seen = set()

        def claim(card_id):
            layout.card(card_id)
            if card_id in seen:
                raise ValueError("A physical card can appear in only one place.")
            seen.add(card_id)
            return card_id

        hand = [claim(card_id) for card_id in data["hand"]]
        table = OrderedDict()
        for card_id, position in data["table"].items():
            claim(card_id)
            if not isinstance(position, (list, tuple)) or len(position) != 2:
                raise ValueError("Each table card needs two coordinates.")
            table[card_id] = layout._coordinates(*position)
        slots = dict.fromkeys(cls.SLOT_NAMES)
        for slot in cls.SLOT_NAMES:
            card_id = data["slots"].get(slot)
            if card_id is not None:
                claim(card_id)
                layout._validate_slot(card_id, slot)
                slots[slot] = card_id
        hand.extend(card_id for card_id in layout.hand if card_id not in seen)
        layout.hand, layout.table, layout.slots = hand, table, slots
        return layout
