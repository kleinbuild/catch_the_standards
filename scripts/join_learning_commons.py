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
rates as the same (jaccard 1.0), and from there to the CDE record. A link is
written only when each end comes out as records with no choice to make. A
parent standard with no record of its own (3.NF.2) stands for its sub-item
records. High school links are left out for now: the same standard is a
separate record in each course, and which course pairs with which is undecided.

Writes to data/derived/:
  learning_commons_map.csv               one row per pairing (or per unmatched record)
  learning_commons_unmapped.csv          California items no CDE record pairs with
  learning_commons_edges.csv             builds-towards links between CDE records; the loader reads this
  learning_commons_edges_unresolved.csv  links not written, and why
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
from load import split_sub_items, normalize_identifier  # noqa: E402

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

def import_edges(rows, items, graph):
    """Returns (edge rows, unresolved rows). See the top of this file for the rule."""
    records_of = defaultdict(set)           # Learning Commons identifier -> CDE record IDs
    info = {}                               # record ID -> (identifier, discipline)
    for r in rows:
        if r[2] == "math" and r[1] == "" and r[6]:
            records_of[r[6]].add(r[0])
            info[r[0]] = (r[3], r[4])

    def resolve(ccss_id):
        """(record IDs, how, problem). Record IDs is empty when there is a problem."""
        ca_items = graph["same_as"].get(ccss_id, [])
        if not ca_items:
            return set(), "", "no California item rated the same (jaccard 1.0)"
        found, how = set(), ""
        for item in ca_items:
            if records_of[item]:
                found |= records_of[item]
            else:                           # a parent with no record: use its sub-items
                kids = set()
                for child in graph["children"].get(item, []):
                    kids |= records_of[child]
                if kids:
                    found |= kids
                    how = "parent standard has no CDE record; linked through its sub-items"
        if not found:
            return set(), "", "the California item has no CDE record"
        if any(info[r][1] for r in found):
            return set(), "", "high school: one record per course, pairing undecided"
        return found, how, ""

    edges, unresolved, seen = [], [], set()
    for a, b, rel_id in graph["builds"]:
        code_a, code_b = graph["ccss"][a], graph["ccss"][b]
        from_ids, how_a, problem_a = resolve(a)
        to_ids, how_b, problem_b = resolve(b)
        if problem_a or problem_b:
            unresolved.append([code_a, code_b, problem_a, problem_b, rel_id])
            continue
        note = "; ".join(dict.fromkeys(h for h in (how_a, how_b) if h))
        for x in sorted(from_ids):
            for y in sorted(to_ids):
                if x != y and (x, y) not in seen:
                    seen.add((x, y))
                    edges.append([x, y, "builds_towards", "learning_commons", note, 0,
                                  info[x][0], info[y][0], code_a, code_b, rel_id])
    return edges, unresolved


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
    records = con.execute(
        "SELECT *, COALESCE(identifier_corrected, identifier_norm) AS join_identifier "
        "FROM standards ORDER BY subject, record_id").fetchall()
    sub_items = defaultdict(list)
    for r in con.execute("SELECT record_id, letter, text FROM sub_items ORDER BY record_id, letter"):
        sub_items[r["record_id"]].append((r["letter"], r["text"]))
    con.close()

    graph_dir = find_lc_dir(args.lc) / "open-knowledge-graph"
    print(f"reading {graph_dir} (two large files; about a minute) ...")
    items, graph, nodes_path, rels_path = read_california_items(graph_dir)
    rows, used = pair(records, sub_items, items)
    edges, unresolved = import_edges(rows, items, graph)

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
    print(f"\nbuilds-towards links in Learning Commons: {len(graph['builds'])}")
    print(f"    {len(graph['builds']) - len(unresolved):5}  written, as {len(edges)} links between CDE records")
    for why, n in Counter(u[2] or u[3] for u in unresolved).most_common():
        print(f"    {n:5}  not written: {why}")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
