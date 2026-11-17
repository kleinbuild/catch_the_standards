#!/usr/bin/env python3
"""
make_review_sheets.py - write the sheets the owner marks, in data/curated/review/.

    python src/load.py
    python scripts/make_review_sheets.py

Each sheet lists the rows that most need a teacher's judgment, most doubtful
first. It does not list every link: a link that is not on a sheet stays in the
database as it is, reviewed=0.

The sheets are the owner's work once marked, so this script never changes or
reorders a row that is already there. Run again later, it only adds rows that
are new (to the end of the sheet).

How the owner marks a row: see data/curated/review/README.md.

Sheets:
  ela_links.csv             same strand and number in the next grade, but the wording changes a lot
  eld_links.csv             next-grade links where the lettering changes, or the wording changes a lot
  math_links.csv            Learning Commons links that jump three or more grades, or involve the
                            Statistics and Probability course
  math_link_candidates.csv  sub-item pairs a link to a parent standard could also mean (not loaded
                            unless kept)
  pairings.csv              records whose text differs from the Learning Commons item they are paired with
  eld_ela_notes.csv         the ELA standards listed against each ELD standard, one row per ELD standard
"""
import argparse
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from load import split_sub_items                    # noqa: E402
from join_learning_commons import similarity        # noqa: E402

OWNER_COLUMNS = ["decision", "confidence", "owner_note"]
LINK_HEADER = (["priority", "why", "from_identifier", "from_grade", "from_text",
                "to_identifier", "to_grade", "to_text"] + OWNER_COLUMNS +
               ["from_record_id", "to_record_id", "type", "reviewed"])
LINK_KEY = ("from_record_id", "to_record_id", "type")


def stem(row):
    """The standard's text without lettered sub-items, on one line."""
    return " ".join(split_sub_items(row["text_standard"])[0].split())


def label(row):
    extra = row["discipline"] or ""
    return row["identifier"] + (f" ({extra})" if extra else "")


def link_row(priority, why, a, b, kind):
    return {"priority": priority, "why": why,
            "from_identifier": label(a), "from_grade": a["grade_label"], "from_text": stem(a),
            "to_identifier": label(b), "to_grade": b["grade_label"], "to_text": stem(b),
            "decision": "", "owner_note": "",
            "from_record_id": a["record_id"], "to_record_id": b["record_id"],
            "type": kind, "reviewed": 0}


