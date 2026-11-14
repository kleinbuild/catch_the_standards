#!/usr/bin/env python3
"""
load.py - rebuild data/build/standards.db from the scraped records files.

    python src/load.py

Reads the newest data/raw/<subject>_records_<date>.csv for math, ela and eld,
plus docs/reference/codes.csv, and writes data/build/standards.db. The old
database is replaced, never updated in place (decisions 0007, 0010).

Every standard is keyed by its CDE record ID (0011). Text and identifiers are
stored exactly as CDE writes them; anything the loader works out (grades,
identifier parts, sub-items) goes in separate columns beside them.

The loader stops with a message, and leaves the old database untouched, when a
file has something it does not recognise: an unknown column, a grade it cannot
read, a field label missing from codes.csv. It does not guess.

Uses only Python's standard library, so it needs no installed packages.
"""
import argparse
import csv
import datetime as dt
import hashlib
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = "1"
SUBJECTS = ("math", "ela", "eld")

# Records-file column -> database column.
FIELD_COLUMNS = {
    "Subject Area": "subject_area",
    "Domain": "domain",
    "Cluster": "cluster",
    "Discipline": "discipline",
    "Conceptual Category": "conceptual_category",
    "Critical Principle": "critical_principle",
    "Proficiency Level": "proficiency_level",
    "Content Strand": "content_strand",
}
TEXT_COLUMNS = {
    "text_Cluster": "text_cluster",
    "text_Standard": "text_standard",
    "text_Footnote": "text_footnote",
}
FIXED_COLUMNS = {"record_id", "url", "identifier", "Grade", "Grade Range", "page"}
REQUIRED_COLUMNS = {"record_id", "url", "identifier", "text_Standard", "page"}

# (subject, code) -> (alias code, reason). Decision 0003.
CLUSTER_ALIASES = {
    ("ela", 3): (2, 'Code 3 "Conventions of Standards English" is a misspelled copy of '
                    'code 2 covering grades 6-8 only (decision 0003).'),
}

EN_DASH, MINUS = "–", "−"
URL_PREFIX = "https://www2.cde.ca.gov/cacs/id/web/"


class LoadError(Exception):
    """Something in the input files the loader will not guess its way past."""


# ---------- small pure functions (tested in tests/test_load.py) ----------

def normalize_identifier(identifier):
    """RH.6–8.1 -> RH.6-8.1. Only en dashes change (0012)."""
    return identifier.replace(EN_DASH, "-")


def search_form(text):
    """Text with the minus sign and en dash written as a keyboard hyphen (0012)."""
    return text.replace(MINUS, "-").replace(EN_DASH, "-")


def parse_grade(label):
    """'K' -> (0, 0), '5' -> (5, 5), '9–10' or '9-10' -> (9, 10). Decision 0004."""
    def one(g):
        g = g.strip()
        if g in ("K", "TK & K"):
            return 0
        if g.isdigit() and 1 <= int(g) <= 12:
            return int(g)
        raise LoadError(f"cannot read grade {label!r}")
    parts = normalize_identifier(label).split("-")
    if len(parts) == 1:
        return one(parts[0]), one(parts[0])
    if len(parts) == 2 and one(parts[0]) < one(parts[1]):
        return one(parts[0]), one(parts[1])
    raise LoadError(f"cannot read grade {label!r}")


GRADE = r"(K|\d+(?:-\d+)?)"
ELA_ID = re.compile(rf"^([A-Z]+)\.{GRADE}\.(\d+)$")
ELD_ID = re.compile(rf"^ELD\.(PI|PII)\.{GRADE}\.(\d+)([a-z]?)\.(Em|Ex|Br)$")
MATH_K8_ID = re.compile(r"^(K|\d)\.([A-Z]+)\.(\d+(?:\.\d+)?)(?:\.([a-z]))?$")
MATH_HS_ID = re.compile(r"^([A-Z][A-Za-z&-]*)\.(\d+(?:\.\d+)?)(?:\.([a-z]))?$")


def parse_identifier(subject, identifier_norm):
    """Split a dash-normalized identifier into parts (0005).

    Returns a dict with strand, grade, number, letter, level and parent, or
    None when the identifier does not have the expected shape. CDE has a few
    malformed ones (RL.2..2, ELD.PI.12a.Br); those return None and are stored
    as written, unrepaired.
    """
    parts = dict(strand=None, grade=None, number=None, letter=None, level=None, parent=None)
    if subject == "ela":
        m = ELA_ID.match(identifier_norm)
        if not m:
            return None
        parts.update(strand=m[1], grade=m[2], number=m[3])
    elif subject == "eld":
        m = ELD_ID.match(identifier_norm)
        if not m:
            return None
        parts.update(strand=m[1], grade=m[2], number=m[3], letter=m[4] or None, level=m[5])
    elif subject == "math":
        m = MATH_K8_ID.match(identifier_norm)
        if m:
            parts.update(grade=m[1], strand=m[2], number=m[3], letter=m[4])
        else:
            m = MATH_HS_ID.match(identifier_norm)
            if not m:
                return None
            parts.update(strand=m[1], number=m[2], letter=m[3])
        if parts["letter"]:
            parts["parent"] = identifier_norm.rsplit(".", 1)[0]
    else:
        raise LoadError(f"unknown subject {subject!r}")
    return parts


