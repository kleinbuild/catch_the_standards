import csv, sys
path = "data/raw/math_subject_raw.csv"   # run from project root
with open(path, encoding="cp1252", newline="") as f:
    rows = list(csv.DictReader(f))
for ident in sys.argv[1:]:
    for r in rows:
        if r["Standard Identifier"] == ident:
            print(f"--- {ident} | {r['Discipline']} | grades {r['Grade Range']} (min {r['Min Grade']}, max {r['Max Grade']})")
            print(r["Description"], "\n")