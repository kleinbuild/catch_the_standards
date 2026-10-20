#!/usr/bin/env python3
"""
scrape_cacs_records.py - walk every HTML results page for one subject and save one
row per CDE record: record ID, record URL, identifier, the labeled fields the page
shows for that subject (math: Grade Range, Domain, Discipline, Conceptual Category),
and the text sections (math: Cluster, Standard).

Why the HTML and not the dl=1 CSV:
  - the CSV has no record IDs, and math identifiers repeat across courses
    (A-CED.1 is 558 in Algebra I and 721 in Math I);
  - the CSV export turns symbols like the minus sign and not-equal into "?",
    while the HTML pages are UTF-8 and keep them.

Run on the owner's machine (the cloud workspace can't reach www2.cde.ca.gov).

Test on one page first, into the scratch folder:
    python scripts/scrape_cacs_records.py math --max-pages 1 --out cacs_probe
Full run (writes data/raw/math_records_YYYY-MM-DD.csv):
    python scripts/scrape_cacs_records.py math

Waits 1 second between requests. Output is UTF-8.
"""
import argparse
import csv
import datetime as dt
import re
import time
from pathlib import Path

import requests                 # install name: requests
from bs4 import BeautifulSoup   # install name: beautifulsoup4, import name: bs4

BASE = "https://www2.cde.ca.gov"
PERPAGE = 100
DELAY = 1.0
RECORD_HREF = re.compile(r"/cacs/id/web/(\d+)")
# A line that is only a section name followed by a colon, e.g. "Cluster:" or "Standard:"
HEADING = re.compile(r"(?m)^[ \t]*([A-Z][A-Za-z ]{0,40}):[ \t]*$")


def clean(s):
    """Collapse runs of whitespace (the HTML indents values across several lines)."""
    return " ".join(s.split())


def parse_text_block(div):
    """'<b>Cluster</b>:<br>...<br><br><b>Standard</b>:<br>...' -> {'Cluster': ..., 'Standard': ...}"""
    for br in div.find_all("br"):
        br.replace_with("\n")
    parts = HEADING.split(div.get_text())
    # parts = [text before first heading, name1, body1, name2, body2, ...]
    out = {}
    if parts[0].strip():
        out["Text"] = parts[0].strip()
    for name, body in zip(parts[1::2], parts[2::2]):
        out[name.strip()] = body.strip()
    return out


def parse_record(h4):
    a = h4.find("a", href=RECORD_HREF)
    href = a["href"]
    rec = {
        "record_id": RECORD_HREF.search(href).group(1),
        "url": BASE + href if href.startswith("/") else href,
        "identifier": clean(a.get_text()),
    }
    fields, texts = {}, {}
    for col in h4.parent.select("div.row > div[class*='col-']"):
        pre = col.find("div", style=re.compile("pre-wrap"))
        if pre:
            texts.update(parse_text_block(pre))
            continue
        b = col.find("b")
        if b:
            label = clean(col.get_text().split(":", 1)[0])
            fields[label] = clean(b.get_text())
    return rec, fields, texts


def fetch(session, subject, page, args):
    params = dict(mingrade=args.mingrade, maxgrade=args.maxgrade, order=args.order,
                  page=page, perpage=PERPAGE, dl=0)
    r = session.get(f"{BASE}/cacs/{subject}", params=params, timeout=60)
    r.raise_for_status()
    # Bytes, not r.text, so BeautifulSoup uses the page's declared charset (utf-8).
    return r.url, BeautifulSoup(r.content, "html.parser")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("subject", help="subject page name, e.g. math, ela, eld")
    ap.add_argument("--mingrade", type=int, default=0)
    ap.add_argument("--maxgrade", type=int, default=12)
    ap.add_argument("--order", type=int, default=0, help="sort code for this subject page")
    ap.add_argument("--max-pages", type=int, default=0, help="stop after this many pages (0 = all)")
    ap.add_argument("--out", default="data/raw")
    args = ap.parse_args()

    records, seen, repeats = [], set(), []
    total, page = None, 0
    with requests.Session() as s:
        s.headers["User-Agent"] = "Mozilla/5.0 (standards research script)"
        while True:
            if page > 0:
                time.sleep(DELAY)
            url, soup = fetch(s, args.subject, page, args)
            if total is None:
                m = re.search(r"Showing \d+ ?- ?\d+ of (\d+)", clean(soup.get_text()))
                total = int(m.group(1)) if m else None
            h4s = [h for h in soup.find_all("h4") if h.find("a", href=RECORD_HREF)]
            print(f"page {page}: {len(h4s)} records   {url}")
            if not h4s:
                break
            for h in h4s:
                rec, fields, texts = parse_record(h)
                if rec["record_id"] in seen:
                    repeats.append(rec["record_id"])
                    continue
                seen.add(rec["record_id"])
                rec["page"] = page
                records.append((rec, fields, texts))
            page += 1
            if args.max_pages and page >= args.max_pages:
                break
            if total is not None and page * PERPAGE >= total:
                break

    # Columns: fixed ones, then field labels and text sections in the order first seen.
    # Text sections get a "text_" prefix because some subjects may also have a field
    # with the same name (e.g. a "Cluster" field next to a "Cluster" text section).
    field_cols, text_cols = [], []
    for _, fields, texts in records:
        field_cols += [k for k in fields if k not in field_cols]
        text_cols += [k for k in texts if k not in text_cols]
    header = ["record_id", "url", "identifier"] + field_cols + ["text_" + k for k in text_cols] + ["page"]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{args.subject}_records_{dt.date.today().isoformat()}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for rec, fields, texts in records:
            w.writerow([rec["record_id"], rec["url"], rec["identifier"]]
                       + [fields.get(k, "") for k in field_cols]
                       + [texts.get(k, "") for k in text_cols]
                       + [rec["page"]])

    # ---- checks
    all_text = " ".join(" ".join(t.values()) for _, _, t in records)
    ids = [r["identifier"] for r, _, _ in records]
    print(f"\nsite says {total} standards; saved {len(records)} unique records to {path}")
    if repeats:
        print(f"WARNING: {len(repeats)} records appeared on more than one page, e.g. {repeats[:5]}. "
              "The sort order may not be stable across pages; some records may be missing.")
    if total is not None and not args.max_pages and len(records) != total:
        print(f"WARNING: saved {len(records)} but the site reports {total}.")
    print(f"columns: {header}")
    print(f"identifiers appearing more than once: {len(ids) - len(set(ids))}")
    print("minus sign (U+2212) count:", all_text.count("\u2212"))
    print("en dash (U+2013) count:   ", all_text.count("\u2013"))
    print("not-equal (U+2260) count: ", all_text.count("\u2260"))
    suspect = re.compile(r"\w\s?\?\s?[a-z0-9(]")
    for rec, _, texts in records:
        for name, body in texts.items():
            for m in suspect.finditer(body):
                start = max(0, m.start() - 40)
                print(f"'?' in {rec['identifier']} ({rec['record_id']}) text_{name}: "
                      f"...{body[start:m.end() + 40]}...")


if __name__ == "__main__":
    main()
