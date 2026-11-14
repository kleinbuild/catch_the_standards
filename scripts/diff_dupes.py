import csv, re, difflib
from collections import defaultdict
path = "data/raw/math_subject_raw.csv"
with open(path, encoding="cp1252", newline="") as f:
    rows = list(csv.DictReader(f))

ids = ['A-CED.3', 'A-CED.4', 'A-REI.3', 'A-REI.7', 'A-SSE.1.b', 'A-SSE.2', 'F-BF.1.b',
       'F-BF.4.a', 'F-IF.5', 'F-IF.9', 'F-LE.5', 'G-GPE.4', 'N-CN.8', 'S-CP.5', 'Calculus.16.0']

def sections(desc):
    _, _, rest = desc.partition("Standard:")
    standard, _, footnote = rest.partition("Footnote:")
    return standard.strip(), footnote.strip()

def loose(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

groups = defaultdict(list)
for r in rows:
    groups[r["Standard Identifier"]].append(r)

for k in ids:
    base = groups[k][0]
    b_std, b_fn = sections(base["Description"])
    for r in groups[k][1:]:
        std, fn = sections(r["Description"])
        where = f"{k}: {base['Discipline']} vs {r['Discipline']}"
        if loose(std) != loose(b_std):
            changes = [w for w in difflib.ndiff(b_std.split(), std.split()) if w[0] in "+-"]
            print(where, "| standard:", " ".join(changes[:40]))
        if loose(fn) != loose(b_fn):
            print(where, "| footnote differs")