SUB_ITEM_LINE = re.compile(r"^\s*([a-z])\s?\.\s*(\S.*)$")


def split_sub_items(text):
    """'Stem\\na. first\\nb. second' -> ('Stem', [('a', 'first'), ('b', 'second')]).

    A line starts a sub-item only if its letter is the next one expected (a,
    then b, ...). That keeps a wrapped line beginning "e.g." from being read as
    item e, and it accepts CDE's two typos: "c . Decode" (RF.2.3) and
    "d.Review" (SL.4.1). Any other line continues whatever came before it.
    """
    stem, items = [], []
    for line in text.split("\n"):
        if not line.strip():
            continue
        m = SUB_ITEM_LINE.match(line)
        if m and m[1] == chr(ord("a") + len(items)):
            items.append([m[1], m[2].strip()])
        elif items:
            items[-1][1] += " " + line.strip()
        else:
            stem.append(line.strip())
    return " ".join(stem), [tuple(i) for i in items]


CA_WORD = re.compile(r"\bCA\b")


def flags(text):
    """(ca_marker, has_asterisk) for a piece of standard text."""
    return int(bool(CA_WORD.search(text))), int("*" in text)


# ---------- reading the input files ----------

def newest_records_file(raw_dir, subject):
    """data/raw/math_records_2026-10-16.csv; the date in the name decides 'newest'."""
    found = sorted(raw_dir.glob(f"{subject}_records_????-??-??.csv"))
    if not found:
        raise LoadError(f"no {subject}_records_<date>.csv in {raw_dir}. "
                        f"Run: python scripts/scrape_cacs_records.py {subject}")
    return found[-1]


