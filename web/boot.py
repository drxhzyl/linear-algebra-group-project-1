"""Browser entry point; the desktop game and its save files stay separate."""

import os
from pathlib import Path
import sys

import js

sys.path.insert(0, "/game")
SAVE_DIR = Path("/gametrix-browser-saves")
os.environ["GAMETRIX_SAVE_DIR"] = str(SAVE_DIR)
SAVE_NAMES = ("auto.json", "auto.previous.json", "student.json", "student.previous.json")
STORAGE_PREFIX = "gametrix.browser.v1:"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# Pyodide's ordinary filesystem is temporary. Restore the browser's last saved
# games before Menu checks for them, then mirror successful writes immediately.
try:
    for _name in SAVE_NAMES:
        _content = js.window.localStorage.getItem(STORAGE_PREFIX + _name)
        if _content is not None:
            (SAVE_DIR / _name).write_text(str(_content), encoding="utf-8")
except Exception:
    # The board reports storage failures when it next attempts to save.
    pass

import arcade
import pyglet
from digital import app
from pyglet.graphics.api.webgl.buffer import WebGLDataStore
from pyglet.libs.emscripten import PersistentBufferView
from pyglet.window.emscripten import EmscriptenWindow

app.SAVE_DIR = SAVE_DIR
_desktop_save = app.Board.save


def _browser_save(self):
    if not _desktop_save(self):
        return False
    try:
        for name in SAVE_NAMES:
            path = SAVE_DIR / name
            if path.exists():
                js.window.localStorage.setItem(STORAGE_PREFIX + name, path.read_text(encoding="utf-8"))
    except Exception:
        self.save_warning = "Browser storage is unavailable; this game cannot be saved."
        return False
    return True


app.Board.save = _browser_save

# Pyodide can grow its WebAssembly memory after pyglet has cached a zero-copy
# view. Growth detaches the old ArrayBuffer; recreate the view when needed.
def _live_buffer_view(self):
    view = self._view
    if view is None:
        raise RuntimeError("WebGL data store has been released.")
    if self.size and view.data.byteLength == 0:
        view.release()
        self._view = view = PersistentBufferView(self.get_memoryview())
    return view


WebGLDataStore.view = property(_live_buffer_view)

# Keep the framebuffer in logical coordinates even on high-density displays.
# Pyglet's browser backend otherwise resizes it to the CSS size times the
# device pixel ratio while Arcade keeps the viewport at 1680×1050.
def _fixed_canvas_size(self, width, height):
    self.canvas.width = self._width
    self.canvas.height = self._height
    self.canvas.style.width = f"{self._width}px"
    self.canvas.style.height = f"{self._height}px"


EmscriptenWindow.adjust_scale = _fixed_canvas_size

# The web backend emits framebuffer-scaled coordinates and raw browser wheel
# events. Convert them to the 1680×1050 logical table after CSS scaling.
window = arcade.Window(app.WIDTH, app.HEIGHT, "GameTrix", resizable=False,
                       update_rate=1 / 30, draw_rate=1 / 30)
_dispatch = window.dispatch_event


def _browser_dispatch(name, *args):
    if name in ("on_mouse_press", "on_mouse_release", "on_mouse_drag", "on_mouse_motion") and len(args) >= 2:
        rect = window.canvas.getBoundingClientRect()
        if rect.width and rect.height:
            args = list(args)
            args[0] = args[0] / window.scale * app.WIDTH / rect.width
            args[1] = app.HEIGHT - ((window.canvas.height - args[1]) / window.scale
                                    * app.HEIGHT / rect.height)
            if name in ("on_mouse_drag", "on_mouse_motion") and len(args) >= 4:
                args[2] *= app.WIDTH / rect.width
                args[3] *= -app.HEIGHT / rect.height
    elif name == "on_mouse_scroll" and len(args) >= 4:
        rect = window.canvas.getBoundingClientRect()
        if rect.width and rect.height:
            args = list(args)
            args[0] = (args[0] - rect.left) * app.WIDTH / rect.width
            args[1] = app.HEIGHT - (args[1] - rect.top) * app.HEIGHT / rect.height
            args[2], args[3] = -args[2] / 100, -args[3] / 100
    return _dispatch(name, *args)


window.dispatch_event = _browser_dispatch
window.show_view(app.Menu())
# Arcade 4.0.0.dev8's arcade.run() passes interval=None, which disables pyglet
# 3.0.dev11's browser draw source. Supply a draw interval explicitly here.
pyglet.app.run(1 / 60)


def _report_loop_failure(task):
    try:
        task.result()
    except Exception:
        import traceback
        global _browser_loop_error
        _browser_loop_error = traceback.format_exc()
        js.window.gameFailed(_browser_loop_error)


_browser_loop_error = ""
_browser_loop_task = pyglet.app.event_loop._run_task
_browser_loop_task.add_done_callback(_report_loop_failure)
