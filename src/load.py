#!/usr/bin/env python3
"""
load.py - rebuild data/build/standards.db from the scraped records files.

    python src/load.py

Reads the newest data/raw/<subject>_records_<date>.csv for math, ela and eld,
docs/reference/codes.csv, data/curated/identifier_corrections.csv and, if they
exist, the learning_commons_*.csv files in data/derived/ (parents, edges,
eld_ela, components, component_links), the owner's decisions in
data/curated/review/ and data/curated/search_terms.csv, and writes
data/build/standards.db. The old database is replaced, never updated in place
(decisions 0007, 0010).

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
SCHEMA_VERSION = "6"
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
PLACEHOLDER = re.compile(r"^\([^)]*\)( CA)?$")


def is_placeholder(text):
    """True for '(Begins in grade 2)' or '(Not applicable to literature)': the
    identifier is listed but there is no standard at this grade."""
    return bool(PLACEHOLDER.match(text.strip()))


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


def read_corrections(path):
    """{record_id: row} from data/curated/identifier_corrections.csv."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as f:
        return {int(r["record_id"]): r for r in csv.DictReader(f)}


SEARCH_TERM_COLUMNS = ["teacher_term", "standards_term", "subject", "evidence", "source", "reviewed"]


def read_search_terms(path):
    """Rows of data/curated/search_terms.csv, checked. Missing file: none."""
    if not path or not path.exists():
        return []
    # utf-8-sig reads the file with or without the marker Excel puts at the start
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != SEARCH_TERM_COLUMNS:
            raise LoadError(f"{path.name}: columns should be {', '.join(SEARCH_TERM_COLUMNS)}")
        rows, seen = [], set()
        for line, r in enumerate(reader, start=2):
            teacher = " ".join(r["teacher_term"].split()).lower()
            standards = " ".join(r["standards_term"].split()).lower()
            subject = r["subject"].strip().lower() or None
            if not teacher or not standards:
                raise LoadError(f"{path.name} line {line}: teacher_term and standards_term are both needed")
            if subject not in (None, "math", "ela", "eld"):
                raise LoadError(f"{path.name} line {line}: subject is {r['subject']!r}; "
                                "write math, ela, eld, or leave it blank")
            if r["reviewed"].strip() not in ("0", "1"):
                raise LoadError(f"{path.name} line {line}: reviewed is {r['reviewed']!r}; write 0 or 1")
            if not r["source"].strip():
                raise LoadError(f"{path.name} line {line}: source is empty")
            if (teacher, standards) in seen:
                raise LoadError(f"{path.name} line {line}: {teacher} -> {standards} is listed twice")
            seen.add((teacher, standards))
            rows.append((teacher, standards, subject, r["evidence"].strip(), r["source"].strip(),
                         int(r["reviewed"])))
    return rows


def read_records(path, subject, codes, corrections=None):
    """Turn one records file into (standards rows, sub-item rows, notes)."""
    corrections = corrections or {}
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
    notes = {"unparsed": [], "grade_mismatch": [], "corrected": []}
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
        corrected = None
        if int(record_id) in corrections:
            fix = corrections[int(record_id)]
            if fix["identifier"] != identifier:
                raise LoadError(f"{where}: identifier_corrections.csv expects record {record_id} "
                                f"to be {fix['identifier']!r}. The site may have changed; check it.")
            corrected = normalize_identifier(fix["corrected_identifier"])
            notes["corrected"].append((int(record_id), identifier, corrected))
        parts = parse_identifier(subject, corrected or identifier_norm)
        if parts is None:
            notes["unparsed"].append((int(record_id), identifier))
            parts = dict(strand=None, grade=None, number=None, letter=None, level=None, parent=None)
        elif parts["grade"] and parse_grade(parts["grade"]) != (grade_min, grade_max):
            notes["grade_mismatch"].append((int(record_id), identifier, grade_label))

        ca_marker, has_asterisk = flags(texts["text_standard"])
        standards.append((
            int(record_id), row["url"], subject, identifier, identifier_norm, corrected,
            grade_label, grade_min, grade_max,
            fields["subject_area"], fields["domain"], fields["cluster"], cluster_code, merged,
            fields["discipline"], fields["conceptual_category"], fields["critical_principle"],
            fields["proficiency_level"], fields["content_strand"],
            texts["text_cluster"] or None, texts["text_standard"], texts["text_footnote"] or None,
            searchable,
            int(parts["strand"] is not None), parts["strand"], parts["grade"], parts["number"],
            parts["letter"], parts["level"], parts["parent"],
            ca_marker, has_asterisk, int(is_placeholder(texts["text_standard"])),
            path.name, int(row["page"]), "cde", None,
        ))
        for letter, text in split_sub_items(texts["text_standard"])[1]:
            sub_items.append((int(record_id), letter, text, *flags(text)))
    return standards, sub_items, notes


