#!/usr/bin/env python3
"""
cacs_codes.py - discover the filter codes on the CA Content Standards (CACS)
search pages and write reference files for them.

For each subject page (/cacs/ela, /cacs/eld, /cacs/math, ...) it reads:
  - the c0 / c1 / c2 dropdowns (Subject Area, Domain, Cluster, or whatever
    that subject calls its levels) and every code -> label pair in them
  - criteria that are already selected (these are NOT in the dropdown; the
    page shows them as "remove" links, so the script recovers them from the
    hidden form inputs)
  - the grade, order, and per-page codes
  - the result count and the notes banner

Outputs (in --out, default ./cacs_reference):
  codes.json                 everything, one entry per subject
  codes.csv                  flat table: subject, param, level, code, label
  CACS_URL_REFERENCE.md      human-readable reference doc
  raw/<subject>.html         the pages as fetched, so you can re-parse offline

Usage:
  python3 cacs_codes.py                       # all subjects
  python3 cacs_codes.py ela eld math          # just these
  python3 cacs_codes.py --from-file ela=saved_page.html   # parse a saved page, no network

Requires: pip install requests beautifulsoup4
"""
import argparse
import csv
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www2.cde.ca.gov/cacs"
SUBJECTS = ["arts", "cte", "cs", "ela", "eld", "health", "history",
            "math", "pe", "library", "science", "wl", "all"]
HEADERS = {"User-Agent": "Mozilla/5.0 (standards research script)"}


# ---------------------------------------------------------------- fetching

def fetch(session, subject, query="a"):
    """Get the subject's base page with no filters, so every code is listed.
    /cacs/all shows no controls until something is searched, so it gets a query."""
    params = {"query": query} if subject == "all" else None
    r = session.get(f"{BASE}/{subject}", params=params, timeout=30)
    r.raise_for_status()
    return r.text


# ---------------------------------------------------------------- parsing

def text(tag):
    return tag.get_text(" ", strip=True) if tag else ""


def options(select):
    """[(value, label), ...] for a <select>, skipping the '0 = Add a ...' placeholder."""
    out = []
    for opt in select.find_all("option"):
        v = opt.get("value")
        if v is None or v == "0" and opt.get_text(strip=True).lower().startswith("add"):
            continue
        out.append((v, opt.get_text(strip=True)))
    return out


def normalize(label):
    """Loose form of a label, used to spot near-duplicates like 'Standard' vs 'Standards'."""
    words = re.findall(r"[a-z0-9]+", label.lower())
    return " ".join(w[:-1] if w.endswith("s") and len(w) > 3 else w for w in words)


