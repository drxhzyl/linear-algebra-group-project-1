# GameTrix in a browser

This experimental build runs the existing Python game with Pyodide 0.29.0,
Arcade 4.0.0.dev8, and pyglet 3.0.dev11. The desktop game continues to use its
separate Arcade 3 environment. The browser downloads Pyodide and Arcade on
first load, so startup can take a while and requires an internet connection.
Use a keyboard with a mouse or trackpad; touch input has not been implemented.

To build and serve it locally from the repository root:

```sh
python3 web/build.py
python3 -m http.server 8000 --directory web/dist
```

Open <http://localhost:8000/>. The build creates `web/dist/index.html`,
`boot.py`, and `game.zip`; `web/dist/` is not tracked. The archive contains the
game's Python modules, the expanded deck, and the card art and fonts, but not
local saves, PDF exports, or development files.

Automatic and student games save separately in the browser's local storage.
They survive reloads in the same browser and origin, but do not synchronize
with the desktop game or other browsers and can be deleted by clearing site
data. The game displays a save warning if browser storage is unavailable.

The browser bootstrap supplies its own draw interval, recreates pyglet's WebGL
buffer view after WebAssembly memory growth, fixes framebuffer dimensions, and
converts scaled browser pointer and wheel coordinates to the desktop table's
logical coordinates. These workarounds are tied to the pinned preview versions
and should be rechecked when upgrading Arcade or pyglet.

## Verification

Run `python3 -m unittest discover -s web -p 'test_build.py'` for the package
check. For the full browser check, install `playwright-core` in `web/` and use
a Chrome or Chromium executable. For example, on macOS, while the local server
is running:

```sh
npm install --prefix web --no-save playwright-core@1.65.0
GAMETRIX_CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' node web/browser_smoke.cjs
```

Set `GAMETRIX_WEB_URL` if the server uses a different address. The test uses a
fresh browser session and checks drawing, high-density scaling, mouse and
keyboard input, student-answer verification, saves, reload, and card removal.

## GitHub Pages

The Pages workflow builds this directory from the committed project source and
publishes `web/dist`. In the repository's **Settings → Pages**, select **GitHub
Actions** as the source, then run or rerun the `Deploy GameTrix to Pages`
workflow. The expected project URL is
`https://drxhzyl.github.io/linear-algebra-group-project-1/`.
