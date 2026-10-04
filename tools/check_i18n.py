"""Checks the translations of the hub (server/CLI messages and the web page).

Usage:   python tools/check_i18n.py          (from any folder; the project is the parent of tools/)
Exit code 0 = OK (warnings allowed), 1 = problems.

Python (vinted_hub/*.py, tools/*.py  <->  DE in vinted_hub/i18n.py):
  - every tr("...") text has a DE entry; no stale or duplicate DE keys
  - tr() only with a plain string literal (no f-string, no variable, no "a" + "b")
  - placeholders: the German text has exactly the {names} of the English one; every tr() call passes exactly the
    keyword arguments its text needs (no kwargs -> no placeholders, no braces)
  - WARNING for German-looking string literals outside tr()/DE in vinted_hub/*.py (maybe untranslated)
Web page (vinted_hub/web/js/**/*.js without vendor/  <->  the dictionaries js/i18n/de.*.js, merged in js/i18n.js):
  - every t("...") literal and both literals of tn(n, "...", "...") have an entry in exactly one dictionary
  - dictionaries: one '"English": "Deutsch",' per line (// comments allowed); no key twice (in one or two files),
    no empty translation, same {placeholders} on both sides, keys are English (no umlauts, „ ‚ » «),
    every de.*.js is imported in js/i18n.js; stale entries (no t()/tn() uses them) are problems
  - t( / tn( without double-quoted literals is a problem, unless the line contains "i18n-dynamic" or defines the
    function ("function t(", "export function tn(", ...); a text with {placeholders} needs values (t("…{x}…") alone)
  - no German left outside the dictionaries: umlauts/„ ‚ » « anywhere in the code (comments ignored), typical
    German words in strings and template literals (allowed: "Deutsch", the language's own name); umlauts in index.html
  - classic scripts with their own dictionary ("const FILE_HINT_DE = {" in js/file-hint.js) are checked against that
    dictionary only; their texts do not count for the module dictionaries
The messages are German like the other tools (they are read by Claude, not shown in the hub).
"""
from __future__ import annotations

import ast
import json
import re
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "vinted_hub"
I18N_PY = PKG / "i18n.py"
PY_FILES = sorted(PKG.glob("*.py")) + sorted((ROOT / "tools").glob("*.py"))
WEB = PKG / "web"
JS = WEB / "js"
DICT_DIR = JS / "i18n"
I18N_JS = JS / "i18n.js"

# ---------------------------------------------------------------- Python ----

# German-looking literals that are fine outside tr(): input values that are mapped, never shown
PY_ALLOWED_GERMAN = {
    "form.py": {"neu mit etikett", "neu ohne etikett", "sehr gut", "gut", "zufriedenstellend", "schwarz", "grau",
                "weiß", "weiss", "creme", "rot", "bordeaux", "rosa", "lila", "violett", "blau", "türkis", "grün",
                "gelb", "silber", "braun", "cognac", "mehrfarbig", "leder", "wildleder", "kunstleder", "gummi",
                "unbekannt", "unklar", "ohne marke", "keine marke", "vermutlich", "klein", "mittel", "groß", "gross"},
}
PY_GERMAN_HINT = re.compile(r"[äöüÄÖÜß„“]|\b(nicht|bitte|Bitte|Fehler|gefunden|Inserat|Zentrale|ausfüllen|"
                            r"läuft|schon|oder|und|der|die|das|ist|kein|keine|Fotos?|Größe|Zustand|Marke)\b")


def py_placeholders(text: str) -> set:
    return {name.split(".")[0].split("[")[0] for _, name, _, _ in string.Formatter().parse(text) if name}


def is_de_assign(node) -> bool:
    return isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DE" for t in node.targets)


def load_py_de(problems: list) -> dict:
    tree = ast.parse(I18N_PY.read_text(encoding="utf-8"))
    for node in tree.body:
        if is_de_assign(node) and isinstance(node.value, ast.Dict):
            de = {}
            for k, v in zip(node.value.keys, node.value.values):
                if not (isinstance(k, ast.Constant) and isinstance(k.value, str) and isinstance(v, ast.Constant)
                        and isinstance(v.value, str)):
                    problems.append(f"i18n.py:{getattr(k, 'lineno', '?')}: DE-Eintrag ist kein einfaches Text-Paar")
                    continue
                if k.value in de:
                    problems.append(f"i18n.py:{k.lineno}: DE hat den Schlüssel doppelt: {k.value!r}")
                de[k.value] = v.value
            return de
    problems.append("i18n.py: kein DE = {...} gefunden")
    return {}


