"""LaTeX/TikZ artwork for the physical cards, compiled to offline SVG assets."""

from pathlib import Path
import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "design" / "formula_cache.json"

PREAMBLE = r"""\documentclass[tikz,border=3pt,multi=tikzpicture]{standalone}
\usepackage{amsmath,amssymb,lmodern}
\usetikzlibrary{arrows.meta,positioning,calc}
\definecolor{Ink}{HTML}{182332}
\definecolor{Blue}{HTML}{245CFF}
\definecolor{Hot}{HTML}{E50078}
\definecolor{Operand}{HTML}{7953C8}
\definecolor{Green}{HTML}{009C73}
\definecolor{Mute}{HTML}{8A96AA}
\newcommand{\sq}{\textcolor{Mute}{\square}}
\newcommand{\focus}[1]{\begingroup\setlength{\fboxsep}{2pt}\setlength{\fboxrule}{0.85pt}\fcolorbox{Hot}{Hot!5}{$\displaystyle #1$}\endgroup}
\tikzset{every node/.style={text=Ink,font=\normalsize},
 box/.style={draw=Blue,line width=.8pt,rounded corners=4pt,inner sep=4pt,fill=Blue!3},
 result/.style={box,draw=Green,fill=Green!3},
 operand/.style={box,draw=Operand,fill=Operand!3},
 lab/.style={font=\sffamily\small,text=Ink!65},
 arrow/.style={-{Stealth[length=4pt]},line width=.9pt,draw=Ink!70}}
\begin{document}
"""


def mat(rows):
    return (r"\begin{bmatrix}" + r"\\".join(" & ".join(row) for row in rows)
            + r"\end{bmatrix}")


def frame(name, x, y, formula, style="box"):
    return rf"\node[{style}] ({name}) at ({x},{y}) {{$ {formula} $}};" + "\n"


def label(x, y, text):
    return rf"\node[lab] at ({x},{y}) {{{text}}};" + "\n"


def picture(body):
    return "\\begin{tikzpicture}\n" + body + "\\end{tikzpicture}\n"


def pair(left, right, formula="", labels=("INPUT", "RESULT")):
    body = frame("a", -1.65, 0, left) + frame("b", 1.65, 0, right, "result")
    body += r"\draw[arrow] (a.east) -- (b.west);" + "\n"
    body += label(-1.65, 1.03, r"$A$") + label(1.65, 1.03, r"$A'$")
    if formula:
        body += rf"\node at (0,-1.2) {{$ {formula} $}};" + "\n"
    return picture(body)


def entry(value):
    return mat([[r"\sq", r"\sq", r"\sq"],
                [r"\sq", r"\focus{" + value + "}", r"\sq"],
                [r"\sq", r"\sq", r"\sq"]])


