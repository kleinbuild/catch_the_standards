import csv, re

#Alpha version 10/15/2026 for test run proving concept

path = "/home/jamesk/Documents/myApps/catch_the_standards/data/raw/math_subject_raw.csv"   # adjust to your actual filename
with open(path, encoding="cp1252", newline="") as f:
    rows = list(csv.DictReader(f))
print(len(rows), "rows")
pattern = re.compile(r"\b(equations?|expressions?|fractions?|multiply|multiplying|multiplication|ratios?|square roots?|cube roots?)\b", re.I)
for r in rows:
    if "Geometry" in (r["Domain"], r["Conceptual Category"]) or r["Domain"] == "Measurement and Data":
        text = r["Description"].split("Standard:", 1)[-1]   # skip the cluster text
        hits = sorted({m.lower() for m in pattern.findall(text)})
        if hits:
            print(r["Standard Identifier"], r["Discipline"], r["Conceptual Category"], hits)

from collections import defaultdict
groups = defaultdict(list)
for r in rows:
    groups[r["Standard Identifier"]].append(r)
print(len(groups), "unique identifiers;", sum(len(v) > 1 for v in groups.values()), "appear more than once")
for k, rs in groups.items():
    if len(rs) > 1:
        differ = [c for c in rs[0] if c != "Discipline" and len({x[c] for x in rs}) > 1]
        if differ:
            print("differs:", k, differ)