# ---------- edges ----------

LEVELS = ("Em", "Ex", "Br")


def structural_edges(con):
    """Links the identifiers themselves imply (0005). Placeholders are skipped,
    so a chain runs past a grade where CDE lists '(Begins in grade 2)'."""
    edges = []
    rows = con.execute(
        "SELECT record_id, subject, id_strand, id_number, id_letter, id_level, grade_min "
        "FROM standards WHERE id_parsed = 1 AND is_placeholder = 0 AND subject IN ('ela', 'eld')"
    ).fetchall()

    # ELA: same strand and number, next grade that has one. L.4.1 -> L.5.1.
    ela = {}
    for rid, subject, strand, number, _, _, grade in rows:
        if subject == "ela":
            ela.setdefault((strand, number), []).append((grade, rid))
    for chain in ela.values():
        chain.sort()
        for (g1, a), (g2, b) in zip(chain, chain[1:]):
            if g1 < g2:
                edges.append((a, b, "next_grade", "structural", None, 0))

    # ELD: same part, number and level in the next grade. Lettering changes
    # between grades (PI.6 in grade 3 becomes PI.6a and PI.6b in grade 4). A
    # record links to the same letter where the earlier grade has it, and
    # otherwise to every record of that number in the earlier grade.
    eld, by_grade = {}, {}
    for rid, subject, part, number, letter, level, grade in rows:
        if subject == "eld":
            eld.setdefault((part, number, level), {}).setdefault(grade, []).append((letter, rid))
            by_grade.setdefault((part, number, letter, grade), {})[level] = rid
    for grades in eld.values():
        ordered = sorted(grades)
        for g1, g2 in zip(ordered, ordered[1:]):
            earlier = dict(grades[g1])
            for letter, rid in grades[g2]:
                if letter in earlier:
                    edges.append((earlier[letter], rid, "next_grade", "structural", None, 0))
                else:
                    for from_rid in earlier.values():
                        edges.append((from_rid, rid, "next_grade", "structural",
                                      "lettering differs between these grades", 0))
    # ELD: Emerging -> Expanding -> Bridging for the same standard in one grade.
    for levels in by_grade.values():
        for lower, higher in zip(LEVELS, LEVELS[1:]):
            if lower in levels and higher in levels:
                edges.append((levels[lower], levels[higher], "next_level", "structural", None, 0))
    return edges