def operation_art(code):
    if code in ("entry_plus", "entry_minus", "entry_zero", "entry_tweak"):
        out = {"entry_plus": "x+1", "entry_minus": "x-1", "entry_zero": "0", "entry_tweak": r"x\pm1"}[code]
        return pair(entry("x"), entry(out), r"a'_{ij}=" + out)
    if code in ("add", "subtract"):
        sign = "+" if code == "add" else "-"
        a = mat([[r"\focus{a_{ij}}", r"\cdots"], [r"\vdots", r"\ddots"]])
        b = mat([[r"\focus{b_{ij}}", r"\cdots"], [r"\vdots", r"\ddots"]])
        c = mat([[rf"\focus{{a_{{ij}}{sign}b_{{ij}}}}", r"\cdots"], [r"\vdots", r"\ddots"]])
        body = frame("a", -1.2, .8, a) + frame("b", 1.2, .8, b, "operand")
        body += rf"\node at (0,.8) {{$ {sign} $}};" + "\n"
        body += label(-1.2, 1.65, r"$A$") + label(1.2, 1.65, r"$B$")
        body += frame("c", 0, -1.12, c, "result")
        body += r"\draw[arrow] (0,-.04) -- (c.north);" + "\n"
        body += label(0, -2, rf"$A'=A{sign}B$")
        return picture(body)
    if code == "multiply":
        a = mat([[r"\color{Hot}a_{i1}", r"\color{Hot}\cdots", r"\color{Hot}a_{in}"],
                 [r"\vdots", r"\ddots", r"\vdots"]])
        b = mat([[r"\color{Hot}b_{1j}", r"\cdots"], [r"\color{Hot}\vdots", r"\ddots"],
                 [r"\color{Hot}b_{nj}", r"\cdots"]])
        body = frame("a", -1.22, .25, a) + frame("b", 1.36, .25, b, "operand")
        body += label(-1.22, 1.28, r"$A$") + label(1.36, 1.28, r"$B$")
        body += r"\node at (0,-1.22) {$\displaystyle c_{ij}=\sum_{k=1}^{n} a_{ik}b_{kj}$};" + "\n"
        body += label(0, -1.93, r"$m\!\times\!n\quad\cdot\quad n\!\times\!p\quad\longrightarrow\quad m\!\times\!p$")
        return picture(body)
    if code in ("shift_plus", "shift_minus", "negate", "double"):
        a = mat([["a", "b"], ["c", "d"]])
        suffix = "+1" if code == "shift_plus" else "-1"
        values = [["a", "b"], ["c", "d"]]
        if code in ("shift_plus", "shift_minus"):
            values = [[x + suffix for x in row] for row in values]
            formula = "A'=A" + suffix[0] + "J_{m,n}"
        else:
            prefix = "-" if code == "negate" else "2"
            values = [[prefix + x for x in row] for row in values]
            formula = "A'=" + prefix + "A"
        b = mat([[r"\color{Hot}" + x for x in row] for row in values])
        return pair(a, b, formula, ("EVERY ENTRY", "EVERY ENTRY"))
    if code == "transpose":
        a = mat([[r"\color{Blue}a", r"\color{Blue}b"], [r"\color{Hot}c", r"\color{Hot}d"], ["e", "f"]])
        b = mat([[r"\color{Blue}a", r"\color{Hot}c", "e"], [r"\color{Blue}b", r"\color{Hot}d", "f"]])
        return pair(a, b, r"(A^{\mathsf T})_{ji}=a_{ij}", ("ROWS", "BECOME COLUMNS"))
    if code == "swap":
        a = mat([[r"\color{Blue}u", r"\color{Blue}v"], [r"\color{Hot}x", r"\color{Hot}y"], [r"\sq", r"\sq"]])
        b = mat([[r"\color{Hot}x", r"\color{Hot}y"], [r"\color{Blue}u", r"\color{Blue}v"], [r"\sq", r"\sq"]])
        return pair(a, b, r"r_i\longleftrightarrow r_j", ("TWO ROWS", "EXCHANGE PLACES"))
    if code in ("add_vector", "replace_vector", "append_vector"):
        a = mat([[r"\sq", r"\sq", r"\sq"], ["a", "b", "c"]])
        vector = mat([[r"\color{Operand}u", r"\color{Operand}v", r"\color{Operand}w"]])
        changed = [r"\color{Hot}" + x for x in (["a+u", "b+v", "c+w"] if code == "add_vector" else ["u", "v", "w"])]
        rows = [[r"\sq", r"\sq", r"\sq"]]
        if code == "append_vector":
            rows += [["a", "b", "c"]]
        rows += [changed]
        body = frame("a", -1.2, .8, a) + frame("v", 1.25, .8, vector, "operand")
        body += label(-1.2, 1.65, r"$A$") + label(1.25, 1.65, r"$r_B$")
        body += frame("b", 0, -1.3, mat(rows), "result")
        body += r"\draw[arrow] (0,-.05) -- (b.north);" + "\n"
        body += label(0, -2.32, r"$A'$")
        return picture(body)
    if code == "combine_vectors":
        a = mat([[r"\color{Blue}u", r"\color{Blue}v"], [r"\color{Hot}a", r"\color{Hot}b"], [r"\sq", r"\sq"]])
        b = mat([[r"\color{Blue}u", r"\color{Blue}v"], [r"\color{Hot}a\pm u", r"\color{Hot}b\pm v"], [r"\sq", r"\sq"]])
        return pair(a, b, r"r_j'=r_j\pm r_i,\qquad i\ne j", ("SOURCE + TARGET", "SOURCE STAYS"))
    if code == "inverse":
        a = mat([[r"a_{11}", r"\cdots"], [r"\vdots", r"\ddots"]])
        body = frame("a", -1.2, .2, a) + frame("b", 1.2, .2, r"A^{-1}", "result")
        body += r"\draw[arrow] (a.east) -- (b.west);" + "\n"
        body += r"\node at (0,-1.08) {$AA^{-1}=I$};" + "\n"
        body += label(0, -1.75, r"$\det(A)\ne0$")
        return picture(body)
    if code == "lu":
        l = mat([["1", "0", "0"], [r"\ell_{21}", "1", "0"], [r"\ell_{31}", r"\ell_{32}", "1"]])
        u = mat([[r"u_{11}", r"u_{12}", r"u_{13}"], ["0", r"u_{22}", r"u_{23}"], ["0", "0", r"u_{33}"]])
        body = r"\node at (0,1.35) {$A=LU$};" + "\n"
        body += frame("l", -1.4, 0, l) + frame("u", 1.4, 0, u, "result")
        body += label(-1.4, -1.2, r"$L$") + label(1.4, -1.2, r"$U$")
        return picture(body)
    raise ValueError(f"No illustration for operation {code}")


