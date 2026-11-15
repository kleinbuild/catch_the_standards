#!/usr/bin/env python3
"""
lookup.py - show what a standard builds on.

    python src/lookup.py L.5.1
    python src/lookup.py L.5.1b            # also marks sub-item b
    python src/lookup.py 4.NF.3.a --depth 2
    python src/lookup.py A-CED.1           # several records: lists them
    python src/lookup.py --record 558      # one record, by CDE record ID

Reads data/build/standards.db (run `python src/load.py` first) and follows the
edges backwards from the standard you name: to the same strand in the grade
below, to the proficiency level below (ELD), and to the standards Learning
Commons says build towards it (math).

No link has been reviewed by the owner yet. The source of each is shown so you
can judge it.
"""
import argparse
import re
import sqlite3
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRADE_NAMES = {0: "K"}
LINK_WORDS = {
    "next_grade": "same strand, earlier grade",
    "next_level": "same standard, lower proficiency level",
    "builds_towards": "builds towards it",
}
SOURCE_WORDS = {"structural": "from the identifier", "learning_commons": "Learning Commons"}


def find_records(con, text):
    """Records whose identifier is `text`. Returns (rows, sub-item letter or None).

    Accepts a hyphen where CDE uses an en dash, and ELA's 'L.5.1b' for
    sub-item b of L.5.1.
    """
    wanted = text.strip().replace("–", "-")
    sql = ("SELECT * FROM standards WHERE identifier_norm = ? COLLATE NOCASE "
           "OR identifier_corrected = ? COLLATE NOCASE ORDER BY record_id")
    rows = con.execute(sql, (wanted, wanted)).fetchall()
    if rows:
        return rows, None
    m = re.fullmatch(r"(.+\d)\.?([a-z])", wanted)
    if m:
        rows = con.execute(sql, (m[1], m[1])).fetchall()
        rows = [r for r in rows if con.execute(
            "SELECT 1 FROM sub_items WHERE record_id = ? AND letter = ?",
            (r["record_id"], m[2])).fetchone()]
        return rows, (m[2] if rows else None)
    return [], None


def walk_back(con, record_id, max_depth):
    """Everything `record_id` builds on, nearest first.

    Returns a list of (steps, record_id, reached_from_record_id, type, source, note).
    This is a breadth-first search: all standards one link away, then all
    standards two links away, and so on. A standard reachable by two routes is
    listed once, at its shortest distance.
    """
    found, seen, frontier = [], {record_id}, [record_id]
    for steps in range(1, max_depth + 1):
        next_frontier = []
        for current in frontier:
            for row in con.execute(
                    "SELECT from_record_id, type, source, note FROM edges "
                    "WHERE to_record_id = ? ORDER BY type, from_record_id", (current,)):
                if row["from_record_id"] not in seen:
                    seen.add(row["from_record_id"])
                    next_frontier.append(row["from_record_id"])
                    found.append((steps, row["from_record_id"], current,
                                  row["type"], row["source"], row["note"]))
        frontier = next_frontier
        if not frontier:
            break
    more = any(con.execute("SELECT 1 FROM edges WHERE to_record_id = ? LIMIT 1", (r,)).fetchone()
               for r in frontier)
    return found, more


def grade_text(row):
    lo, hi = row["grade_min"], row["grade_max"]
    name = lambda g: GRADE_NAMES.get(g, str(g))
    return f"grade {name(lo)}" if lo == hi else f"grades {name(lo)}-{name(hi)}"


def label(row):
    extra = [x for x in (row["discipline"], row["proficiency_level"]) if x]
    return row["identifier"] + (f" ({', '.join(extra)})" if extra else "")


def wrapped(text, indent, first=None, width=96):
    return textwrap.fill(" ".join(text.split()), width=width,
                         initial_indent=indent if first is None else first,
                         subsequent_indent=indent)


