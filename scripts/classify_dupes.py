import csv, re
from collections import defaultdict, Counter
path = "data/raw/math_subject_raw.csv"
with open(path, encoding="cp1252", newline="") as f:
    rows = list(csv.DictReader(f))

def split(desc):
    cluster, _, standard = desc.partition("Standard:")
    return cluster, standard

def loose(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

def core(s):
    s = re.sub(r"\[.*?\]", "", s, flags=re.S)        # drop bracketed scope notes
    s = re.sub(r"For example,.*", "", s, flags=re.S)  # drop the example and anything after it
    return loose(s)

groups = defaultdict(list)
for r in rows:
    groups[r["Standard Identifier"]].append(r)

buckets = defaultdict(list)
for k, rs in groups.items():
    if len(rs) < 2:
        continue
    descs = [r["Description"] for r in rs]
    if len({loose(split(d)[1]) for d in descs}) > 1:
        buckets["1 standard text differs"].append(k)
    elif len({loose(split(d)[0]) for d in descs}) > 1:
        buckets["2 cluster note differs"].append(k)
    elif len(set(descs)) > 1:
        buckets["3 punctuation/spacing only"].append(k)
    else:
        buckets["4 same text, course/grade only"].append(k)

for name in sorted(buckets):
    print(name, len(buckets[name]))
print("\nstandard text differs:", buckets["1 standard text differs"])