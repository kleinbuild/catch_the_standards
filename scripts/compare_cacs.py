#!/usr/bin/env python3
"""
compare_cacs.py - compare a subject-page download with a /cacs/all download
of the same standards, and write a comparison table.

Two ways to run it:

  1) Let it download both (needs network):
       python3 compare_cacs.py --fetch ela
       python3 compare_cacs.py --fetch eld --query e
     Subject URL:  /cacs/<subject>?mingrade=0&maxgrade=12&perpage=100&dl=1
     Search URL:   /cacs/all?query=<q>&carea=<code>&mingrade=0&maxgrade=12&perpage=100&dl=1
     The search needs some text; the default "a" matches nearly every standard,
     and the comparison will show any that it misses.

  2) Compare two CSVs you already downloaded:
       python3 compare_cacs.py subject_ela.csv all_ela.csv

Output (in --out, default ./cacs_compare):
  <name>_comparison.md   summary + tables (columns, counts, missing IDs, field differences)
  <name>_rows.csv        one row per standard ID: in_subject, in_all, which fields differ
  raw files               when --fetch is used

Requires: pip install requests   (only for --fetch)
"""
import argparse
import csv
import io
import sys
from pathlib import Path

BASE = "https://www2.cde.ca.gov/cacs"
# carea codes from the Content Area dropdown on /cacs/all
CAREA = {"cs": 1, "math": 2, "health": 3, "history": 4, "arts": 5, "wl": 6,
         "ela": 7, "library": 8, "pe": 9, "eld": 10, "science": 13, "cte": 11}  # cte: 11 Anchors, 12 Pathways


# ---------------------------------------------------------------- loading

def decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def load_csv(raw: bytes, label: str):
    text = decode(raw)
    if text.lstrip().lower().startswith(("<!doctype", "<html")):
        sys.exit(f"{label}: got an HTML page, not a CSV. Check the URL.")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        sys.exit(f"{label}: no rows.")
    cols = list(rows[0].keys())
    return cols, rows


def find_key(cols):
    if {"subject", "param", "level", "code", "label"} <= set(cols):
        sys.exit("This is a codes.csv from cacs_codes.py (the filter-code list), not a standards "
                 "download.\nCompare two dl=1 downloads instead, e.g.: python3 compare_cacs.py --fetch ela")
    for c in cols:
        if c and "identifier" in c.lower():
            return c
    for c in cols:
        if c and c.strip().lower() in ("id", "code", "standard id"):
            return c
    sys.exit(f"Can't find an identifier column in: {cols}\nUse --key to name it.")


def norm(v):
    """Ignore differences that are only whitespace or dash style."""
    v = (v or "").replace("\r\n", "\n").replace("\u2013", "-").replace("\u2014", "-")
    return " ".join(v.split())


# ---------------------------------------------------------------- fetching

def fetch_pair(subject, query, out):
    import requests
    if subject not in CAREA:
        sys.exit(f"No carea code known for '{subject}'. Known: {', '.join(CAREA)}")
    common = {"mingrade": 0, "maxgrade": 12, "order": 0, "page": 0, "perpage": 100, "dl": 1}
    urls = {
        "subject": (f"{BASE}/{subject}", dict(common)),
        "all": (f"{BASE}/all", dict(common, query=query, carea=CAREA[subject])),
    }
    raws = {}
    with requests.Session() as s:
        s.headers["User-Agent"] = "Mozilla/5.0 (standards research script)"
        for name, (url, params) in urls.items():
            r = s.get(url, params=params, timeout=60)
            r.raise_for_status()
            print(f"[{name}] {r.url}\n        {r.headers.get('Content-Type')} | "
                  f"{r.headers.get('Content-Disposition')}")
            (out / f"{subject}_{name}_raw.csv").write_bytes(r.content)
            raws[name] = (r.content, r.url)
    return raws


# ---------------------------------------------------------------- comparing

def md_table(rows, cols):
    esc = lambda x: str(x).replace("|", "\\|").replace("\n", " ")
    return ("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n" +
            "".join("| " + " | ".join(esc(x) for x in r) + " |\n" for r in rows))


