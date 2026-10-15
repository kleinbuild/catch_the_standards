import csv, re

#Alpha version 10/15/2026 for test run proving concept

path = "data/raw/math_subject_raw.csv"   # adjust to your actual filename
with open(path, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))
print(len(rows), "rows")
pattern = re.compile(r"equation|expression|fraction|multipl|ratio|square root|cube root", re.I)
for r in rows:
    if "Geometry" in (r["Domain"], r["Conceptual Category"]) or r["Domain"] == "Measurement and Data":
        text = r["Description"].split("Standard:", 1)[-1]   # skip the cluster text
        hits = sorted({m.lower() for m in pattern.findall(text)})
        if hits:
            print(r["Standard Identifier"], hits)