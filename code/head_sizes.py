"""HEAD requests only (no download): print status and Content-Length. Same robots.txt and 1 req/s rules.

Usage: python -I code/head_sizes.py <url> [<url> ...]
"""
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run under python -I
import download_sources as d

for url in sys.argv[1:]:
    ok, note = d.allowed(url)
    if not ok:
        print("ROBOTS-DISALLOW", url)
        continue
    d._wait()
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": d.UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(r.status, r.headers.get("Content-Length"), r.headers.get("Last-Modified"), url)
    except Exception as e:
        print("ERR", getattr(e, "code", type(e).__name__), url)