OBJECTIVE_FORMULAS = {
    "C01": r"A^{\mathsf T}=A\qquad\det(A)\ne0",
    "C02+": r"A=I_n", "C02-": r"A=-I_n",
    "C03": r"A=\operatorname{diag}(d_1,\ldots,d_n)",
    "C04": r"A\mathbf{1}=\mathbf{1}\qquad A^{\mathsf T}\mathbf{1}=\mathbf{1}",
    "C05": r"A^{\mathsf T}=-A\qquad A\ne0",
    "C06": r"A^2=I_n", "C07": r"\det(A)=1",
    "C08": r"A^2=A\qquad\operatorname{rank}(A)=2",
    "C09": r"A^3=0\qquad A^2\ne0", "C10": r"A^3=I_n",
    "C11": r"\begin{gathered}A^{\mathsf T}A=D\\D=\operatorname{diag}(d_1,\ldots,d_n),\quad d_i>0\end{gathered}",
    "C12": r"\begin{gathered}AA^{\mathsf T}=D\\D=\operatorname{diag}(d_1,\ldots,d_m),\quad d_i>0\end{gathered}",
    "C13": r"A\mathbf{1}=n\mathbf{1}\qquad A^{\mathsf T}\mathbf{1}=m\mathbf{1}",
    "C14": r"\begin{gathered}A\mathbf{1}=0\\AA^{\mathsf T}=\operatorname{diag}(d_i),\quad d_i>0\end{gathered}",
}


def scalar(value):
    if "/" in str(value):
        a, b = str(value).split("/")
        return rf"\frac{{{int(a)}}}{{{int(b)}}}"
    return str(int(value))


def matrix_art(A):
    return picture(r"\node at (0,0) {$\displaystyle " + mat([[scalar(x) for x in row] for row in A]) + "$};\n")


def objective_art(card):
    return picture(r"\node at (0,0) {$\displaystyle " + OBJECTIVE_FORMULAS[card["id"]] + "$};\n")


def source_key(source):
    return hashlib.sha256(("pdflatex-pdftocairo-v1\n" + PREAMBLE + source).encode()).hexdigest()


def load_cache():
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def svg_image(source, alt, cache):
    import html
    key = source_key(source)
    if key not in cache:
        raise ValueError("Missing LaTeX artwork. Run python3 render_cards.py first.")
    encoded = base64.b64encode(cache[key].encode()).decode()
    return f'<img class="math-art" src="data:image/svg+xml;base64,{encoded}" alt="{html.escape(alt, quote=True)}">'


def compile_art(sources):
    """Compile only missing art; each standalone TikZ picture becomes one SVG."""
    unique = dict((source_key(s), s) for s in sources)
    cache = load_cache()
    missing = [(key, src) for key, src in unique.items() if key not in cache]
    CACHE.parent.mkdir(exist_ok=True)
    # Keep the complete reproducible LaTeX source, not auxiliary build files.
    (CACHE.parent / "illustrations.tex").write_text(PREAMBLE + "".join(unique.values()) + "\\end{document}\n")
    if missing:
        cairo = os.environ.get("GAMETRIX_PDFTOCAIRO") or shutil.which("pdftocairo")
        if not cairo:
            bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin/pdftocairo"
            if bundled.is_file():
                cairo = str(bundled)
        if not shutil.which("pdflatex") or not cairo:
            raise RuntimeError("pdflatex and pdftocairo are required to build artwork; existing HTML remains usable offline.")
        with tempfile.TemporaryDirectory(prefix=".tex-build-", dir=CACHE.parent) as tmp:
            path = Path(tmp)
            (path / "art.tex").write_text(PREAMBLE + "".join(s for _, s in missing) + "\\end{document}\n")
            run = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape", "art.tex"],
                                 cwd=path, capture_output=True, text=True)
            if run.returncode:
                raise RuntimeError((run.stdout + run.stderr)[-7000:])
            for i in range(1, len(missing) + 1):
                run = subprocess.run([cairo, "-svg", "-f", str(i), "-l", str(i), "art.pdf", f"art-{i}.svg"],
                                     cwd=path, capture_output=True, text=True)
                if run.returncode:
                    raise RuntimeError((run.stdout + run.stderr)[-2000:])
            rendered = sorted(path.glob("art-*.svg"), key=lambda p: int(p.stem.split("-")[-1]))
            if len(rendered) != len(missing):
                raise RuntimeError(f"Expected {len(missing)} LaTeX pages, found {len(rendered)} SVG files")
            for (key, _), output in zip(missing, rendered):
                svg = output.read_text()
                svg = svg[svg.index("<svg"):]
                cache[key] = svg
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")))
    return cache, len(missing)
