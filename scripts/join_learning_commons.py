#!/usr/bin/env python3
"""
join_learning_commons.py - find, for every CDE record, the matching item in the
Learning Commons Knowledge Graph, and write the pairs to a mapping file.

    python src/load.py                          # first: build the database
    python scripts/join_learning_commons.py     # then: write the mapping

Why: Learning Commons publishes prerequisite links, learning components and
parent standards, all attached to its own item IDs. To use any of them we need
to know which of its items is which CDE record.

Where the Learning Commons files are: by default the folder "learning_commons"
beside this repo, holding open-knowledge-graph/nodes.jsonl and
relationships.jsonl. To use another place, put this line in local_config.toml
in the project root (the file is not committed), or pass --lc:
    learning_commons_dir = "D:/somewhere/learning_commons"

How records are paired. The code decides; the text only confirms.
  math   Learning Commons writes 3.NF.A.2 and HSA-CED.A.1 where CDE writes
         3.NF.2 and A-CED.1. Its codes are rewritten to CDE's form. High school
         standards are paired within the same course.
  ela    Codes are the same. Lettered sub-items (L.5.1.b) pair with the lettered
         lines the loader split out of the record's text.
  eld    Learning Commons has one item per standard (ELD.4.I.C.12) where CDE has
         one record per letter and proficiency level, so several records share
         an item. Built from the record's grade, part, cluster and number.
  text   A record whose code finds nothing is paired with an item of the same
         grade or course whose text is the same. This is how CDE's malformed
         identifiers (RL.2..2) get a match.

Nothing is guessed: a record with no match gets a row saying so.

It then brings in the math "builds towards" links (the Student Achievement
Partners coherence map). Those links join Common Core standards, so each end is
followed from the Common Core item to the California item Learning Commons
rates as the same (jaccard 1.0), and from there to the CDE record.

Some standards have no CDE record: CDE lists 4.NF.3.a, b, c and d but not
4.NF.3 itself. Learning Commons has the parent, so it is written to
learning_commons_parents.csv and the loader adds it as a row of its own. A
link that Learning Commons publishes to or from 4.NF.3 then stays one link, on
the parent. Copying it onto every sub-item would state pairs nobody published;
those pairs are listed in learning_commons_spread_candidates.csv for the owner
to look at, and are not loaded.

High school standards are one record per course, so a link has to choose which
course copies to join. The rule (owner's decision, 2026-11-14) is "same
pathway": copies are joined within Algebra I / Geometry / Algebra II and within
Math I / II / III, never across the two. Each later standard is linked from the
nearest copy of the earlier standard at or before its own course. A K-8
standard, having one record, links to every course copy. The course
"Statistics and Probability" is treated as following either pathway.

Last, it reads the ELA standards listed against each ELD standard. Every
California ELD item in Learning Commons has a note such as
"W.4.4–5; SL.4.4, 6; L.4.1, 3, 5–6". Each note is split into single ELA
standards and each is matched to its CDE record. The note belongs to the ELD
standard as a whole (ELD Part I, grade 4, standard 12), not to one proficiency
level or letter, and it is written out that way.

Writes to data/derived/:
  learning_commons_map.csv               one row per pairing (or per unmatched record)
  learning_commons_unmapped.csv          California items no CDE record pairs with
  learning_commons_parents.csv           parent standards CDE has no record for; the loader reads this
  learning_commons_edges.csv             builds-towards links between rows; the loader reads this
  learning_commons_spread_candidates.csv sub-item pairs a link to a parent could also mean; not loaded
  learning_commons_edges_unresolved.csv  links not written, and why
  learning_commons_eld_ela.csv           ELA standards listed against each ELD standard; the loader reads this
  learning_commons_eld_ela_unresolved.csv  pieces of those notes that matched no ELA record
  learning_commons_source.json           which Learning Commons files were read
"""
import argparse
import csv
import difflib
import hashlib
import json
import re
import sqlite3
import sys
import tomllib      # reads .toml settings files; part of Python since 3.11
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from load import split_sub_items, normalize_identifier, parse_grade  # noqa: E402