def read_codes(codes_path):
    """{(subject, level, label): (param, code)} for the c0..c3 filter levels."""
    if not codes_path.exists():
        raise LoadError(f"{codes_path} is missing. Run: python scripts/cacs_codes.py")
    codes = {}
    with open(codes_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["subject"] in SUBJECTS and re.fullmatch(r"c\d", row["param"]):
                codes[(row["subject"], row["level"], row["label"])] = (row["param"], int(row["code"]))
    return codes


def read_records(path, subject, codes):
    """Turn one records file into (standards rows, sub-item rows, notes)."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        rows = list(reader)

    unknown = columns - FIXED_COLUMNS - set(FIELD_COLUMNS) - set(TEXT_COLUMNS)
    missing = REQUIRED_COLUMNS - columns
    if unknown or missing:
        raise LoadError(f"{path.name}: unknown columns {sorted(unknown)}, missing columns "
                        f"{sorted(missing)}. Map new columns in src/load.py before loading.")
    if not rows:
        raise LoadError(f"{path.name}: no rows")

    standards, sub_items = [], []
    notes = {"unparsed": [], "grade_mismatch": []}
    for line, row in enumerate(rows, start=2):          # line 1 is the header
        where = f"{path.name} line {line} ({row['identifier']})"
        record_id = row["record_id"]
        if not record_id.isdigit() or row["url"] != URL_PREFIX + record_id:
            raise LoadError(f"{where}: record_id {record_id!r} and url {row['url']!r} do not agree")

        grade_label = row.get("Grade") or row.get("Grade Range") or ""
        try:
            grade_min, grade_max = parse_grade(grade_label)
        except LoadError as e:
            raise LoadError(f"{where}: {e}") from None

        fields = {}
        for label, column in FIELD_COLUMNS.items():
            value = (row.get(label) or "").strip() or None
            fields[column] = value
            if value and (subject, label, value) not in codes:
                raise LoadError(f"{where}: {label} {value!r} is not in codes.csv for {subject}. "
                                "Re-run scripts/cacs_codes.py, or check the scrape.")
        cluster_code = merged = None
        if fields["cluster"]:
            cluster_code = codes[(subject, "Cluster", fields["cluster"])][1]
            merged = CLUSTER_ALIASES.get((subject, cluster_code), (cluster_code,))[0]

        texts = {column: (row.get(name) or "") for name, column in TEXT_COLUMNS.items()}
        if not texts["text_standard"].strip():
            raise LoadError(f"{where}: empty standard text")
        searchable = search_form("\n".join(t for t in texts.values() if t))

        identifier = row["identifier"]
        identifier_norm = normalize_identifier(identifier)
        parts = parse_identifier(subject, identifier_norm)
        if parts is None:
            notes["unparsed"].append((int(record_id), identifier))
            parts = dict(strand=None, grade=None, number=None, letter=None, level=None, parent=None)
        elif parts["grade"] and parse_grade(parts["grade"]) != (grade_min, grade_max):
            notes["grade_mismatch"].append((int(record_id), identifier, grade_label))

        ca_marker, has_asterisk = flags(texts["text_standard"])
        standards.append((
            int(record_id), row["url"], subject, identifier, identifier_norm,
            grade_label, grade_min, grade_max,
            fields["subject_area"], fields["domain"], fields["cluster"], cluster_code, merged,
            fields["discipline"], fields["conceptual_category"], fields["critical_principle"],
            fields["proficiency_level"], fields["content_strand"],
            texts["text_cluster"] or None, texts["text_standard"], texts["text_footnote"] or None,
            searchable,
            int(parts["strand"] is not None), parts["strand"], parts["grade"], parts["number"],
            parts["letter"], parts["level"], parts["parent"],
            ca_marker, has_asterisk, path.name, int(row["page"]),
        ))
        for letter, text in split_sub_items(texts["text_standard"])[1]:
            sub_items.append((int(record_id), letter, text, *flags(text)))
    return standards, sub_items, notes


# ---------- building the database ----------

def build(raw_dir, codes_path, schema_path, db_path):
    """Read everything, then write the database. Returns a summary dict."""
    codes = read_codes(codes_path)
    loaded, summary = [], {"subjects": {}, "unparsed": [], "grade_mismatch": []}
    seen = {}
    for subject in SUBJECTS:
        path = newest_records_file(raw_dir, subject)
        standards, sub_items, notes = read_records(path, subject, codes)
        for row in standards:
            if row[0] in seen:
                raise LoadError(f"record ID {row[0]} appears twice: {seen[row[0]]} and {path.name}")
            seen[row[0]] = path.name
        loaded.append((subject, path, standards, sub_items))
        summary["subjects"][subject] = {"file": path.name, "records": len(standards),
                                        "sub_items": len(sub_items)}
        summary["unparsed"] += notes["unparsed"]
        summary["grade_mismatch"] += notes["grade_mismatch"]

    # Build into a temporary file and swap it in at the end, so a failure
    # part-way never leaves a half-written standards.db behind.
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = db_path.with_name(db_path.name + ".tmp")
    tmp_path.unlink(missing_ok=True)
    con = sqlite3.connect(tmp_path)
    try:
        con.executescript(schema_path.read_text(encoding="utf-8"))
        con.executemany("INSERT INTO build_info VALUES (?, ?)", [
            ("schema_version", SCHEMA_VERSION),
            ("built_at_utc", dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")),
        ])
        con.executemany("INSERT INTO filter_codes VALUES (?, ?, ?, ?, ?)",
                        [(s, param, level, code, label)
                         for (s, level, label), (param, code) in sorted(codes.items())])
        con.executemany("INSERT INTO cluster_alias VALUES (?, ?, ?, ?)",
                        [(s, code, alias, reason)
                         for (s, code), (alias, reason) in CLUSTER_ALIASES.items()])
        for subject, path, standards, sub_items in loaded:
            con.execute("INSERT INTO source_files VALUES (?, ?, ?, ?)",
                        (subject, path.name, hashlib.sha256(path.read_bytes()).hexdigest(),
                         len(standards)))
            con.executemany(f"INSERT INTO standards VALUES ({','.join('?' * 33)})", standards)
            con.executemany("INSERT INTO sub_items VALUES (?, ?, ?, ?, ?)", sub_items)
        con.commit()
    finally:
        con.close()
    tmp_path.replace(db_path)
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("--codes", type=Path, default=ROOT / "docs" / "reference" / "codes.csv")
    ap.add_argument("--db", type=Path, default=ROOT / "data" / "build" / "standards.db")
    args = ap.parse_args()
    try:
        summary = build(args.raw, args.codes, ROOT / "src" / "schema.sql", args.db)
    except LoadError as e:
        sys.exit(f"Load stopped, database not changed.\n  {e}")

    for subject, s in summary["subjects"].items():
        print(f"{subject:5} {s['records']:4} records, {s['sub_items']:3} sub-items   from {s['file']}")
    print(f"\nidentifiers the loader could not split into parts: {len(summary['unparsed'])}")
    for record_id, identifier in summary["unparsed"]:
        print(f"  record {record_id}: {identifier}")
    print(f"grade in the identifier differs from the Grade field: {len(summary['grade_mismatch'])}")
    for record_id, identifier, grade in summary["grade_mismatch"]:
        print(f"  record {record_id}: {identifier} has Grade {grade}")
    print(f"\nWrote {args.db}")


if __name__ == "__main__":
    main()