def parse_page(html, subject):
    soup = BeautifulSoup(html, "html.parser")
    warnings = []

    # Hidden inputs in the search form hold the current filter values (c0=1, c1=2 ...)
    hidden = {}
    form = soup.find("form", id="CriteriaForm")
    if form:
        for inp in form.find_all("input", type="hidden"):
            hidden[inp.get("name")] = inp.get("value", "")
    else:
        warnings.append("No CriteriaForm found - page layout may have changed.")

    # The filter levels: <select id="CriteriaValues_0_">, _1_, _2_ ...
    levels = []
    for sel in soup.find_all("select", id=re.compile(r"^CriteriaValues_\d+_$")):
        idx = int(re.search(r"\d+", sel["id"]).group())
        param = f"c{idx}"
        label_tag = soup.find("label", attrs={"for": sel["id"]})
        level_name = text(label_tag) or f"Level {idx}"

        codes = [{"code": int(v), "label": lab, "selected": False}
                 for v, lab in options(sel)]

        # Already-selected criteria are removed from the dropdown and shown as
        # bold "remove" links in the same form-group. Pair them with the hidden input.
        selected_vals = [v for v in hidden.get(param, "").split(",") if v.strip()]
        group = sel.find_parent("div", class_="form-group")
        selected_labels = []
        if group:
            for chip in group.select("span.results-criteria-option"):
                bold = chip.find("span", style=re.compile("font-weight"))
                if bold:
                    selected_labels.append(text(bold))
        if len(selected_vals) != len(selected_labels):
            warnings.append(f"{param}: {len(selected_vals)} selected value(s) but "
                            f"{len(selected_labels)} label(s); check by hand.")
        for v, lab in zip(selected_vals, selected_labels):
            codes.append({"code": int(v), "label": lab, "selected": True})

        codes.sort(key=lambda c: c["code"])
        if not codes:
            warnings.append(f"{param} ({level_name}) has no codes on this page.")

        # Flag labels that are probably the same thing under two codes
        seen = {}
        for c in codes:
            seen.setdefault(normalize(c["label"]), []).append(c)
        dupes = [group for group in seen.values() if len(group) > 1]
        for d in dupes:
            warnings.append(f"{param} possible duplicate: " +
                            " / ".join(f'{c["code"]}="{c["label"]}"' for c in d))

        levels.append({"param": param, "name": level_name, "codes": codes})

    # Every other dropdown (grades, order, per-page, content area, ...).
    # Each one's change handler copies its value into a hidden input; this maps
    # the dropdown id to that hidden input's name, which is the URL parameter.
    controls = []
    for sel in soup.find_all("select"):
        sid = sel.get("id", "")
        if not sid or sid.startswith("CriteriaValues_"):
            continue
        # the first setter call, $("#x").val(something), inside this dropdown's change handler
        handler = re.search(r'\$\("#' + re.escape(sid) + r'"\)\.change\(.*?\$\("#(\w+)"\)\.val\(\w',
                            html, re.S)
        param = handler.group(1) if handler else None
        if sid == "MinGradeSelect":
            param = "mingrade"
        elif sid == "MaxGradeSelect":
            param = "maxgrade"
        label_tag = soup.find("label", attrs={"for": sid})
        codes = []
        for opt in sel.find_all("option"):
            try:
                codes.append({"code": int(opt.get("value")), "label": opt.get_text(strip=True)})
            except (TypeError, ValueError):
                pass
        if param is None:
            warnings.append(f"Could not tell which URL parameter {sid} sets.")
        controls.append({"select_id": sid, "param": param, "name": text(label_tag) or sid,
                         "codes": codes})

    count_match = re.search(r"of\s*<b>\s*(\d+)\s*</b>\s*Standards", html)
    banner = soup.find("div", class_="banner-container")

    return {
        "subject": subject,
        "page_title": text(soup.select_one("#content h2")),
        "url": f"{BASE}/{subject}",
        "form_defaults": hidden,
        "levels": levels,
        "controls": controls,
        "result_count_on_page": int(count_match.group(1)) if count_match else None,
        "notes": [text(li) for li in banner.find_all("li")] if banner else [],
        "warnings": warnings,
    }


# ---------------------------------------------------------------- writing

def write_csv(results, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["subject", "param", "level", "code", "label"])
        for r in results:
            for lvl in r["levels"] + r["controls"]:
                for c in lvl["codes"]:
                    w.writerow([r["subject"], lvl["param"], lvl["name"], c["code"], c["label"]])


def md_table(rows, cols):
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    return head + "".join("| " + " | ".join(str(x) for x in row) + " |\n" for row in rows)