def stem_of(con, row):
    """The standard's text without its lettered sub-items."""
    first = con.execute("SELECT text FROM sub_items WHERE record_id = ? AND letter = 'a'",
                        (row["record_id"],)).fetchone()
    if not first:
        return row["text_standard"]
    return re.split(r"\n\s*a\s?\.", row["text_standard"], maxsplit=1)[0]


def print_standard(con, row, indent, letter=None, sub_items=True):
    print(wrapped(stem_of(con, row), indent))
    if sub_items:
        for sub in con.execute("SELECT letter, text FROM sub_items WHERE record_id = ? "
                               "ORDER BY letter", (row["record_id"],)):
            mark = ">> " if sub["letter"] == letter else "   "
            print(wrapped(f"{sub['letter']}. {sub['text']}", indent + "      ",
                          first=indent + mark))


def show(con, row, letter, depth, sub_items):
    get = lambda rid: con.execute("SELECT * FROM standards WHERE record_id = ?", (rid,)).fetchone()
    print(f"{label(row)}   {grade_text(row)}   record {row['record_id']}")
    print(f"  {row['url']}")
    if row["identifier_corrected"]:
        print(f"  CDE's identifier looks wrong; read here as {row['identifier_corrected']}")
    print_standard(con, row, "  ", letter)

    found, more = walk_back(con, row["record_id"], depth)
    if not found:
        print("\nNothing recorded that this builds on.")
        return
    print("\nBuilds on:")
    for steps in sorted({f[0] for f in found}):
        print(f"\n  {steps} step{'s' if steps > 1 else ''} back")
        level = sorted((f for f in found if f[0] == steps),
                       key=lambda f: (-get(f[1])["grade_min"], get(f[1])["identifier"]))
        for _, rid, via, kind, source, note in level:
            r = get(rid)
            towards = "" if via == row["record_id"] else f" (towards {get(via)['identifier']})"
            print(f"    {label(r)}   {grade_text(r)}   record {rid}")
            print(f"      {LINK_WORDS.get(kind, kind)}{towards}; source: "
                  f"{SOURCE_WORDS.get(source, source)}" + (f"; {note}" if note else ""))
            print_standard(con, r, "      ", sub_items=sub_items)
    if more:
        print(f"\n  More lies further back. Use --depth {depth + 1} or higher to see it.")
    print("\nNone of these links has been reviewed yet.")


def main():
    # Standards text has characters (en dash, minus sign, multiplication sign)
    # that Windows' default output encoding lacks. UTF-8 has them all.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("identifier", nargs="?", help="e.g. L.5.1, 4.NF.3.a, ELD.PI.4.6a.Ex")
    ap.add_argument("--record", type=int, help="CDE record ID, when an identifier has several")
    ap.add_argument("--depth", type=int, default=3, help="how many links back to follow (default 3)")
    ap.add_argument("--no-sub-items", action="store_true",
                    help="leave the lettered sub-items out of the earlier standards")
    ap.add_argument("--db", type=Path, default=ROOT / "data" / "build" / "standards.db")
    args = ap.parse_args()
    if not args.db.exists():
        sys.exit(f"{args.db} does not exist. Run: python src/load.py")
    if not args.identifier and args.record is None:
        ap.error("give an identifier or --record")

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row      # lets a row be read by column name
    letter = None
    if args.record is not None:
        rows = con.execute("SELECT * FROM standards WHERE record_id = ?", (args.record,)).fetchall()
    else:
        rows, letter = find_records(con, args.identifier)
    if not rows:
        sys.exit(f"No standard found for {args.identifier or args.record!r}.")
    if len(rows) > 1:
        print(f"{args.identifier} is {len(rows)} records. Pick one with --record:\n")
        for r in rows:
            print(f"  --record {r['record_id']:<6} {label(r)}   {grade_text(r)}")
            print(wrapped(r["text_standard"][:150], "      "))
        return
    show(con, rows[0], letter, args.depth, not args.no_sub_items)


if __name__ == "__main__":
    main()