def read_parents(path):
    """Rows of data/derived/learning_commons_parents.csv: parent standards that
    CDE lists only as their parts. Missing file: none."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def insert_parent(con, p, file_name):
    """Add one parent standard. Grade, domain and course are taken from its
    sub-item records, which must agree with each other."""
    kids = [int(k) for k in p["child_record_ids"].split()]
    marks = ",".join("?" * len(kids))
    facts = con.execute(
        "SELECT grade_label, grade_min, grade_max, domain, discipline, conceptual_category, "
        f"MIN(text_cluster), COUNT(*) FROM standards WHERE record_id IN ({marks}) "
        "GROUP BY 1, 2, 3, 4, 5, 6", kids).fetchall()
    if len(facts) != 1 or facts[0][7] != len(kids) or (facts[0][4] or "") != p["discipline"]:
        raise LoadError(f"{file_name}: the sub-item records of {p['identifier']} "
                        f"({p['child_record_ids']}) are missing or disagree on grade, domain "
                        "or course. Re-run scripts/join_learning_commons.py.")
    grade_label, grade_min, grade_max, domain, discipline, category, text_cluster, _ = facts[0]
    identifier_norm = normalize_identifier(p["identifier"])
    parts = parse_identifier("math", identifier_norm) or dict(
        strand=None, grade=None, number=None, letter=None, level=None, parent=None)
    ca_marker, has_asterisk = flags(p["text"])
    con.execute(
        "INSERT INTO standards (record_id, subject, identifier, identifier_norm, grade_label, "
        "grade_min, grade_max, domain, discipline, conceptual_category, text_cluster, "
        "text_standard, text_search, id_parsed, id_strand, id_grade, id_number, id_letter, "
        "id_level, parent_identifier_norm, ca_marker, has_asterisk, is_placeholder, "
        "source_file, origin) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (int(p["row_id"]), "math", p["identifier"], identifier_norm, grade_label, grade_min,
         grade_max, domain, discipline, category, text_cluster, p["text"],
         search_form(p["text"]), int(parts["strand"] is not None), parts["strand"],
         parts["grade"], parts["number"], parts["letter"], parts["level"], parts["parent"],
         ca_marker, has_asterisk, 0, file_name, "learning_commons"))


def read_eld_ela(path, known_ids):
    """Rows of data/derived/learning_commons_eld_ela.csv. Missing file: none."""
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        for line, r in enumerate(csv.DictReader(f), start=2):
            if int(r["ela_record_id"]) not in known_ids:
                raise LoadError(f"{path.name} line {line}: record {r['ela_record_id']} is not in "
                                "the records files. Re-run scripts/join_learning_commons.py.")
            rows.append((r["eld_part"], r["eld_number"], int(r["eld_grade_min"]),
                         int(r["eld_grade_max"]), int(r["ela_record_id"]), r["as_written"],
                         r["source"], int(r["reviewed"])))
    return rows


def read_imported_edges(path, known_ids):
    """Rows of data/derived/learning_commons_edges.csv, written by
    scripts/join_learning_commons.py. Missing file: no imported edges."""
    if not path.exists():
        return []
    edges = []
    with open(path, encoding="utf-8", newline="") as f:
        for line, r in enumerate(csv.DictReader(f), start=2):
            a, b = int(r["from_record_id"]), int(r["to_record_id"])
            if a not in known_ids or b not in known_ids:
                raise LoadError(f"{path.name} line {line}: record {a} or {b} is not in the "
                                "records files. Re-run scripts/join_learning_commons.py.")
            edges.append((a, b, r["type"], r["source"], r["note"] or None, int(r["reviewed"])))
    return edges


def read_components(derived_dir, known_ids):
    """(component rows, link rows) from data/derived/. Both files or neither."""
    if not derived_dir:
        return [], []
    comp_path = derived_dir / "learning_commons_components.csv"
    link_path = derived_dir / "learning_commons_component_links.csv"
    if not comp_path.exists() or not link_path.exists():
        return [], []
    with open(comp_path, encoding="utf-8", newline="") as f:
        comps = [(r["component_id"], r["subject"], r["text"], r["author"], r["source"])
                 for r in csv.DictReader(f)]
    links = []
    with open(link_path, encoding="utf-8", newline="") as f:
        for line, r in enumerate(csv.DictReader(f), start=2):
            if int(r["record_id"]) not in known_ids:
                raise LoadError(f"{link_path.name} line {line}: record {r['record_id']} is not "
                                "in the database. Re-run scripts/join_learning_commons.py.")
            links.append((int(r["record_id"]), r["letter"], r["component_id"], r["note"] or None,
                          r["source"], int(r["reviewed"])))
    return comps, links


def read_decisions(review_dir):
    """The owner's decisions on links, from the sheets in data/curated/review/.

    Returns (decisions, pending). A decision is (from, to, type, 'keep' or
    'reject', note, sheet name, confidence) and counts only where the row has
    reviewed = 1. confidence is 'low', 'medium', 'high' or None (left blank).
    pending counts rows with a decision written but reviewed still 0.
    """
    decisions, pending = [], 0
    if not review_dir or not review_dir.exists():
        return decisions, pending
    for path in sorted(review_dir.glob("*.csv")):
        # utf-8-sig reads the file with or without the marker Excel puts at the start
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if "from_record_id" not in (reader.fieldnames or []):
                continue                    # pairings and ELD notes: recorded, not applied here
            for line, r in enumerate(reader, start=2):
                decision = (r["decision"] or "").strip().lower()
                if (r["reviewed"] or "").strip() != "1":
                    pending += bool(decision)
                    continue
                if decision not in ("keep", "reject"):
                    raise LoadError(f"{path.name} line {line}: reviewed is 1 but decision is "
                                    f"{r['decision']!r}. Write keep or reject.")
                # .get: a sheet without the confidence column is read as all blank
                confidence = (r.get("confidence") or "").strip().lower() or None
                if confidence not in (None, "low", "medium", "high"):
                    raise LoadError(f"{path.name} line {line}: confidence is {r['confidence']!r}. "
                                    "Write low, medium or high, or leave it blank.")
                decisions.append((int(r["from_record_id"]), int(r["to_record_id"]), r["type"],
                                  decision, (r["owner_note"] or "").strip() or None, path.name,
                                  confidence))
    return decisions, pending


def apply_decisions(con, decisions):
    """keep: mark the link reviewed, adding it if it is not there (a candidate
    the owner accepted). reject: leave the link out."""
    kept = added = rejected = 0
    for a, b, kind, decision, note, sheet, confidence in decisions:
        where = "from_record_id = ? AND to_record_id = ? AND type = ?"
        present = con.execute(f"SELECT COUNT(*) FROM edges WHERE {where}", (a, b, kind)).fetchone()[0]
        if decision == "reject":
            con.execute(f"DELETE FROM edges WHERE {where}", (a, b, kind))
            rejected += 1
        elif present:
            con.execute(f"UPDATE edges SET reviewed = 1, confidence = ? WHERE {where}",
                        (confidence, a, b, kind))
            kept += 1
        else:
            try:
                con.execute("INSERT INTO edges VALUES (?, ?, ?, 'owner', ?, 1, ?)",
                            (a, b, kind, note, confidence))
            except sqlite3.IntegrityError:
                raise LoadError(f"{sheet}: record {a} or {b} is not in the database.") from None
            added += 1
    return {"kept": kept, "added": added, "rejected": rejected}


# ---------- building the database ----------

def build(raw_dir, codes_path, schema_path, db_path, corrections_path=None, edges_path=None,
          parents_path=None, eld_ela_path=None, review_dir=None, components_dir=None,
          search_terms_path=None):
    """Read everything, then write the database. Returns a summary dict."""
    search_terms = read_search_terms(search_terms_path)
    codes = read_codes(codes_path)
    corrections = read_corrections(corrections_path) if corrections_path else {}
    loaded, summary = [], {"subjects": {}, "unparsed": [], "grade_mismatch": [], "corrected": []}
    seen = {}
    for subject in SUBJECTS:
        path = newest_records_file(raw_dir, subject)
        standards, sub_items, notes = read_records(path, subject, codes, corrections)
        for row in standards:
            if row[0] in seen:
                raise LoadError(f"record ID {row[0]} appears twice: {seen[row[0]]} and {path.name}")
            seen[row[0]] = path.name
        loaded.append((subject, path, standards, sub_items))
        summary["subjects"][subject] = {"file": path.name, "records": len(standards),
                                        "sub_items": len(sub_items)}
        summary["unparsed"] += notes["unparsed"]
        summary["grade_mismatch"] += notes["grade_mismatch"]
        summary["corrected"] += notes["corrected"]
    unknown = set(corrections) - set(seen)
    if unknown:
        raise LoadError(f"identifier_corrections.csv names records that are not in the "
                        f"records files: {sorted(unknown)}")
    parents = read_parents(parents_path) if parents_path else []
    known_ids = set(seen) | {int(p["row_id"]) for p in parents}
    imported = read_imported_edges(edges_path, known_ids) if edges_path else []
    eld_ela = read_eld_ela(eld_ela_path, known_ids) if eld_ela_path else []
    decisions, pending = read_decisions(review_dir)
    components, component_links = read_components(components_dir, known_ids)

    # Build into a temporary file and swap it in at the end, so a failure
    # part-way never leaves a half-written standards.db behind.
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = db_path.with_name(db_path.name + ".tmp")
    tmp_path.unlink(missing_ok=True)
    con = sqlite3.connect(tmp_path)
    con.execute("PRAGMA foreign_keys = ON")     # refuse a link to a record that does not exist
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
            con.executemany(f"INSERT INTO standards VALUES ({','.join('?' * 37)})", standards)
            con.executemany("INSERT INTO sub_items VALUES (?, ?, ?, ?, ?)", sub_items)
        for p in parents:
            insert_parent(con, p, parents_path.name)
        # Point each math sub-item record at its parent's row, in the same course.
        con.execute(
            "UPDATE standards SET parent_record_id = ("
            "  SELECT p.record_id FROM standards p WHERE p.subject = 'math' "
            "  AND p.identifier_norm = standards.parent_identifier_norm "
            "  AND COALESCE(p.discipline, '') = COALESCE(standards.discipline, '') "
            "  ORDER BY p.record_id DESC LIMIT 1) "
            "WHERE parent_identifier_norm IS NOT NULL")
        summary["added_parents"] = len(parents)
        summary["sub_items_without_parent"] = con.execute(
            "SELECT COUNT(*) FROM standards WHERE parent_identifier_norm IS NOT NULL "
            "AND parent_record_id IS NULL").fetchone()[0]
        con.executemany("INSERT INTO identifier_corrections VALUES (?, ?, ?, ?, ?, ?)",
                        [(rid, r["identifier"], r["corrected_identifier"], r["evidence"],
                          r["source"], int(r["reviewed"])) for rid, r in sorted(corrections.items())])
        con.executemany("INSERT INTO eld_ela_links VALUES (?, ?, ?, ?, ?, ?, ?, ?)", eld_ela)
        summary["eld_ela_links"] = len(eld_ela)
        edges = structural_edges(con) + imported
        con.executemany("INSERT INTO edges (from_record_id, to_record_id, type, source, note, reviewed) "
                        "VALUES (?, ?, ?, ?, ?, ?)", edges)
        con.executemany("INSERT INTO learning_components VALUES (?, ?, ?, ?, ?)", components)
        con.executemany("INSERT INTO component_links VALUES (?, ?, ?, ?, ?, ?)", component_links)
        summary["components"] = (len(components), len(component_links))
        con.executemany("INSERT INTO search_terms VALUES (?, ?, ?, ?, ?, ?)", search_terms)
        summary["search_terms"] = (len(search_terms), sum(r[5] for r in search_terms))
        summary["decisions"] = apply_decisions(con, decisions)
        summary["decisions"]["pending"] = pending
        summary["edges"] = con.execute(
            "SELECT type, source, COUNT(*) FROM edges GROUP BY 1, 2 ORDER BY 1, 2").fetchall()
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
        summary = build(args.raw, args.codes, ROOT / "src" / "schema.sql", args.db,
                        ROOT / "data" / "curated" / "identifier_corrections.csv",
                        ROOT / "data" / "derived" / "learning_commons_edges.csv",
                        ROOT / "data" / "derived" / "learning_commons_parents.csv",
                        ROOT / "data" / "derived" / "learning_commons_eld_ela.csv",
                        ROOT / "data" / "curated" / "review",
                        ROOT / "data" / "derived",
                        ROOT / "data" / "curated" / "search_terms.csv")
    except LoadError as e:
        sys.exit(f"Load stopped, database not changed.\n  {e}")

    for subject, s in summary["subjects"].items():
        print(f"{subject:5} {s['records']:4} records, {s['sub_items']:3} sub-items   from {s['file']}")
    print(f"\nidentifiers read through a correction: {len(summary['corrected'])}")
    for record_id, identifier, corrected in summary["corrected"]:
        print(f"  record {record_id}: {identifier} read as {corrected}")
    print(f"identifiers the loader could not split into parts: {len(summary['unparsed'])}")
    for record_id, identifier in summary["unparsed"]:
        print(f"  record {record_id}: {identifier}")
    print(f"grade in the identifier differs from the Grade field: {len(summary['grade_mismatch'])}")
    for record_id, identifier, grade in summary["grade_mismatch"]:
        print(f"  record {record_id}: {identifier} has Grade {grade}")
    print(f"\nparent standards added from Learning Commons (CDE has no record): "
          f"{summary['added_parents']}")
    print(f"math sub-item records with no parent row: {summary['sub_items_without_parent']}")
    print(f"ELA standards listed against ELD standards: {summary['eld_ela_links']}")
    print(f"learning components: {summary['components'][0]}, attached in "
          f"{summary['components'][1]} places")
    print(f"search terms (teacher wording -> standards wording): {summary['search_terms'][0]}, "
          f"{summary['search_terms'][1]} reviewed")
    print("\nedges:")
    for kind, source, n in summary["edges"]:
        print(f"  {n:5}  {kind} ({source})")
    d = summary["decisions"]
    print(f"\nowner's decisions applied: {d['kept']} links marked reviewed, {d['added']} added, "
          f"{d['rejected']} left out")
    if d["pending"]:
        print(f"  {d['pending']} rows have a decision written but reviewed is still 0; not applied")
    print(f"\nWrote {args.db}")


if __name__ == "__main__":
    main()