def check_python(problems: list, warnings: list) -> str:
    de = load_py_de(problems)
    used = {}
    for path in PY_FILES:
        rel = path.relative_to(ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        in_tr, de_nodes, docstrings = set(), set(), set()
        for node in ast.walk(tree):
            if path == I18N_PY and is_de_assign(node):
                de_nodes |= {id(n) for n in ast.walk(node)}
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body \
                    and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                docstrings.add(id(node.body[0].value))
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
            if name != "tr" or (path == I18N_PY and not node.args):
                continue
            if not node.args or not (isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                got = ast.dump(node.args[0])[:60] if node.args else "nichts"
                problems.append(f"{rel}:{node.lineno}: tr() braucht ein einfaches Text-Literal, bekommt {got}")
                continue
            text = node.args[0].value
            in_tr.add(id(node.args[0]))
            used.setdefault(text, []).append(f"{rel}:{node.lineno}")
            kw = {k.arg for k in node.keywords}
            if None in kw:
                problems.append(f"{rel}:{node.lineno}: tr(**dict) kann nicht geprüft werden")
                continue
            need = py_placeholders(text)
            if kw and kw != need:
                problems.append(f"{rel}:{node.lineno}: tr({text!r}) übergibt {sorted(kw)}, der Text braucht {sorted(need)}")
            if not kw and need:
                problems.append(f"{rel}:{node.lineno}: tr({text!r}) hat Platzhalter, aber keine Keyword-Argumente")
            if not kw and ("{" in text or "}" in text):
                problems.append(f"{rel}:{node.lineno}: tr({text!r}) ohne Keyword-Argumente darf keine Klammern enthalten")
        if path.parent.name == "tools":
            continue  # tool messages are for Claude and stay German
        allowed = PY_ALLOWED_GERMAN.get(path.name, set())
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in in_tr
                    and id(node) not in de_nodes and id(node) not in docstrings
                    and node.value.strip().lower() not in allowed and PY_GERMAN_HINT.search(node.value)):
                warnings.append(f"{rel}:{node.lineno}: deutsch wirkender Text außerhalb von tr(): {node.value[:70]!r}")

    for text, where in sorted(used.items()):
        if text not in de:
            problems.append(f"{where[0]}: kein DE-Eintrag für {text!r}")
        elif py_placeholders(de[text]) != py_placeholders(text):
            problems.append(f"Platzhalter verschieden: {text!r} {sorted(py_placeholders(text))} <-> DE "
                            f"{sorted(py_placeholders(de[text]))}")
    for text in sorted(set(de) - set(used)):
        problems.append(f"i18n.py: veralteter DE-Eintrag (in keinem tr() benutzt): {text!r}")
    for value in de.values():
        names = py_placeholders(value)
        try:
            if names:
                value.format(**{n: "x" for n in names})
        except (ValueError, KeyError, IndexError) as e:
            problems.append(f"i18n.py: DE-Text lässt sich nicht formatieren: {value!r} ({e})")
        if not names and ("{" in value or "}" in value):
            problems.append(f"i18n.py: DE-Text mit losen Klammern: {value!r}")
    return f"Python: {len(used)} tr()-Texte in {len(PY_FILES)} Dateien, {len(de)} DE-Einträge"


# ------------------------------------------------------------------- Web ----

STR = r'"((?:[^"\\\n]|\\.)*)"'                       # a JS double-quoted string literal (group = content)
T_CALL = re.compile(r'(?<![\w$.])t\(\s*' + STR)
T_ANY = re.compile(r'(?<![\w$.])t\(')
TN_CALL = re.compile(r'(?<![\w$.])tn\(\s*[^"\n,()]+,\s*' + STR + r'\s*,\s*' + STR)   # literals may be on the next lines
TN_ANY = re.compile(r'(?<![\w$.])tn\(')
DEFINES = re.compile(r'^\s*(export\s+)?(async\s+)?function\s+tn?\s*\(')
JS_PLACEHOLDER = re.compile(r"\{(\w+)\}")
GERMAN_CHARS = re.compile(r"[äöüÄÖÜß„‚»«]")          # “ ” ’ are English typography too
GERMAN_WORDS = re.compile(r"\b(Inserate?n?|Preis(e|en)?|fehlt|bitte|Zentrale|Speichern|[Gg]espeichert|Abrufe?|Aufrufe|Favoriten|"
                          r"Zustand|Marke|Beschreibung|Freigeben|freigegeben|Einstellungen|Sprache|Fehler|nicht|und|oder|mit|"
                          r"noch|schon|Fotos?|Ordner|Neu laden|geladen|Auftrag|Statistik|Titelbild|Verkauft|Entwurf|"
                          r"Abbrechen|Kopieren|Deutsch|Englisch|Verlauf|gesamt|seit|letztem|Vorschlag|Mindestpreis)\b")
ALLOWED_GERMAN_WORDS = {"Deutsch"}    # the language switch names each language in its own language
CLASSIC_DICT = re.compile(r"^const (\w+_DE) = \{\s*$", re.M)
KEYWORDS_BEFORE_REGEX = {"return", "typeof", "case", "do", "else", "in", "of", "new", "delete", "void", "throw",
                         "instanceof", "yield", "await"}


def unescape(s: str) -> str:
    return json.loads('"' + s.replace("\\'", "'") + '"')


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan_js(src: str):
    """Small JS scanner. Returns (code, literals): `code` is the source with comments replaced by spaces (newlines
    kept, so offsets and line numbers stay right); `literals` are (kind, offset, text) for strings ('"', "'"),
    template literal text parts ("`") and regex literals ("/")."""
    out = list(src)
    literals = []
    i, n = 0, len(src)
    stack = []            # template nesting: brace depth of each open "${"
    depth = 0
    last = ""             # last significant character/word in code (decides "/" = regex or division)

    def blank(a, b):
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "

    def template(start):
        # src[start] == "`" or the "}" closing a ${...}: read text up to "`" or "${"
        j, text = start + 1, []
        while j < n:
            c = src[j]
            if c == "\\":
                text.append(src[j:j + 2])
                j += 2
                continue
            if c == "`":
                literals.append(("`", start + 1, "".join(text)))
                return j + 1, False
            if c == "$" and src[j + 1:j + 2] == "{":
                literals.append(("`", start + 1, "".join(text)))
                return j + 2, True
            text.append(c)
            j += 1
        literals.append(("`", start + 1, "".join(text)))
        return n, False

    while i < n:
        c = src[i]
        if c in " \t\r\n":
            i += 1
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
            continue
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            literals.append((c, i + 1, src[i + 1:j]))
            i, last = j + 1, "a"
            continue
        if c == "`":
            i, opened = template(i)
            if opened:
                stack.append(depth)
                depth = 0
                last = "("
            else:
                last = "a"
            continue
        if c == "{":
            depth += 1
            i, last = i + 1, "{"
            continue
        if c == "}":
            if stack and depth == 0:
                i, opened = template(i)
                if opened:
                    last = "("
                else:
                    depth = stack.pop()
                    last = "a"
                continue
            depth -= 1
            i, last = i + 1, "}"
            continue
        if c == "/":
            if last == "" or last in "(,=:[!&|?{};+-*%<>~^" or last in KEYWORDS_BEFORE_REGEX:
                j, in_class = i + 1, False
                while j < n and src[j] != "\n":
                    if src[j] == "\\":
                        j += 2
                        continue
                    if src[j] == "[":
                        in_class = True
                    elif src[j] == "]":
                        in_class = False
                    elif src[j] == "/" and not in_class:
                        break
                    j += 1
                literals.append(("/", i + 1, src[i + 1:j]))
                j += 1
                while j < n and (src[j].isalnum()):
                    j += 1
                i, last = j, "a"
                continue
            i, last = i + 1, "/"
            continue
        m = re.match(r"[A-Za-z_$][\w$]*", src[i:i + 64])
        if m:
            word = m.group(0)
            i += len(word)
            last = word if word in KEYWORDS_BEFORE_REGEX else "a"
            continue
        if c.isdigit():
            m = re.match(r"[\w.]+", src[i:i + 64])
            i += len(m.group(0))
            last = "a"
            continue
        last = c
        i += 1
    return "".join(out), literals


def parse_dict_block(text: str, start: int, rel: str, problems: list) -> tuple:
    """Entries of a dictionary block starting after the line at `start` (the "{" line) up to "};".
    Returns (entries {key: (value, line)}, end offset)."""
    end = text.find("\n};", start)
    if end < 0:
        problems.append(f"{rel}: Wörterbuch ohne abschließendes '}};'")
        return {}, len(text)
    entries = {}
    first_line = line_of(text, start)
    for k, line in enumerate(text[start:end].split("\n")):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped == "{" or stripped.endswith("= {"):
            continue
        m = re.fullmatch(STR + r"\s*:\s*" + STR + r",?(\s*//.*)?", stripped)
        no = first_line + k
        if not m:
            problems.append(f"{rel}:{no}: Eintrag nicht lesbar (ein '\"English\": \"Deutsch\",' pro Zeile): {stripped[:80]}")
            continue
        key, value = unescape(m.group(1)), unescape(m.group(2))
        if key in entries:
            problems.append(f"{rel}:{no}: Schlüssel doppelt in derselben Datei: {key!r}")
        entries[key] = (value, no)
        if not value.strip():
            problems.append(f"{rel}:{no}: leere Übersetzung für {key!r}")
        if set(JS_PLACEHOLDER.findall(key)) != set(JS_PLACEHOLDER.findall(value)):
            problems.append(f"{rel}:{no}: Platzhalter verschieden: {key!r} -> {value!r}")
        if GERMAN_CHARS.search(key):
            problems.append(f"{rel}:{no}: Quelltext (Schlüssel) ist nicht englisch: {key!r}")
    return entries, end + 3


def calls_in(code: str, src: str, rel: str, problems: list) -> list:
    """t()/tn() literals of one file: [(text, line)]. Problems for calls without literals and for texts with
    placeholders that get no values."""
    src_lines = src.split("\n")
    found, literal_at = [], set()
    for m in T_CALL.finditer(code):
        literal_at.add(m.start())
        text = unescape(m.group(1))
        found.append((text, line_of(code, m.start())))
        if JS_PLACEHOLDER.search(text) and code[m.end():].lstrip().startswith(")"):
            problems.append(f"{rel}:{line_of(code, m.start())}: t({text!r}) hat Platzhalter, bekommt aber keine Werte")
    for m in TN_CALL.finditer(code):
        literal_at.add(m.start())
        for g in (1, 2):
            text = unescape(m.group(g))
            found.append((text, line_of(code, m.start())))
            if set(JS_PLACEHOLDER.findall(text)) - {"n"} and code[m.end():].lstrip().startswith(")"):
                problems.append(f"{rel}:{line_of(code, m.start())}: tn(…, {text!r}) hat Platzhalter außer {{n}}, bekommt aber keine Werte")
    for pattern, what in ((T_ANY, "t() ohne Text-Literal in doppelten Anführungszeichen"),
                          (TN_ANY, "tn() ohne zwei Text-Literale in doppelten Anführungszeichen")):
        for m in pattern.finditer(code):
            if m.start() in literal_at:
                continue
            no = line_of(code, m.start())
            line = src_lines[no - 1]
            if "i18n-dynamic" in line or DEFINES.match(line):
                continue
            problems.append(f"{rel}:{no}: {what}: {line.strip()[:100]}")
    return found


def german_leftovers(code: str, literals: list, rel: str, problems: list, skip=(0, 0)) -> None:
    """Umlauts etc. anywhere in the code (comments are already blanked), German words in strings/templates.
    `skip`: offsets of a dictionary block in the same file."""
    for m in GERMAN_CHARS.finditer(code):
        if skip[0] <= m.start() < skip[1]:
            continue
        no = line_of(code, m.start())
        problems.append(f"{rel}:{no}: deutsche Zeichen außerhalb der Wörterbücher: {code.split(chr(10))[no - 1].strip()[:100]}")
    for kind, offset, text in literals:
        if kind == "/" or skip[0] <= offset < skip[1]:
            continue
        for wm in GERMAN_WORDS.finditer(text):
            if wm.group(1) not in ALLOWED_GERMAN_WORDS:
                problems.append(f"{rel}:{line_of(code, offset)}: deutsches Wort {wm.group(1)!r} in einem Text außerhalb "
                                f"der Wörterbücher: {text.strip()[:80]!r}")


def check_web(problems: list) -> str:
    # module dictionaries
    merged = {}   # key -> (value, rel, line)
    dict_files = sorted(DICT_DIR.glob("de.*.js"))
    i18n_src = I18N_JS.read_text(encoding="utf-8") if I18N_JS.exists() else ""
    for path in dict_files:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        m = re.search(r"^export default \{\s*$", text, re.M)
        if not m:
            problems.append(f"{rel}: kein 'export default {{' gefunden")
            continue
        if not re.search(r'from\s+"\./i18n/' + re.escape(path.name) + '"', i18n_src):
            problems.append(f"{rel}: wird in js/i18n.js nicht importiert (seine Texte würden fehlen)")
        entries, end = parse_dict_block(text, m.end(), rel, problems)
        if text[end:].strip():
            problems.append(f"{rel}: Text nach dem Wörterbuch: {text[end:].strip()[:60]!r}")
        for key, (value, no) in entries.items():
            if key in merged:
                problems.append(f"{rel}:{no}: Schlüssel steht schon in {merged[key][1]}:{merged[key][2]}: {key!r}")
                continue
            merged[key] = (value, rel, no)

    used = {}     # text -> first "file:line" (module code)
    files = sorted(p for p in JS.rglob("*.js") if DICT_DIR not in p.parents)
    classic_count = 0
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        src = path.read_text(encoding="utf-8")
        code, literals = scan_js(src)
        cm = CLASSIC_DICT.search(code)
        if cm:   # classic script with its own dictionary
            classic_count += 1
            own, end = parse_dict_block(code, cm.end(), rel, problems)
            own = {k: v for k, (v, _) in own.items()}
            masked = code[:cm.start()] + re.sub(r"[^\n]", " ", code[cm.start():end]) + code[end:]   # newlines kept
            calls = calls_in(masked, src, rel, problems)
            for text, no in calls:
                if text not in own:
                    problems.append(f"{rel}:{no}: kein Eintrag in {cm.group(1)} für {text!r}")
            for key in sorted(set(own) - {text for text, _ in calls}):
                problems.append(f"{rel}: veralteter Eintrag in {cm.group(1)}: {key!r}")
            german_leftovers(code, literals, rel, problems, skip=(cm.start(), end))
            continue
        for text, no in calls_in(code, src, rel, problems):
            used.setdefault(text, f"{rel}:{no}")
        german_leftovers(code, literals, rel, problems)

    for text in sorted(used):
        if text not in merged:
            problems.append(f"{used[text]}: kein Eintrag in js/i18n/de.*.js für {text!r}")
    for key in sorted(set(merged) - set(used)):
        problems.append(f"{merged[key][1]}:{merged[key][2]}: veralteter Eintrag (kein t()/tn() benutzt ihn): {key!r}")

    index = WEB / "index.html"
    if index.exists():
        html = index.read_text(encoding="utf-8")
        for m in GERMAN_CHARS.finditer(html):
            problems.append(f"web/index.html:{line_of(html, m.start())}: deutsches Zeichen: {html[max(0, m.start() - 30):m.start() + 30]!r}")
    return (f"Web: {len(used)} Texte in t()/tn() in {len(files)} Dateien ({classic_count} klassisches Skript mit eigenem "
            f"Wörterbuch), {len(merged)} Einträge in {len(dict_files)} Wörterbüchern")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")   # a pipe on Windows is cp1252: never crash on "→" etc.
    problems, warnings = [], []
    summary = [check_python(problems, warnings), check_web(problems)]
    for line in summary:
        print(line)
    for w in warnings:
        print("WARNUNG " + w)
    if problems:
        print(f"PROBLEME ({len(problems)}):")
        print("\n".join(" - " + p for p in problems))
        return 1
    print("OK: alle Texte übersetzt, keine veralteten Einträge, Platzhalter gleich, kein Deutsch außerhalb der Wörterbücher")
    return 0


if __name__ == "__main__":
    sys.exit(main())
