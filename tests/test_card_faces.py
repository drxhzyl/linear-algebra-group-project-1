"""Cell interaction and hidden-result rendering match the printed matrix face."""

import unittest
from unittest.mock import patch

from PIL import ImageChops

from digital import card_faces as faces


class CardFaceTests(unittest.TestCase):
    def test_cell_bounds_match_print_centers_at_small_card_sizes(self):
        for rows, cols in ((2, 2), (2, 3), (3, 2), (3, 3), (4, 4)):
            for width in (170, 200, 240):
                height = width * 88 / 63
                rect = (17, 29, width, height)
                cells = faces.matrix_cell_rects(rows, cols, *rect)
                cw = min(135, 461 / cols)
                ch = min(125, 478 / rows)
                for row in range(rows):
                    for col in range(cols):
                        x, y, w, h = cells[row][col]
                        # Existing printed matrix is centered at (315, 555).
                        print_x = 315 + (col + .5 - cols / 2) * cw
                        print_y = 555 + (row + .5 - rows / 2) * ch
                        self.assertAlmostEqual(x + w / 2, 17 + print_x * width / 630)
                        self.assertAlmostEqual(y + h / 2, 29 + (880 - print_y) * height / 880)
                        self.assertEqual(faces.matrix_cell_at(rows, cols, rect, x + w / 2, y + h / 2), (row, col))
                self.assertIsNone(faces.matrix_cell_at(rows, cols, rect, 17, 29))

    def test_blank_faces_never_format_hidden_entries(self):
        card = {"id": "G01", "matrix": [[object(), object()], [object(), object()]]}
        blank = faces.render_card_image(card, "blue", blank=True)
        other = faces.render_card_image({"id": "G01", "matrix": [[999, -412], ["3/7", 5]]}, "blue", blank=True)
        self.assertEqual(blank.tobytes(), other.tobytes())
        for row in faces.matrix_cell_rects(2, 2, 0, 0, 630, 880):
            for x, y, w, h in row:
                crop = blank.crop((int(x + 6), int(880 - y - h + 6), int(x + w - 6), int(880 - y - 6)))
                self.assertEqual(crop.getextrema(), ((255, 255),) * 4)

    def test_highlight_changes_only_selected_cell_and_preserves_cached_face(self):
        card = {"id": "R01", "matrix": [[1, 2], [3, 4]]}
        plain = faces.render_card_image(card, "red")
        highlighted = faces.render_card_image(card, "red", highlights={(1, 0): (35, 160, 245, 65)})
        # Compare RGB: opaque RGBA images have no alpha-channel difference.
        bounds = ImageChops.difference(plain.convert("RGB"), highlighted.convert("RGB")).getbbox()
        self.assertIsNotNone(bounds)
        x, y, w, h = faces.matrix_cell_rects(2, 2, 0, 0, 630, 880)[1][0]
        self.assertGreaterEqual(bounds[0], x)
        self.assertGreaterEqual(bounds[1], 880 - y - h)
        self.assertLessEqual(bounds[2], x + w)
        self.assertLessEqual(bounds[3], 880 - y)
        self.assertEqual(plain.tobytes(), faces.render_card_image(card, "red").tobytes())

    def test_draw_card_forwards_blank_and_highlights(self):
        card = {"id": "G01", "matrix": [[None, None], [None, None]]}
        tints = {(0, 1): (22, 160, 220, 60)}
        with patch.object(faces.arcade, "draw_texture_rect"), patch.object(faces, "_shadow"), patch.object(faces, "get_card_texture") as texture:
            faces.draw_card(card, "blue", 10, 20, 200, 280, scale=1.5, blank=True, highlights=tints)
        texture.assert_called_once_with(card, "blue", blank=True, highlights=tints)


if __name__ == "__main__":
    unittest.main()
