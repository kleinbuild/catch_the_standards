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
    def with_parent(rid):
        """A sub-item record such as 4.NF.3.a also builds on whatever its
        parent standard 4.NF.3 builds on."""
        parent = con.execute("SELECT parent_record_id FROM standards WHERE record_id = ?",
                             (rid,)).fetchone()[0]
        return [rid] if parent is None else [rid, parent]

    found, seen, frontier = [], set(with_parent(record_id)), [record_id]
    for steps in range(1, max_depth + 1):
        next_frontier = []
        for current in frontier:
            for target in with_parent(current):
                for row in con.execute(
                        "SELECT from_record_id, type, source, note FROM edges "
                        "WHERE to_record_id = ? ORDER BY type, from_record_id", (target,)):
                    if row["from_record_id"] not in seen:
                        seen.add(row["from_record_id"])
                        next_frontier.append(row["from_record_id"])
                        found.append((steps, row["from_record_id"], target,
                                      row["type"], row["source"], row["note"]))
        frontier = next_frontier
        if not frontier:
            break
    more = any(con.execute("SELECT 1 FROM edges WHERE to_record_id = ? LIMIT 1", (t,)).fetchone()
               for r in frontier for t in with_parent(r))
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


def heading(row):
    where = (f"record {row['record_id']}" if row["origin"] == "cde"
             else "no CDE record; text from Learning Commons")
    return f"{label(row)}   {grade_text(row)}   {where}"


def print_standard(con, row, indent, letter=None, sub_items=True):
    print(wrapped(stem_of(con, row), indent))
    parts = [r["identifier"] for r in con.execute(
        "SELECT identifier FROM standards WHERE parent_record_id = ? ORDER BY identifier",
        (row["record_id"],))]
    if parts:
        print(wrapped("CDE records for its parts: " + ", ".join(parts), indent))
    if sub_items:
        for sub in con.execute("SELECT letter, text FROM sub_items WHERE record_id = ? "
                               "ORDER BY letter", (row["record_id"],)):
            mark = ">> " if sub["letter"] == letter else "   "
            print(wrapped(f"{sub['letter']}. {sub['text']}", indent + "      ",
                          first=indent + mark))


def print_bridge(con, row):
    """For a student who is both an English learner and in special education:
    the ELA standards listed against an ELD standard, or the reverse."""
    if row["subject"] == "eld" and row["id_parsed"]:
        names = [r["identifier"] for r in con.execute(
            "SELECT s.identifier FROM eld_ela_links l JOIN standards s ON s.record_id = l.ela_record_id "
            "WHERE l.eld_part = ? AND l.eld_number = ? AND l.eld_grade_min = ? "
            "AND s.is_placeholder = 0 "     # a range like RL 7-9 can cross "(Not applicable)"
            "ORDER BY s.id_strand, CAST(s.id_number AS INTEGER)",
            (row["id_strand"], row["id_number"], row["grade_min"]))]
        if names:
            whole = f"ELD {row['id_strand']} standard {row['id_number']}, {grade_text(row)}"
            print(f"\n  ELA standards listed against {whole} (all levels and letters):")
            print(wrapped(", ".join(names), "    "))
    elif row["subject"] == "ela":
        names = [f"{r['eld_part']} {r['eld_number']}" for r in con.execute(
            "SELECT eld_part, eld_number FROM eld_ela_links WHERE ela_record_id = ? "
            "ORDER BY eld_part, CAST(eld_number AS INTEGER)", (row["record_id"],))]
        if names:
            print(f"\n  ELD standards at this grade that list this standard "
                  f"(part and number; all levels):")
            print(wrapped(", ".join(names), "    "))


def show(con, row, letter, depth, sub_items):
    get = lambda rid: con.execute("SELECT * FROM standards WHERE record_id = ?", (rid,)).fetchone()
    print(heading(row))
    if row["url"]:
        print(f"  {row['url']}")
    if row["identifier_corrected"]:
        print(f"  CDE's identifier looks wrong; read here as {row['identifier_corrected']}")
    print_standard(con, row, "  ", letter)
    if row["parent_record_id"] is not None:
        parent = get(row["parent_record_id"])
        print(f"\n  Part of {heading(parent)}")
        print(wrapped(stem_of(con, parent), "    "))

    print_bridge(con, row)

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
            print(f"    {heading(r)}")
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
