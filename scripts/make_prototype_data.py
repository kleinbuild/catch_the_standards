#!/usr/bin/env python3
"""
make_prototype_data.py - write the data file for the interface prototype.

    python src/load.py                        # build the database first
    python scripts/make_prototype_data.py     # writes docs/design/prototype/data.js

The prototype page (docs/design/prototype/index.html) shows a handful of
standards so the owner can react to a layout. This script copies what
`python src/lookup.py` would print for each of them out of the database and
into one JavaScript file the page loads. Nothing is made up here: every text,
link, source and reviewed flag is read from data/build/standards.db.

The file is JavaScript, not JSON, so the page works when opened by
double-click. A browser will not let a page opened from disk read a separate
JSON file, but it will run a script that sits beside it.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import lookup  # noqa: E402   (src/lookup.py: the same queries the command line tool uses)

EXAMPLES = ["L.5.1", "4.NF.3.a", "ELD.PI.4.6a.Ex"]
DEPTH = 3


def record(con, row):
    """One standard as the page needs it."""
    return {
        "id": row["record_id"],
        "identifier": row["identifier"],
        "label": lookup.label(row),
        "grade": lookup.grade_text(row),
        "grade_min": row["grade_min"],
        "subject": row["subject"],
        "url": row["url"],                 # None for a parent standard CDE has no record for
        "origin": row["origin"],
        "text": " ".join(lookup.stem_of(con, row).split()),
        "subs": [{"letter": s["letter"], "text": " ".join(s["text"].split())}
                 for s in con.execute("SELECT letter, text FROM sub_items WHERE record_id = ? "
                                      "ORDER BY letter", (row["record_id"],))],
        "parts": [r["identifier"] for r in con.execute(
            "SELECT identifier FROM standards WHERE parent_record_id = ? ORDER BY identifier",
            (row["record_id"],))],
    }


def bridge(con, row):
    """ELA standards listed against an ELD standard, grouped by strand; or the
    ELD standards that list an ELA standard, grouped by part."""
    if row["subject"] == "eld" and row["id_parsed"]:
        rows = con.execute(
            "SELECT s.identifier, s.id_strand, l.reviewed, l.source FROM eld_ela_links l "
            "JOIN standards s ON s.record_id = l.ela_record_id "
            "WHERE l.eld_part = ? AND l.eld_number = ? AND l.eld_grade_min = ? "
            "AND s.is_placeholder = 0 ORDER BY s.id_strand, CAST(s.id_number AS INTEGER)",
            (row["id_strand"], row["id_number"], row["grade_min"])).fetchall()
        title = (f"ELA standards listed against ELD {row['id_strand']} standard "
                 f"{row['id_number']}, {lookup.grade_text(row)} (all levels and letters)")
        pairs = [(r["id_strand"], r["identifier"]) for r in rows]
    elif row["subject"] == "ela":
        rows = con.execute(
            "SELECT eld_part, eld_number, reviewed, source FROM eld_ela_links "
            "WHERE ela_record_id = ? ORDER BY eld_part, CAST(eld_number AS INTEGER)",
            (row["record_id"],)).fetchall()
        title = "ELD standards at this grade that list this standard (part and number; all levels)"
        pairs = [(r["eld_part"], f"{r['eld_part']} {r['eld_number']}") for r in rows]
    else:
        return None
    if not rows:
        return None
    groups = {}
    for group, name in pairs:
        groups.setdefault(group, []).append(name)
    return {"title": title,
            "groups": [{"name": g, "items": items} for g, items in groups.items()],
            "sources": sorted({r["source"] for r in rows}),
            "reviewed": sum(r["reviewed"] for r in rows), "count": len(rows)}


def components(con, row):
    return [{"letter": r["letter"], "text": r["text"], "author": r["author"],
             "reviewed": r["reviewed"]}
            for r in con.execute(
                "SELECT l.letter, c.text, c.author, l.reviewed FROM component_links l "
                "JOIN learning_components c USING (component_id) "
                "WHERE l.record_id = ? ORDER BY l.letter, c.text", (row["record_id"],))]


def example(con, identifier):
    rows, letter = lookup.find_records(con, identifier)
    if len(rows) != 1:
        sys.exit(f"{identifier}: expected one record, found {len(rows)}")
    row = rows[0]
    get = lambda rid: con.execute("SELECT * FROM standards WHERE record_id = ?", (rid,)).fetchone()
    found, more = lookup.walk_back(con, row["record_id"], DEPTH)
    back = []
    for steps, rid, via, kind, source, note in found:
        reviewed = con.execute(
            "SELECT reviewed FROM edges WHERE from_record_id = ? AND to_record_id = ? "
            "AND type = ? AND source = ?", (rid, via, kind, source)).fetchone()[0]
        back.append({"steps": steps, "towards": get(via)["identifier"],
                     "towards_id": via, "type": kind, "source": source, "note": note,
                     "reviewed": reviewed, "record": record(con, get(rid))})
    # Nearest first; within a step, higher grades first, as lookup.py prints them.
    back.sort(key=lambda b: (b["steps"], -b["record"]["grade_min"], b["record"]["identifier"]))
    parent = get(row["parent_record_id"]) if row["parent_record_id"] is not None else None
    return {"key": identifier, "letter": letter, "record": record(con, row),
            "parent": record(con, parent) if parent else None,
            "bridge": bridge(con, row), "components": components(con, row),
            "parent_components": components(con, parent) if parent else [],
            "back": back, "more": more}


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
    data = {"depth": DEPTH, "examples": [example(con, i) for i in EXAMPLES]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = ("// Written by scripts/make_prototype_data.py from data/build/standards.db. Do not edit.\n"
            "window.PROTOTYPE_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    args.out.write_text(text, encoding="utf-8", newline="\n")
    for e in data["examples"]:
        print(f"{e['key']}: {len(e['back'])} earlier standards, {len(e['components'])} components")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