def compare(a, b, name, out, key_override=None, urls=None, max_examples=15):
    cols_a, rows_a = a
    cols_b, rows_b = b
    key_a = key_override or find_key(cols_a)
    key_b = key_override or find_key(cols_b)

    def index(rows, key):
        idx, dupes = {}, []
        for r in rows:
            k = (r.get(key) or "").strip()
            if k in idx:
                dupes.append(k)
            idx[k] = r
        return idx, dupes

    ia, dupes_a = index(rows_a, key_a)
    ib, dupes_b = index(rows_b, key_b)
    only_a = sorted(set(ia) - set(ib))
    only_b = sorted(set(ib) - set(ia))
    both = sorted(set(ia) & set(ib))

    shared_cols = [c for c in cols_a if c in cols_b]
    col_rows = [[c, "yes" if c in cols_a else "-", "yes" if c in cols_b else "-"]
                for c in list(dict.fromkeys(cols_a + cols_b))]

    # field-by-field differences for standards in both
    diff_counts = {c: 0 for c in shared_cols}
    examples = {c: [] for c in shared_cols}
    per_id = {}
    for k in both:
        changed = []
        for c in shared_cols:
            if norm(ia[k].get(c)) != norm(ib[k].get(c)):
                diff_counts[c] += 1
                changed.append(c)
                if len(examples[c]) < 3:
                    examples[c].append((k, ia[k].get(c, ""), ib[k].get(c, "")))
        per_id[k] = changed

    # ---- markdown
    md = [f"# Comparison: {name}\n\n"]
    if urls:
        md.append(f"- Subject download: `{urls[0]}`\n- Search download: `{urls[1]}`\n\n")
    md.append("## Summary\n\n")
    md.append(md_table([
        ["Rows", len(rows_a), len(rows_b)],
        ["Columns", len(cols_a), len(cols_b)],
        ["Identifier column", key_a, key_b],
        ["Duplicate identifiers", len(dupes_a), len(dupes_b)],
        ["Standards only in this file", len(only_a), len(only_b)],
        ["Standards in both", len(both), len(both)],
        ["...of those, with any field different", sum(1 for v in per_id.values() if v), ""],
    ], ["", "Subject page", "Search all"]))

    md.append("\n## Columns\n\n" + md_table(col_rows, ["column", "Subject page", "Search all"]))

    md.append("\n## Field differences (standards in both)\n\n")
    md.append(md_table([[c, diff_counts[c]] for c in shared_cols], ["column", "standards that differ"]))
    for c in shared_cols:
        for k, va, vb in examples[c]:
            md.append(f"\n**{c}** for `{k}`\n\n- subject: {va[:300]!r}\n- all: {vb[:300]!r}\n")

    for title, ids in (("Only in subject-page download", only_a), ("Only in search-all download", only_b)):
        md.append(f"\n## {title} ({len(ids)})\n\n")
        md.append(", ".join(f"`{i}`" for i in ids[:200]) + (" ..." if len(ids) > 200 else "") + "\n"
                  if ids else "None.\n")

    md_path = out / f"{name}_comparison.md"
    md_path.write_text("".join(md), encoding="utf-8")

    # ---- per-standard CSV
    rows_path = out / f"{name}_rows.csv"
    with open(rows_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["identifier", "in_subject", "in_all", "fields_different"])
        for k in sorted(set(ia) | set(ib)):
            w.writerow([k, int(k in ia), int(k in ib), "; ".join(per_id.get(k, []))])

    # ---- console
    print(f"\nsubject: {len(rows_a)} rows, {len(cols_a)} cols | all: {len(rows_b)} rows, {len(cols_b)} cols")
    print(f"only in subject: {len(only_a)} | only in all: {len(only_b)} | both: {len(both)}")
    print(f"columns only in subject: {[c for c in cols_a if c not in cols_b]}")
    print(f"columns only in all:     {[c for c in cols_b if c not in cols_a]}")
    print("fields that differ:", {c: n for c, n in diff_counts.items() if n} or "none")
    print(f"Wrote {md_path} and {rows_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="subject_csv all_csv")
    ap.add_argument("--fetch", metavar="SUBJECT", help="download both versions of this subject")
    ap.add_argument("--query", default="a", help="search text for the /all download")
    ap.add_argument("--key", help="identifier column name, if auto-detect fails")
    ap.add_argument("--name", help="name for output files")
    ap.add_argument("--out", default="cacs_compare")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.fetch:
        raws = fetch_pair(args.fetch, args.query, out)
        a = load_csv(raws["subject"][0], "subject")
        b = load_csv(raws["all"][0], "all")
        urls = (raws["subject"][1], raws["all"][1])
        name = args.name or args.fetch
    elif len(args.files) == 2:
        a = load_csv(Path(args.files[0]).read_bytes(), args.files[0])
        b = load_csv(Path(args.files[1]).read_bytes(), args.files[1])
        urls = None
        name = args.name or Path(args.files[0]).stem
    else:
        ap.error("give --fetch SUBJECT, or two CSV files")

    compare(a, b, name, out, args.key, urls)


if __name__ == "__main__":
    main()
