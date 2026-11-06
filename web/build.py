"""Build the static, browser-only GameTrix distribution."""

from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
DIST = WEB / "dist"


def build():
    DIST.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "boot.py"):
        shutil.copyfile(WEB / name, DIST / name)

    files = [ROOT / name for name in (
        "matrix.py", "card_art.py", "card_layout.py",
        "expansion_split/generated/deck.json",
    )]
    files.extend(sorted((ROOT / "digital").glob("*.py")))
    assets = ROOT / "digital/assets"
    files.extend(sorted(p for p in assets.iterdir()
                        if p.suffix.lower() in (".png", ".ttf")
                        or p.name in ("LICENSE_LIBERATION", "README.txt")))
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(path)
    with zipfile.ZipFile(DIST / "game.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
    print(f"Built {DIST} ({len(files)} game files)")


if __name__ == "__main__":
    build()