SUBJECTS = {"Mathematics": "math", "English Language Arts": "ela",
            "English Language Development": "eld"}
# Learning Commons course name -> CDE Discipline.
COURSES = {
    "Algebra I": "Algebra I", "Algebra II": "Algebra II", "Geometry": "Geometry",
    "Mathematics I": "Math I", "Mathematics II": "Math II", "Mathematics III": "Math III",
    "Calculus Standards": "Calculus",
    "Advanced Placement Probability and Statistics Standards": "Statistics and Probability (AP)",
}
COURSE_CODE_PREFIX = {"Calculus": "Calculus.", "Statistics and Probability (AP)": "AP-Prob&Stats."}
SAME_TEXT = 0.97      # similarity at or above this counts as the same text


def loose(text):
    """Letters and digits only, lower case. Hides differences in dashes, quotes,
    spacing and math markup, which the two sources write differently."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def similarity(a, b):
    """0.0 to 1.0: how alike two texts are after loose()."""
    a, b = loose(a), loose(b)
    if not a or not b:
        return 0.0
    return 1.0 if a == b else difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def text_check(a, b):
    """('same' | 'one contains the other' | 'differs', similarity).

    'one contains the other' is the usual case when texts are not the same: CDE
    repeats the parent standard's sentence in front of a sub-item, and one side
    or the other leaves out the worked examples.
    """
    sim = similarity(a, b)
    if sim >= SAME_TEXT:
        return "same", sim
    la, lb = loose(a), loose(b)
    if la and lb and (la in lb or lb in la):
        return "one contains the other", sim
    return "differs", sim


def cde_form(code, course):
    """Rewrite a Learning Commons math code the way CDE writes it.

    3.NF.A.2 -> 3.NF.2     HSA-CED.A.1 -> A-CED.1     17.0 (Calculus) -> Calculus.17.0
    The dropped piece is the cluster letter, which CDE leaves out.
    """
    if course in COURSE_CODE_PREFIX and re.fullmatch(r"\d+\.\d+", code):
        return COURSE_CODE_PREFIX[course] + code
    # High school codes start HS and join category and domain with a hyphen
    # (HSA-CED). California's own additions are written with a dot (HSF.LE.A.4.1).
    hs = re.match(r"HS([A-Z])[-.]([A-Z]+)(\..*)", code)
    high_school = bool(hs)
    if high_school:
        code = f"{hs[1]}-{hs[2]}{hs[3]}"
    parts = code.split(".")
    before = 1 if high_school else 2          # pieces before the cluster letter: [grade,] domain
    if (len(parts) > before + 1 and re.fullmatch(r"[A-Z]", parts[before])
            and parts[before + 1].isdigit()):
        del parts[before]
    return ".".join(parts)


# ---------- reading Learning Commons ----------

def find_lc_dir(arg):
    if arg:
        return Path(arg)
    config = ROOT / "local_config.toml"
    if config.exists():
        with open(config, "rb") as f:
            value = tomllib.load(f).get("learning_commons_dir")
        if value:
            return Path(value)
    return ROOT.parent / "learning_commons"


def read_california_items(graph_dir):
    """California math, ELA and ELD items, each with its code, type, course and parent."""
    nodes, rels = graph_dir / "nodes.jsonl", graph_dir / "relationships.jsonl"
    for p in (nodes, rels):
        if not p.exists():
            sys.exit(f"Cannot find {p}\nSee the top of this script for where the "
                     "Learning Commons files go.")
    items, frameworks, ccss = {}, set(), {}
    with open(nodes, encoding="utf-8") as f:
        for line in f:
            # cheap test before the slower json.loads
            if '"California"' not in line and '"Multi-State"' not in line:
                continue
            node = json.loads(line)
            p = node["properties"]
            if (p.get("jurisdiction") == "Multi-State" and p.get("academicSubject") == "Mathematics"
                    and "StandardsFrameworkItem" in node["labels"]):
                ccss[node["identifier"]] = (p.get("statementCode") or "").strip()
                continue
            if p.get("jurisdiction") != "California":
                continue
            if "StandardsFramework" in node["labels"]:
                frameworks.add(node["identifier"])
            elif "StandardsFrameworkItem" in node["labels"] and p.get("academicSubject") in SUBJECTS:
                items[node["identifier"]] = {
                    "lc_identifier": node["identifier"],
                    "case_uuid": p.get("caseIdentifierUUID") or "",
                    "subject": SUBJECTS[p["academicSubject"]],
                    "code": normalize_identifier((p.get("statementCode") or "").strip()),
                    "type": p.get("statementType") or "",
                    "grades": json.loads(p.get("gradeLevel") or "[]"),
                    "text": p.get("description") or "",
                    "notes": (p.get("notes") or "").strip(),
                }
    parent, builds, same_as = {}, [], defaultdict(list)
    with open(rels, encoding="utf-8") as f:
        for line in f:
            if "hasChild" not in line and "buildsTowards" not in line \
                    and "hasStandardAlignment" not in line:
                continue
            rel = json.loads(line)
            a, b = rel["source_identifier"], rel["target_identifier"]
            if rel["label"] == "hasChild" and b in items:
                parent[b] = a
            elif rel["label"] == "buildsTowards" and a in ccss and b in ccss:
                builds.append((a, b, rel["identifier"]))
            elif (rel["label"] == "hasStandardAlignment" and a in items and b in ccss
                  and rel["properties"].get("jaccard") == "1.0"):
                same_as[b].append(a)        # Common Core item -> California items
    for key, item in items.items():
        item["parent_code"] = items.get(parent.get(key), {}).get("code", "")
        item["course"] = ""
        up = parent.get(key)
        while up in items:                         # walk up to the course, if any
            if items[up]["type"] == "Course":
                item["course"] = COURSES.get(items[up]["text"], items[up]["text"])
                break
            up = parent.get(up)
    children = defaultdict(list)
    for child, up in parent.items():
        children[up].append(child)
    graph = {"ccss": ccss, "builds": builds, "same_as": same_as, "children": children}
    return items, graph, nodes, rels


# ---------- builds-towards links ----------

# Where each course sits. K-8 records have no course ("") and come before all.
PATHWAYS = {
    "": ("traditional", "integrated"),
    "Algebra I": ("traditional",), "Geometry": ("traditional",), "Algebra II": ("traditional",),
    "Math I": ("integrated",), "Math II": ("integrated",), "Math III": ("integrated",),
    "Statistics and Probability": ("traditional", "integrated"),
}
COURSE_ORDER = {"": 0, "Algebra I": 1, "Math I": 1, "Geometry": 2, "Math II": 2,
                "Algebra II": 3, "Math III": 3, "Statistics and Probability": 4}


def pathway_pairs(from_records, to_records):
    """Which (from, to) record pairs a link becomes. Each argument is a dict
    {record_id: course}. See the top of this file for the rule."""
    pairs = set()
    for b, course_b in to_records.items():
        for pathway in PATHWAYS[course_b]:
            earlier = {a: COURSE_ORDER[c] for a, c in from_records.items()
                       if pathway in PATHWAYS[c] and COURSE_ORDER[c] <= COURSE_ORDER[course_b]}
            if earlier:
                nearest = max(earlier.values())
                pairs |= {(a, b) for a, order in earlier.items() if order == nearest and a != b}
    return pairs


def plain_math(text):
    """Learning Commons writes some fractions as LaTeX, a typesetting notation:
    $\\frac{a}{b}$. CDE writes a/b. This turns the first into the second."""
    return re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"\1/\2", text).replace("$", "")


# \s? allows the one note written with a stray space: "WHST. 9-10.4-5".
NOTE_SEGMENT = re.compile(r"^([A-Z]+)\.\s?(K|\d+(?:-\d+)?)\.(.+)$")
LC_ELD_CODE = re.compile(r"^ELD\.(K|\d+(?:-\d+)?)\.(I|II)\.[A-Z]\.(\d+)$")


def parse_note(note):
    """'W.4.4-5; SL.4.4, 6' -> [('W','4','4',seg), ('W','4','5',seg), ('SL','4','4',seg), ...]
    plus a list of segments that could not be read."""
    found, unread = [], []
    for segment in normalize_identifier(note).split(";"):
        segment = segment.strip()
        m = NOTE_SEGMENT.match(segment)
        if not segment:
            continue
        if not m:
            unread.append(segment)
            continue
        numbers = []
        for piece in m[3].split(","):
            r = re.fullmatch(r"(\d+)(?:-(\d+))?", piece.strip())
            if not r or int(r[2] or r[1]) < int(r[1]):
                numbers = None
                break
            numbers += range(int(r[1]), int(r[2] or r[1]) + 1)
        if numbers is None:
            unread.append(segment)
        else:
            found += [(m[1], m[2], str(n), segment) for n in numbers]
    return found, unread


def eld_ela_rows(items, records):
    """Returns (rows for learning_commons_eld_ela.csv, unresolved rows)."""
    ela = defaultdict(list)                 # (strand, number) -> ELA records
    for r in records:
        if r["subject"] == "ela" and r["id_parsed"]:
            ela[(r["id_strand"], r["id_number"])].append(r)
    rows, unresolved = [], []
    for item in sorted(items.values(), key=lambda i: i["code"]):
        m = LC_ELD_CODE.match(item["code"]) if item["subject"] == "eld" else None
        if not m or item["type"] != "Standard":
            continue
        grade_min, grade_max = parse_grade(m[1])
        found, unread = parse_note(item["notes"])
        for segment in unread:
            unresolved.append([item["code"], segment, "cannot read this piece of the note"])
        seen = set()
        for strand, grade, number, segment in found:
            lo, hi = parse_grade(grade)
            # RH, RST and WHST are written "RH.6.1" in the notes but are one
            # record for grades 6-8, so match on the grade falling inside the record's range.
            hits = [r for r in ela[(strand, number)] if r["grade_min"] <= lo and hi <= r["grade_max"]]
            if len(hits) != 1:
                unresolved.append([item["code"], segment,
                                   f"{strand}.{grade}.{number}: {len(hits)} ELA records match"])
                continue
            r = hits[0]
            if r["record_id"] in seen:
                continue
            seen.add(r["record_id"])
            rows.append(["P" + m[2], m[3], m[1], grade_min, grade_max, r["record_id"],
                         r["identifier"], r["is_placeholder"], segment, item["code"],
                         item["case_uuid"], item["lc_identifier"], "learning_commons_notes", 0])
    return rows, unresolved


def math_records_of(rows):
    """Learning Commons identifier -> CDE record IDs, and record ID -> (identifier, course)."""
    records_of, info = defaultdict(set), {}
    for r in rows:
        if r[2] == "math" and r[1] == "" and r[6]:
            records_of[r[6]].add(r[0])
            info[r[0]] = (r[3], r[4])
    return records_of, info


def build_parents(rows, items, graph, records):
    """Parent standards that have no CDE record but whose sub-items do.

    Returns (rows for learning_commons_parents.csv,
             {Learning Commons identifier: {row_id: course}}).
    The row_id is negative and worked out from the Learning Commons identifier
    and the course, so it is the same every time the script runs.
    """
    rec = {r["record_id"]: r for r in records if r["subject"] == "math"}
    records_of, _ = math_records_of(rows)
    existing = {(r["join_identifier"], r["discipline"] or "") for r in rec.values()}
    parents, parent_ids, taken = [], defaultdict(dict), set()
    for item in sorted(items.values(), key=lambda i: i["lc_identifier"]):
        if item["subject"] != "math" or item["type"] != "Standard" or records_of[item["lc_identifier"]]:
            continue
        identifier = cde_form(item["code"], item["course"])
        by_course = defaultdict(list)
        for child in graph["children"].get(item["lc_identifier"], []):
            for k in records_of[child]:
                if rec[k]["parent_identifier_norm"] == identifier:
                    by_course[rec[k]["discipline"] or ""].append(k)
        for course, kids in sorted(by_course.items()):
            kids = sorted(set(kids))
            if (identifier, course) in existing or len({rec[k]["grade_label"] for k in kids}) != 1:
                continue
            digest = hashlib.sha256(f"{item['lc_identifier']}|{course}".encode()).hexdigest()
            row_id = -int(digest[:7], 16)
            if row_id in taken:
                sys.exit(f"Two parent standards came out with the same row_id {row_id}.")
            taken.add(row_id)
            parents.append([row_id, "math", identifier, course, rec[kids[0]]["grade_label"],
                            plain_math(item["text"]), " ".join(map(str, kids)), item["case_uuid"],
                            item["lc_identifier"], item["code"], "learning_commons", 0])
            parent_ids[item["lc_identifier"]][row_id] = course
    return sorted(parents, key=lambda r: (r[3], r[2])), parent_ids


def import_edges(rows, items, graph, parents, parent_ids):
    """Returns (edge rows, unresolved rows, spread-candidate rows)."""
    records_of, info = math_records_of(rows)
    for parent in parents:
        info[parent[0]] = (parent[2], parent[3])
    copies = defaultdict(list)              # code -> every California math item with that code
    for item in items.values():
        if item["subject"] == "math" and item["code"]:
            copies[item["code"]].append(item["lc_identifier"])

    def resolve(ccss_id, use_parents):
        """({row_id: course}, note, problem, True if a parent row was used)."""
        ca_items = graph["same_as"].get(ccss_id, [])
        if not ca_items:
            return {}, "", "no California item rated the same (jaccard 1.0)", False
        # Learning Commons rates one copy of a high school standard against
        # Common Core; the per-course copies carry the same code.
        every_copy = {c for item in ca_items for c in copies[items[item]["code"]]} | set(ca_items)
        found, note, used_parent = set(), "", False
        for item in every_copy:
            if records_of[item]:
                found |= records_of[item]
            elif parent_ids.get(item):
                used_parent = True
                if use_parents:
                    found |= set(parent_ids[item])
                else:
                    for row_id in parent_ids[item]:
                        found |= {int(k) for p in parents if p[0] == row_id for k in p[6].split()}
            else:                           # no record and no parent row: fall back to sub-items
                kids = set()
                for child in graph["children"].get(item, []):
                    kids |= records_of[child]
                if kids:
                    found |= kids
                    note = "parent standard has no row; linked through its sub-items"
        if not found:
            return {}, "", "the California item has no CDE record", False
        outside = sorted({info[r][1] for r in found} - set(PATHWAYS))
        if outside:
            return {}, "", f"course not placed in a pathway: {', '.join(outside)}", False
        return {r: info[r][1] for r in found}, note, "", used_parent

    edges, unresolved, candidates, seen = [], [], [], set()
    for a, b, rel_id in graph["builds"]:
        code_a, code_b = graph["ccss"][a], graph["ccss"][b]
        from_rows, note_a, problem_a, parent_a = resolve(a, True)
        to_rows, note_b, problem_b, parent_b = resolve(b, True)
        if problem_a or problem_b:
            unresolved.append([code_a, code_b, problem_a, problem_b, rel_id])
            continue
        pairs = pathway_pairs(from_rows, to_rows)
        if not pairs:
            unresolved.append([code_a, code_b, "no copy at or before the later standard's "
                               "course in the same pathway", "", rel_id])
            continue
        high_school = any(from_rows.values()) or any(to_rows.values())
        note = "; ".join(dict.fromkeys(n for n in (
            note_a, note_b, "high school: course copies joined within the same pathway"
            if high_school else "") if n))
        for x, y in sorted(pairs):
            if (x, y) not in seen:
                seen.add((x, y))
                edges.append([x, y, "builds_towards", "learning_commons", note, 0,
                              info[x][0], info[y][0], code_a, code_b, rel_id])
        if parent_a or parent_b:            # what copying onto sub-items would have produced
            spread = pathway_pairs(resolve(a, False)[0], resolve(b, False)[0])
            for x, y in sorted(spread - pairs):
                candidates.append([rel_id, code_a, code_b, x, info[x][0], info[x][1],
                                   y, info[y][0], info[y][1]])
    return edges, unresolved, candidates


# ---------- pairing ----------

def grade_label_norm(label):
    return normalize_identifier(label)


def item_grade_label(item):
    g = item["grades"]
    return g[0] if len(g) == 1 else (f"{g[0]}-{g[-1]}" if g else "")


def pair(records, sub_items, items):
    """Returns (mapping rows, set of Learning Commons identifiers that were used)."""
    standards = [i for i in items.values() if i["type"] in ("Standard", "Component")]
    by_code = defaultdict(list)
    for item in standards:
        code = cde_form(item["code"], item["course"]) if item["subject"] == "math" else item["code"]
        by_code[(item["subject"], code)].append(item)

    rows, used = [], set()

    def add(rec, letter, item, match, check):
        used.add(item["lc_identifier"])
        verdict, sim = check or ("not compared", None)
        rows.append([rec["record_id"], letter, rec["subject"], rec["identifier"],
                     rec["discipline"] or "", item["case_uuid"], item["lc_identifier"],
                     item["code"], item["type"], item["course"], match, verdict,
                     "" if sim is None else f"{sim:.2f}", "learning_commons", 0])

    def none(rec, letter, why):
        rows.append([rec["record_id"], letter, rec["subject"], rec["identifier"],
                     rec["discipline"] or "", "", "", "", "", "", f"none: {why}", "", "",
                     "learning_commons", 0])

    def text_fallback(rec, text):
        """An item with the same text, in the same grade (or the same course)."""
        best, best_sim = None, 0.0
        for item in standards:
            if item["subject"] != rec["subject"]:
                continue
            if rec["discipline"]:
                if item["course"] != rec["discipline"]:
                    continue
            elif item_grade_label(item) != grade_label_norm(rec["grade_label"]):
                continue
            sim = similarity(text, item["text"])
            if sim > best_sim:
                best, best_sim = item, sim
        return (best, best_sim) if best_sim >= SAME_TEXT else (None, best_sim)

    for rec in records:
        subject = rec["subject"]
        stem, _ = split_sub_items(rec["text_standard"])
        letters = sub_items.get(rec["record_id"], [])
        text = stem if letters else rec["text_standard"]

        if subject == "eld":
            pair_eld(rec, by_code, add, none)
            continue

        candidates = by_code.get((subject, rec["join_identifier"]), [])
        match = "code"
        if subject == "math" and rec["discipline"]:
            in_course = [c for c in candidates if c["course"] == rec["discipline"]]
            generic = [c for c in candidates if not c["course"]]
            if in_course:
                candidates, match = in_course, "code and course"
            elif generic:
                candidates, match = generic, "code; no copy for this course"
            else:
                candidates = []

        scored = [(text_check(text, c["text"]), c) for c in candidates]
        # CDE repeats Calculus.16.0 for two different standards. If the code's
        # item has plainly different text, look for the item whose text matches.
        if not any(check[0] != "differs" or check[1] >= 0.5 for check, _ in scored):
            item, sim = text_fallback(rec, text)
            if item:
                add(rec, "", item, "text; code differs", ("same", sim))
            elif scored:
                for check, c in scored:
                    add(rec, "", c, match, check)
            else:
                none(rec, "", "no item has this code"
                     + (" or this text" if not rec["text_standard"].startswith("(") else
                        "; the record is a placeholder, not a standard"))
                continue
        else:
            for check, c in scored:
                add(rec, "", c, match, check)

        # Lettered sub-items inside the record's text (ELA).
        matched_code = rows[-1][7]
        for letter, sub_text in letters:
            subs = [c for c in by_code.get((subject, f"{matched_code}.{letter}"), [])]
            if subs:
                for c in subs:
                    add(rec, letter, c, "code", text_check(sub_text, c["text"]))
            else:
                none(rec, letter, "no item has this code")
    return rows, used


ELD_NUMBER = re.compile(r"\.(\d+)[a-z]?\.(?:Em|Ex|Br)$")


def pair_eld(rec, by_code, add, none):
    part = {"Part I": "I", "Part II": "II"}.get((rec["critical_principle"] or "").split(":")[0])
    cluster = (rec["cluster"] or "")[:1]
    number = ELD_NUMBER.search(rec["join_identifier"])
    if not (part and cluster and number):
        none(rec, "", "cannot read part, cluster or number from the record")
        return
    code = f"ELD.{grade_label_norm(rec['grade_label'])}.{part}.{cluster}.{number[1]}"
    candidates = by_code.get(("eld", code), [])
    if not candidates:
        none(rec, "", f"no item has the code {code}")
    for c in candidates:
        # The item's text is the strand's name, not the level's wording, and CDE
        # abbreviates strand names, so there is no text to confirm against.
        add(rec, "", c, "code built from grade, part, cluster, number; item covers all levels", None)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lc", help="Learning Commons folder (default: see above)")
    ap.add_argument("--db", type=Path, default=ROOT / "data" / "build" / "standards.db")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "derived")
    args = ap.parse_args()

    if not args.db.exists():
        sys.exit(f"{args.db} does not exist. Run: python src/load.py")
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row       # lets rows be read by column name
    # join_identifier: the corrected identifier where CDE's own is wrong.
    # origin = 'cde' leaves out parent rows an earlier run of this script supplied.
    records = con.execute(
        "SELECT *, COALESCE(identifier_corrected, identifier_norm) AS join_identifier "
        "FROM standards WHERE origin = 'cde' ORDER BY subject, record_id").fetchall()
    sub_items = defaultdict(list)
    for r in con.execute("SELECT record_id, letter, text FROM sub_items ORDER BY record_id, letter"):
        sub_items[r["record_id"]].append((r["letter"], r["text"]))
    con.close()

    graph_dir = find_lc_dir(args.lc) / "open-knowledge-graph"
    print(f"reading {graph_dir} (two large files; about a minute) ...")
    items, graph, nodes_path, rels_path = read_california_items(graph_dir)
    rows, used = pair(records, sub_items, items)
    parents, parent_ids = build_parents(rows, items, graph, records)
    edges, unresolved, candidates = import_edges(rows, items, graph, parents, parent_ids)
    eld_ela, eld_ela_unresolved = eld_ela_rows(items, records)

    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "learning_commons_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["record_id", "letter", "subject", "identifier", "discipline", "lc_case_uuid",
                    "lc_identifier", "lc_statement_code", "lc_statement_type", "lc_course",
                    "match", "text_check", "text_similarity", "source", "reviewed"])
        w.writerows(rows)
    unmapped = sorted((i for i in items.values()
                       if i["type"] in ("Standard", "Component") and i["lc_identifier"] not in used),
                      key=lambda i: (i["subject"], i["course"], i["code"], i["lc_identifier"]))
    with open(args.out / "learning_commons_unmapped.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["subject", "lc_statement_code", "lc_statement_type", "lc_course", "grades",
                    "lc_parent_code", "lc_case_uuid", "lc_identifier"])
        for i in unmapped:
            w.writerow([i["subject"], i["code"], i["type"], i["course"], " ".join(i["grades"]),
                        i["parent_code"], i["case_uuid"], i["lc_identifier"]])
    with open(args.out / "learning_commons_eld_ela.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["eld_part", "eld_number", "eld_grade_label", "eld_grade_min", "eld_grade_max",
                    "ela_record_id", "ela_identifier", "ela_is_placeholder", "as_written",
                    "lc_statement_code", "lc_case_uuid", "lc_identifier", "source", "reviewed"])
        w.writerows(eld_ela)
    with open(args.out / "learning_commons_eld_ela_unresolved.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["lc_statement_code", "as_written", "problem"])
        w.writerows(eld_ela_unresolved)
    with open(args.out / "learning_commons_parents.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["row_id", "subject", "identifier", "discipline", "grade_label", "text",
                    "child_record_ids", "lc_case_uuid", "lc_identifier", "lc_statement_code",
                    "source", "reviewed"])
        w.writerows(parents)
    with open(args.out / "learning_commons_spread_candidates.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["lc_relationship_id", "published_from", "published_to", "from_record_id",
                    "from_identifier", "from_discipline", "to_record_id", "to_identifier",
                    "to_discipline"])
        w.writerows(sorted(candidates, key=lambda c: (c[1], c[2], c[3], c[6])))
    with open(args.out / "learning_commons_edges.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["from_record_id", "to_record_id", "type", "source", "note", "reviewed",
                    "from_identifier", "to_identifier", "lc_from_code", "lc_to_code",
                    "lc_relationship_id"])
        w.writerows(sorted(edges, key=lambda e: (e[0], e[1])))
    with open(args.out / "learning_commons_edges_unresolved.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["lc_from_code", "lc_to_code", "from_problem", "to_problem",
                    "lc_relationship_id"])
        w.writerows(sorted(unresolved))
    source = {p.name: {"bytes": p.stat().st_size} for p in (nodes_path, rels_path)}
    source["nodes.jsonl"]["sha256"] = hashlib.sha256(nodes_path.read_bytes()).hexdigest()
    source["note"] = ("Learning Commons Knowledge Graph, open-knowledge-graph export. "
                      "Provided by Learning Commons under CC BY 4.0; standards data from the "
                      "publishers named in each item's attributionStatement. Learning "
                      "progressions (builds-towards links) are provided under CC0 from "
                      "Student Achievement Partners.")
    (args.out / "learning_commons_source.json").write_text(json.dumps(source, indent=2) + "\n",
                                                           encoding="utf-8")

    # ---- report
    print(f"\nCalifornia items read: {len(items)}")
    for subject in ("math", "ela", "eld"):
        recs = {r["record_id"] for r in records if r["subject"] == subject}
        rec_rows = [r for r in rows if r[2] == subject and r[1] == ""]
        matched = {r[0] for r in rec_rows if not r[10].startswith("none")}
        print(f"\n{subject}: {len(matched)} of {len(recs)} records paired")
        for kind, n in Counter(r[10] for r in rec_rows).most_common():
            print(f"    {n:5}  {kind}")
        checks = Counter(r[11] for r in rec_rows if r[11])
        if checks:
            print("    text: " + ", ".join(f"{n} {k}" for k, n in checks.most_common()))
        subs = [r for r in rows if r[2] == subject and r[1]]
        if subs:
            print(f"    sub-items: {sum(not r[10].startswith('none') for r in subs)} of {len(subs)} paired")
    print(f"\nCalifornia standards and components no record pairs with: {len(unmapped)}")
    for (subject, kind), n in sorted(Counter((i['subject'], i['type']) for i in unmapped).items()):
        print(f"    {subject:5} {kind:10} {n}")
    print(f"\nparent standards with no CDE record, added from Learning Commons: {len(parents)}")
    for course, n in sorted(Counter(p[3] or "K-8" for p in parents).items()):
        print(f"    {n:5}  {course}")
    print(f"\nbuilds-towards links in Learning Commons: {len(graph['builds'])}")
    print(f"    {len(graph['builds']) - len(unresolved):5}  written, as {len(edges)} links between rows")
    print(f"           ({len({c[0] for c in candidates})} of them touch a parent standard; the "
          f"{len(candidates)} sub-item pairs they could also mean are listed, not loaded)")
    for why, n in Counter(u[2] or u[3] for u in unresolved).most_common():
        print(f"    {n:5}  not written: {why}")
    eld_items = {r[9] for r in eld_ela}
    print(f"\nELA standards listed against ELD standards: {len(eld_ela)} pairs, "
          f"from the notes of {len(eld_items)} ELD items")
    print(f"    {sum(1 for r in eld_ela if r[7]):5}  point at an ELA placeholder record")
    for why, n in Counter(u[2].split(":")[-1].strip() for u in eld_ela_unresolved).most_common():
        print(f"    {n:5}  not written: {why}")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
