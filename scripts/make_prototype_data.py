#!/usr/bin/env python3
"""
make_prototype_data.py - write the data file for the interface prototype.

    python src/load.py                        # build the database first
    python scripts/make_prototype_data.py     # writes docs/design/prototype/data.js

The prototype page (docs/design/prototype/index.html) searches the standards
and draws what each one builds on, all inside the browser. This script copies
what it needs out of the database into one JavaScript file the page loads:
every standard, link, ELD-to-ELA row and learning component. Nothing is made
up here: every text, link, source and reviewed flag is read from
data/build/standards.db.

The file is JavaScript, not JSON, so the page works when opened by
double-click. A browser will not let a page opened from disk read a separate
JSON file, but it will run a script that sits beside it.

data.js is build output, like the database: it is not committed. Run this
script again after `python src/load.py` to refresh it.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import lookup  # noqa: E402   (src/lookup.py: the same helpers the command line tool uses)


def one_line(text):
    return " ".join(text.split())


def where(row):
    """The headings CDE files the record under, for a line of context."""
    if row["subject"] == "eld":
        parts = [row["critical_principle"], row["cluster"], row["content_strand"]]
    else:
        parts = [row["domain"], row["cluster"]]
    return " / ".join(p for p in parts if p)


def export(con):
    """Everything the page needs, as plain lists and dictionaries."""
    subs = {}
    for r in con.execute("SELECT record_id, letter, text FROM sub_items ORDER BY record_id, letter"):
        subs.setdefault(r["record_id"], []).append([r["letter"], one_line(r["text"])])

    standards = []
    for row in con.execute("SELECT * FROM standards ORDER BY subject, grade_min, grade_max, "
                           "discipline, id_strand, CAST(id_number AS REAL), id_letter, "
                           "CASE proficiency_level WHEN 'Emerging' THEN 1 WHEN 'Expanding' THEN 2 "
                           "WHEN 'Bridging' THEN 3 END, identifier"):
        standards.append({
            "id": row["record_id"],                    # CDE record ID; negative for an added parent
            "identifier": row["identifier"],           # as CDE writes it
            "norm": row["identifier_norm"],            # en dashes as hyphens, for matching typed codes
            "corrected": row["identifier_corrected"],
            "subject": row["subject"],
            "grade": lookup.grade_text(row),
            "gmin": row["grade_min"], "gmax": row["grade_max"],
            "course": row["discipline"],               # high school math only
            "level": row["proficiency_level"],         # ELD only
            "strand": row["id_strand"], "number": row["id_number"],
            "where": where(row),
            "text": one_line(lookup.stem_of(con, row)),
            "subs": subs.get(row["record_id"], []),
            "url": row["url"],                         # None for a parent standard CDE has no record for
            "parent": row["parent_record_id"],
            "placeholder": row["is_placeholder"],
        })

    return {
        "standards": standards,
        # [from, to, type, source, note, reviewed, confidence]; `from` is the earlier standard
        "edges": [list(r) for r in con.execute(
            "SELECT from_record_id, to_record_id, type, source, note, reviewed, confidence "
            "FROM edges ORDER BY to_record_id, type, from_record_id")],
        # [ELD part, ELD number, ELD grade_min, ELA record ID, reviewed]
        "eld_ela": [list(r) for r in con.execute(
            "SELECT eld_part, eld_number, eld_grade_min, ela_record_id, reviewed "
            "FROM eld_ela_links ORDER BY eld_grade_min, eld_part, eld_number, ela_record_id")],
        # component ID -> [text, author]
        "components": {r["component_id"]: [one_line(r["text"]), r["author"]] for r in con.execute(
            "SELECT component_id, text, author FROM learning_components ORDER BY component_id")},
        # [teacher term, standards term, subject or None, evidence, source, reviewed]
        "search_terms": [list(r) for r in con.execute(
            "SELECT teacher_term, standards_term, subject, evidence, source, reviewed "
            "FROM search_terms ORDER BY teacher_term, standards_term")],
        # [record ID, sub-item letter or '', component ID, reviewed]
        "component_links": [list(r) for r in con.execute(
            "SELECT record_id, letter, component_id, reviewed FROM component_links "
            "ORDER BY record_id, letter, component_id")],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=ROOT / "data" / "build" / "standards.db")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "design" / "prototype" / "data.js")
    args = ap.parse_args()
    if not args.db.exists():
        sys.exit(f"{args.db} does not exist. Run: python src/load.py")
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    data = export(con)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # separators=(",", ":") leaves out the spaces JSON normally puts after commas; the file is a third smaller.
    text = ("// Written by scripts/make_prototype_data.py from data/build/standards.db. Do not edit.\n"
            "window.PROTOTYPE_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(f"{len(data['standards'])} standards, {len(data['edges'])} links, "
          f"{len(data['eld_ela'])} ELD-to-ELA rows, {len(data['components'])} learning components")
    print(f"Wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
