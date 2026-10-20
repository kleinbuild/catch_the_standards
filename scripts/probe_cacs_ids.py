#!/usr/bin/env python3
"""
probe_cacs_ids.py - fetch ONE CDE results page as HTML (dl=0, not the CSV) and report:
  1. whether it links to individual standard records (/cacs/id/...),
  2. which identifier and text sit next to each link,
  3. whether math symbols (minus sign, not-equal) survive in the HTML.

This is a look-before-we-build step. It makes a single request.
Run it on the owner's machine (the cloud workspace can't reach www2.cde.ca.gov):

    python scripts/probe_cacs_ids.py
    python scripts/probe_cacs_ids.py --subject ela --mingrade 3 --maxgrade 3

It also saves the raw page to cacs_probe/<subject>_page.html so the HTML
structure can be inspected before writing the real scraper.
"""
import argparse
import re
from pathlib import Path

import requests                 # install name: requests
from bs4 import BeautifulSoup   # install name: beautifulsoup4, import name: bs4

BASE = "https://www2.cde.ca.gov/cacs"


def is_record_link(href: str) -> bool:
    return "/cacs/id/" in href or href.startswith("id/")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subject", default="math")
    ap.add_argument("--mingrade", type=int, default=9)
    ap.add_argument("--maxgrade", type=int, default=12)
    ap.add_argument("--perpage", type=int, default=100)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--show", type=int, default=8, help="how many links to print")
    ap.add_argument("--out", default="cacs_probe")
    args = ap.parse_args()

    params = dict(mingrade=args.mingrade, maxgrade=args.maxgrade, order=0,
                  page=args.page, perpage=args.perpage, dl=0)
    r = requests.get(f"{BASE}/{args.subject}", params=params, timeout=60,
                     headers={"User-Agent": "Mozilla/5.0 (standards research script)"})
    r.raise_for_status()
    print(r.url)
    print("Content-Type:", r.headers.get("Content-Type"))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    page_path = out / f"{args.subject}_page.html"
    page_path.write_bytes(r.content)

    # Passing bytes (not r.text) lets BeautifulSoup use the charset the page declares.
    soup = BeautifulSoup(r.content, "html.parser")

    all_links = soup.find_all("a", href=True)
    links = [a for a in all_links if is_record_link(a["href"])]
    print(f"\n{len(links)} links to individual records (of {len(all_links)} links on the page)")

    for a in links[:args.show]:
        row = a.find_parent("tr") or a.parent
        context = " ".join(row.get_text(" ").split())[:160]
        print(f"  href: {a['href']}")
        print(f"    link text: {a.get_text(strip=True)!r}")
        print(f"    row text:  {context!r}")

    if not links:
        # Show the shapes of the links that ARE there, digits replaced with N.
        shapes = sorted({re.sub(r"\d+", "N", a["href"].split("?")[0]) for a in all_links})
        print("No record links found. Link patterns on the page:")
        for s in shapes:
            print("  ", s)

    text = soup.get_text(" ")
    print("\nminus sign (U+2212) on page:", "\u2212" in text)
    print("not-equal (U+2260) on page: ", "\u2260" in text)
    suspects = re.findall(r"\w\s?\?\s?[a-z0-9(]", text)
    print("'?' sitting between math-like terms:", len(suspects), suspects[:5])
    print(f"\nSaved page to {page_path}")


if __name__ == "__main__":
    main()
