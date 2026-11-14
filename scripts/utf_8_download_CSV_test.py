import requests

url = "https://www2.cde.ca.gov/cacs/math"
params = dict(mingrade=0, maxgrade=12, order=0, page=0, perpage=100, dl=1)
headers = {"User-Agent": "Mozilla/5.0 (standards research script)",
           "Accept-Charset": "utf-8"}

r = requests.get(url, params=params, headers=headers, timeout=60)
print(r.headers.get("Content-Type"))
# UTF-8 byte sequences for − (U+2212) and ≠ (U+2260)
print("minus present:", b"\xe2\x88\x92" in r.content)
print("not-equal present:", b"\xe2\x89\xa0" in r.content)