#!/usr/bin/env python3
"""
match_csv_to_records.py - pair each row of a subject's dl=1 CSV with exactly one
scraped HTML record (from scrape_cacs_records.py). If every row pairs one-to-one,
the scrape holds everything the CSV does, and every CSV row gets a CDE record ID.

    python scripts/match_csv_to_records.py data/raw/<the math CSV> data/raw/math_records_2026-10-16.csv

How rows are paired:
  key   identifier, plus course (Discipline) when both files have that column.
  text  all text sections joined, headings like "Cluster:" removed, whitespace
        collapsed. Before comparing, the scraped text is converted the way CDE's
        export did it: any character cp1252 lacks becomes "?". So the minus sign,
        not-equal, square root, and approximately-equal turn into "?" on both sides.
Three passes, strictest first:
  exact    same text after the steps above
  loose    also treats every dash and "?" as equal, straight and curly quotes as
           equal, and ignores spaces (catches "context.*" vs "context. *")
  partial  one text contains the other (e.g. one file includes a footnote)

Writes cacs_compare/<subject>_csv_to_records.csv: one row per CSV row, with the
record_id it matched (blank if none) and which pass matched it.
"""
import argparse
import csv
import io
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HEADING = re.compile(r"(?m)^[ \t]*[A-Z][A-Za-z ]{0,40}:[ \t]*$")
LOOSE = str.maketrans({**{c: "~" for c in "-\u2010\u2011\u2012\u2013\u2014\u2212?"},
                       "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})


def decode(raw):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def read_csv(path):
    rows = list(csv.DictReader(io.StringIO(decode(Path(path).read_bytes()))))
    if not rows:
        sys.exit(f"{path}: no rows")
    return rows, list(rows[0].keys())


def like_cde_export(s):
    """What CDE's cp1252 export does to characters it can't encode."""
    return s.encode("cp1252", errors="replace").decode("cp1252")


def strict(s):
    s = HEADING.sub(" ", (s or "").replace("\r\n", "\n"))
    return " ".join(s.split())


def loose(s):
    return strict(s).translate(LOOSE).replace(" ", "")


def dashes(s):
    return re.sub(r"[\u2013\u2014\u2212]", "-", (s or "").strip())


def pick(cols, *names):
    for n in names:
        for c in cols:
            if c and c.strip().lower() == n.lower():
                return c
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv_file", help="the dl=1 download")
    ap.add_argument("records_file", help="output of scrape_cacs_records.py")
    ap.add_argument("--text-col", help="CSV column holding the standard text, if auto-detect fails")
    ap.add_argument("--out", default="cacs_compare")
    args = ap.parse_args()

    csv_rows, csv_cols = read_csv(args.csv_file)
    recs, rec_cols = read_csv(args.records_file)
    print(f"CSV columns:     {csv_cols}")
    print(f"scraped columns: {rec_cols}\n")

    csv_id = next((c for c in csv_cols if c and "identifier" in c.lower()), None)
    csv_text = args.text_col or pick(csv_cols, "Description", "Standard", "Text")
    if not csv_id or not csv_text:
        sys.exit("Can't find the identifier or text column in the CSV. Use --text-col.")
    csv_course = pick(csv_cols, "Discipline")
    use_course = bool(csv_course) and "Discipline" in rec_cols
    csv_grade = pick(csv_cols, "Grade Range", "Grade")
    text_cols = [c for c in rec_cols if c.startswith("text_")]
    print(f"pairing on: {csv_id}" + (f" + {csv_course}" if use_course else "")
          + f"; CSV text column: {csv_text}; scraped text: {text_cols}\n")

    # Identifiers are compared with all dashes as hyphens: the HTML writes some grade
    # bands with an en dash (RH.6–8.1, ELD.PI.9–10.1.Br) where the CSV has a hyphen.
    def rec_key(r):
        return (dashes(r["identifier"]), (r.get("Discipline") or "").strip() if use_course else "")

    def csv_key(r):
        return (dashes(r[csv_id]), (r.get(csv_course) or "").strip() if use_course else "")

    rec_text = [like_cde_export("\n".join(r.get(c, "") for c in text_cols)) for r in recs]
    by_key = defaultdict(list)
    for i, r in enumerate(recs):
        by_key[rec_key(r)].append(i)

    used, results = set(), []
    for line, row in enumerate(csv_rows, start=2):   # line 1 is the header
        cands = [i for i in by_key.get(csv_key(row), []) if i not in used]
        ct = row.get(csv_text) or ""
        match, how = None, ""
        for level, fn in (("exact", strict), ("loose", loose)):
            hits = [i for i in cands if fn(rec_text[i]) == fn(ct)]
            if hits:
                match, how = hits[0], level
                break
        if match is None:
            lc = loose(ct)
            hits = [i for i in cands if lc and (lc in loose(rec_text[i]) or loose(rec_text[i]) in lc)]
            if hits:
                match, how = hits[0], "partial"
        if match is None:
            how = f"none ({len(cands)} candidates with same key)"
        else:
            used.add(match)
        results.append((line, row, match, how))

    # ---- report file
    subject = Path(args.records_file).stem.split("_")[0]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{subject}_csv_to_records.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["csv_line", "identifier", "course", "record_id", "match"])
        for line, row, m, how in results:
            w.writerow([line, row[csv_id], row.get(csv_course, "") if use_course else "",
                        recs[m]["record_id"] if m is not None else "", how])

    # ---- console summary
    counts = Counter(how.split(" ")[0] for _, _, _, how in results)
    print(f"CSV rows: {len(csv_rows)} | scraped records: {len(recs)}")
    print("matches by pass:", dict(counts))
    unmatched = [(l, r, h) for l, r, m, h in results if m is None]
    unused = [i for i in range(len(recs)) if i not in used]
    print(f"CSV rows with no record: {len(unmatched)} | scraped records not used: {len(unused)}")
    for l, r, h in unmatched[:10]:
        print(f"  CSV line {l}: {r[csv_id]} {r.get(csv_course, '') if use_course else ''} -> {h}")
        print(f"      {strict(r.get(csv_text))[:150]!r}")
    for i in unused[:10]:
        r = recs[i]
        print(f"  unused record {r['record_id']}: {r['identifier']} {r.get('Discipline', '')}")
        print(f"      {strict(rec_text[i])[:150]!r}")
    for l, r, m, h in results:
        if h == "partial":
            print(f"  partial, CSV line {l} {r[csv_id]} -> record {recs[m]['record_id']}")

    if csv_grade:
        bad = [(l, r, recs[m]) for l, r, m, h in results if m is not None
               and dashes(r.get(csv_grade)) != dashes(recs[m].get("Grade Range") or recs[m].get("Grade"))]
        print(f"\ngrade differs between CSV and record: {len(bad)}")
        for l, r, rec in bad[:5]:
            print(f"  CSV line {l} {r[csv_id]}: CSV {r.get(csv_grade)!r} vs "
                  f"record {rec['record_id']} {rec.get('Grade Range') or rec.get('Grade')!r}")
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