def write_markdown(results, path):
    out = [f"# CACS URL reference\n",
           f"Generated {date.today().isoformat()} by cacs_codes.py from {BASE}/<subject>.\n",
           "## URL pattern\n",
           "```\n" + BASE + "/<subject>?c0=..&c1=..&c2=..&order=0&page=0"
           "&perpage=100&mingrade=0&maxgrade=12&dl=1\n```\n",
           md_table([
               ["subject", "path segment: " + ", ".join(SUBJECTS)],
               ["c0, c1, c2", "filter levels (names vary by subject, see below). "
                              "Comma-separate for several values: c1=2,3. Leave out unused levels."],
               ["mingrade / maxgrade", "0 = TK & K, 1-12 = grades 1-12. Both default to 0 (K only)."],
               ["order", "sort order, codes below"],
               ["page / perpage", "page index from 0; 10, 25 or 100 per page"],
               ["dl", "0 = HTML results page, 1 = download the results as a file"],
           ], ["param", "meaning"]),
           "\nVerified so far: dl=1 returns the full result set as one CSV (row count "
           "matched the page's 'Showing X of Y' for ela c0=1&c1=2).\n"]

    # Grade codes are the same everywhere, so list them once
    grade_ctrl = next((c for r in results for c in r["controls"] if c["param"] == "mingrade"), None)
    if grade_ctrl:
        out.append("\n## Grade codes (mingrade / maxgrade, all pages)\n\n")
        out.append(md_table([[c["code"], c["label"]] for c in grade_ctrl["codes"]], ["code", "label"]))

    for r in results:
        out.append(f"\n## {r['subject']} - {r['page_title']}\n")
        out.append(f"Base page: {r['url']}\n")
        if r["form_defaults"]:
            out.append("\nForm defaults on fetched page: `" +
                       "&".join(f"{k}={v}" for k, v in r["form_defaults"].items()) + "`\n")
        if r["result_count_on_page"] is not None:
            out.append(f"\nStandards shown on the fetched page: {r['result_count_on_page']}\n")
        for lvl in r["levels"]:
            out.append(f"\n### {lvl['param']} = {lvl['name']}\n\n")
            out.append(md_table([[c["code"], c["label"] + (" (was selected on fetched page)" if c["selected"] else "")]
                                 for c in lvl["codes"]], ["code", "label"]))
        for ctrl in r["controls"]:
            if ctrl["param"] in ("mingrade", "maxgrade"):
                continue
            out.append(f"\n### {ctrl['param'] or '?'} = {ctrl['name']}\n\n")
            out.append(md_table([[c["code"], c["label"]] for c in ctrl["codes"]], ["code", "label"]))
        if r["notes"]:
            out.append("\nPage notes:\n\n" + "".join(f"- {n}\n" for n in r["notes"]))
        if r["warnings"]:
            out.append("\nCheck by hand:\n\n" + "".join(f"- {w}\n" for w in r["warnings"]))
        out.append("\nOpen questions:\n\n- [ ] Are these codes stable over time?\n"
                   "- [ ] Columns in this subject's dl=1 CSV:\n")

    Path(path).write_text("".join(out), encoding="utf-8")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("subjects", nargs="*", default=SUBJECTS)
    ap.add_argument("--out", default="cacs_reference")
    ap.add_argument("--from-file", action="append", default=[], metavar="SUBJECT=PATH",
                    help="parse a saved page instead of fetching (repeatable)")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    ap.add_argument("--query", default="a", help="search text used when fetching 'all'")
    args = ap.parse_args()

    out = Path(args.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)

    pages = {}
    for spec in args.from_file:
        subj, _, p = spec.partition("=")
        pages[subj] = Path(p).read_text(encoding="utf-8")

    results = []
    with requests.Session() as s:
        s.headers.update(HEADERS)
        todo = list(pages) if pages else args.subjects
        for i, subj in enumerate(todo):
            html = pages.get(subj)
            if html is None:
                if i:
                    time.sleep(args.delay)
                try:
                    html = fetch(s, subj, args.query)
                except requests.RequestException as e:
                    print(f"[{subj}] fetch failed: {e}", file=sys.stderr)
                    continue
                (out / "raw" / f"{subj}.html").write_text(html, encoding="utf-8")
            r = parse_page(html, subj)
            results.append(r)
            n = sum(len(l["codes"]) for l in r["levels"])
            ctrls = ", ".join(f"{c['param']}({len(c['codes'])})" for c in r["controls"])
            print(f"[{subj}] {len(r['levels'])} filter levels, {n} codes; "
                  f"controls: {ctrls or 'none'}; {len(r['warnings'])} warnings")
            for w in r["warnings"]:
                print(f"    ! {w}")

    (out / "codes.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(results, out / "codes.csv")
    write_markdown(results, out / "CACS_URL_REFERENCE.md")
    print(f"Wrote {out}/codes.json, codes.csv, CACS_URL_REFERENCE.md")


if __name__ == "__main__":
    main()