def add_confidence_column(path, header):
    """A sheet written before the confidence column existed gets the column,
    empty, between decision and owner_note. Every other cell, and the order of
    the rows, stays as it is. A sheet that already has the column, or whose
    columns differ in any other way, is not touched."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows or rows[0] != [c for c in header if c != "confidence"]:
        return False
    at = header.index("confidence")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(r[:at] + [""] + r[at:] for r in rows[1:])
    return True


def write_sheet(path, header, key, rows):
    """Create the sheet, or add to its end the rows whose key is not in it yet.
    Returns (rows already there, rows added)."""
    rows = sorted(rows, key=lambda r: r["priority"])        # stable: keeps the given order within a priority
    for r in rows:
        r.setdefault("confidence", "")
    existing = set()
    if path.exists():
        if add_confidence_column(path, header):
            print(f"{path.name}: added the empty confidence column")
        # utf-8-sig reads the file with or without the marker Excel puts at the start
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != header:
                sys.exit(f"{path} has different columns from the ones this script writes. "
                         "It was not touched. Sort that out by hand before running again.")
            existing = {tuple(str(r[k]) for k in key) for r in reader}
    new = [r for r in rows if tuple(str(r[k]) for k in key) not in existing]
    if not path.exists():
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f, lineterminator="\n").writerow(header)
    if new:
        with open(path, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=header, lineterminator="\n")
            w.writerows(new)
    return len(existing), len(new)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=ROOT / "data" / "build" / "standards.db")
    ap.add_argument("--derived", type=Path, default=ROOT / "data" / "derived")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "curated" / "review")
    args = ap.parse_args()
    if not args.db.exists():
        sys.exit(f"{args.db} does not exist. Run: python src/load.py")
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    std = {r["record_id"]: r for r in con.execute("SELECT * FROM standards")}
    edges = con.execute("SELECT * FROM edges ORDER BY from_record_id, to_record_id").fetchall()
    args.out.mkdir(parents=True, exist_ok=True)
    report = []

    # ---- ELA: wording changes a lot from one grade to the next
    rows = []
    for e in edges:
        a, b = std[e["from_record_id"]], std[e["to_record_id"]]
        if a["subject"] == "ela" and e["type"] == "next_grade":
            sim = similarity(stem(a), stem(b))
            if sim < 0.3:
                rows.append((sim, link_row(
                    1 if sim < 0.2 else 2,
                    f"same strand and number, but the wording is {round(sim * 100)}% alike; "
                    "is it the same skill a grade on?", a, b, e["type"])))
    rows = [r for _, r in sorted(rows, key=lambda x: x[0])]
    report.append(("ela_links.csv", write_sheet(args.out / "ela_links.csv", LINK_HEADER, LINK_KEY, rows)))

    # ---- ELD: lettering changes, or wording changes a lot
    rows, seen = [], set()
    for e in edges:
        a, b = std[e["from_record_id"]], std[e["to_record_id"]]
        if a["subject"] != "eld" or e["type"] != "next_grade":
            continue
        sim = similarity(a["text_standard"], b["text_standard"])
        if e["note"]:
            rows.append((0, sim, link_row(
                1, "the lettering differs between these grades, so every record of this number "
                   "was linked; keep only the pairs that are the same skill", a, b, e["type"])))
        elif sim < 0.3:
            rows.append((1, sim, link_row(
                2, f"same part, number and level, but the wording is {round(sim * 100)}% alike",
                a, b, e["type"])))
    rows = [r for *_, r in sorted(rows, key=lambda x: (x[0], x[2]["from_identifier"], x[2]["to_identifier"]))]
    report.append(("eld_links.csv", write_sheet(args.out / "eld_links.csv", LINK_HEADER, LINK_KEY, rows)))

    # ---- math: long jumps, and the statistics course
    rows = []
    for e in edges:
        a, b = std[e["from_record_id"]], std[e["to_record_id"]]
        if e["type"] != "builds_towards":
            continue
        courses = {a["discipline"], b["discipline"]}
        if courses == {None} and b["grade_min"] - a["grade_min"] >= 3:
            rows.append((0, -(b["grade_min"] - a["grade_min"]), link_row(
                1, f"Learning Commons link that jumps {b['grade_min'] - a['grade_min']} grades",
                a, b, e["type"])))
        elif "Statistics and Probability" in courses:
            rows.append((1, 0, link_row(
                2, "involves the course Statistics and Probability, which the join script "
                   "treats as following either pathway (an assumption)", a, b, e["type"])))
    rows = [r for *_, r in sorted(rows, key=lambda x: (x[0], x[1], x[2]["from_identifier"]))]
    report.append(("math_links.csv", write_sheet(args.out / "math_links.csv", LINK_HEADER, LINK_KEY, rows)))

    # ---- math: sub-item pairs a link to a parent could also mean
    header = ["priority", "published_link"] + LINK_HEADER[1:]
    rows, groups = [], {}
    with open(args.derived / "learning_commons_spread_candidates.csv", encoding="utf-8", newline="") as f:
        for c in csv.DictReader(f):
            a, b = std[int(c["from_record_id"])], std[int(c["to_record_id"])]
            n = groups.setdefault(c["lc_relationship_id"], len(groups) + 1)
            row = link_row(1, "Learning Commons links the parent standard; does this "
                              "particular part belong in the link?", a, b, "builds_towards")
            row["published_link"] = (f"{n}: {c['published_from']} builds towards {c['published_to']}"
                                     " (Learning Commons codes)")
            rows.append(row)
    report.append(("math_link_candidates.csv",
                   write_sheet(args.out / "math_link_candidates.csv", header, LINK_KEY, rows)))

    # ---- pairings whose text differs
    header = ["priority", "why", "identifier", "grade", "cde_text", "lc_statement_code", "lc_text"] \
        + OWNER_COLUMNS + ["record_id", "lc_identifier", "reviewed"]
    rows = []
    with open(args.derived / "learning_commons_text_differs.csv", encoding="utf-8", newline="") as f:
        for d in sorted(csv.DictReader(f), key=lambda d: float(d["text_similarity"])):
            r = std[int(d["record_id"])]
            rows.append({"priority": 1 if float(d["text_similarity"]) < 0.6 else 2,
                         "why": f"paired by code, but the texts are {round(float(d['text_similarity']) * 100)}% "
                                "alike; is the Learning Commons item the same standard?",
                         "identifier": label(r), "grade": r["grade_label"], "cde_text": d["cde_text"],
                         "lc_statement_code": d["lc_statement_code"], "lc_text": d["lc_text"],
                         "decision": "", "owner_note": "", "record_id": d["record_id"],
                         "lc_identifier": d["lc_identifier"], "reviewed": 0})
    report.append(("pairings.csv", write_sheet(args.out / "pairings.csv", header,
                                               ("record_id", "lc_identifier"), rows)))

    # ---- ELD notes: one row per ELD standard
    header = ["priority", "why", "eld_standard", "grade", "eld_strand_name", "note_as_written",
              "ela_standards_read_from_it"] + OWNER_COLUMNS + \
             ["eld_part", "eld_number", "eld_grade_min", "reviewed"]
    notes, first = {}, set()
    with open(args.derived / "learning_commons_eld_ela.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            key = (r["eld_part"], r["eld_number"], r["eld_grade_min"])
            n = notes.setdefault(key, {"label": r["eld_grade_label"], "segments": [], "ela": []})
            if r["as_written"] not in n["segments"]:
                n["segments"].append(r["as_written"])
            n["ela"].append(r["ela_identifier"])
    rows = []
    for (part, number, grade_min), n in sorted(notes.items(), key=lambda k: (int(k[0][2]), k[0][0], int(k[0][1]))):
        strand = con.execute(
            "SELECT content_strand FROM standards WHERE subject = 'eld' AND id_strand = ? "
            "AND id_number = ? AND grade_min = ? LIMIT 1", (part, number, int(grade_min))).fetchone()
        sample = (part, grade_min) not in first          # the first standard of each part in each grade
        first.add((part, grade_min))
        rows.append({"priority": 1 if sample else 2,
                     "why": "compare with the 'Corresponding CA CCSS for ELA/Literacy' column of the "
                            "published CA ELD Standards" + (" (sample: one per part per grade)" if sample else ""),
                     "eld_standard": f"ELD {part} standard {number}", "grade": n["label"],
                     "eld_strand_name": strand[0] if strand else "",
                     "note_as_written": "; ".join(n["segments"]),
                     "ela_standards_read_from_it": ", ".join(n["ela"]),
                     "decision": "", "owner_note": "", "eld_part": part, "eld_number": number,
                     "eld_grade_min": grade_min, "reviewed": 0})
    report.append(("eld_ela_notes.csv", write_sheet(args.out / "eld_ela_notes.csv", header,
                                                    ("eld_part", "eld_number", "eld_grade_min"), rows)))

    for name, (already, added) in report:
        print(f"{name:26} {already:4} rows already there, {added:4} added")
    print(f"\nSheets are in {args.out}")


if __name__ == "__main__":
    main()
