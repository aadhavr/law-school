"""Polite downloader for data/raw/. Downloads only; never opens or runs downloaded content.

Usage: python -I code/download_sources.py <subfolder> <url> [<url> ...]

- Checks robots.txt for each host (cached) and skips disallowed URLs.
- Waits at least 1 second between any two requests (robots.txt fetches included).
- Never overwrites: an existing file gets a numeric suffix.
- Appends one row per URL to data/raw/manifest.csv:
  url, date_utc, file, bytes, sha256, status, http_status, note
"""
import csv
import hashlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "manifest.csv"
UA = "Mozilla/5.0 (compatible; research-download-script/1.0)"
FIELDS = ["url", "date_utc", "file", "bytes", "sha256", "status", "http_status", "note"]

_last = [0.0]
_robots = {}


def _wait():
    dt = time.time() - _last[0]
    if dt < 1.1:
        time.sleep(1.1 - dt)
    _last[0] = time.time()


def _open(url, timeout=60):
    _wait()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout)


def allowed(url):
    p = urllib.parse.urlsplit(url)
    host = f"{p.scheme}://{p.netloc}"
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            with _open(host + "/robots.txt", timeout=30) as r:
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
            _robots[host] = (rp, "robots.txt read")
        except urllib.error.HTTPError as e:
            # 4xx on robots.txt: treated as no restrictions (RFC 9309); 5xx: treated as disallow.
            rp.parse([] if e.code < 500 else ["User-agent: *", "Disallow: /"])
            _robots[host] = (rp, f"robots.txt HTTP {e.code}")
        except Exception as e:  # network failure: do not assume permission
            rp.parse(["User-agent: *", "Disallow: /"])
            _robots[host] = (rp, f"robots.txt unreachable: {type(e).__name__}")
    rp, note = _robots[host]
    return rp.can_fetch(UA, url), note


def _name_for(url, ctype):
    p = urllib.parse.urlsplit(url)
    name = Path(urllib.parse.unquote(p.path)).name or "index"
    if "." not in name:
        name += ".pdf" if "pdf" in ctype else ".csv" if "csv" in ctype else ".html" if "html" in ctype else ""
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


def _unique(path):
    i = 1
    out = path
    while out.exists():
        out = path.with_name(f"{path.stem}_{i}{path.suffix}")
        i += 1
    return out


def record(row):
    new = not MANIFEST.exists()
    with open(MANIFEST, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})


def fetch(sub, url):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    ok, rnote = allowed(url)
    if not ok:
        record({"url": url, "date_utc": now, "status": "manual", "note": f"disallowed by robots.txt ({rnote})"})
        print("ROBOTS-DISALLOW", url)
        return
    dest_dir = RAW / sub
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        with _open(url) as r:
            data = r.read()
            ctype = r.headers.get("Content-Type", "")
            code = r.status
            final = r.geturl()
            cd = r.headers.get_filename()
    except urllib.error.HTTPError as e:
        record({"url": url, "date_utc": now, "status": "failed", "http_status": e.code, "note": rnote})
        print("HTTP", e.code, url)
        return
    except Exception as e:
        record({"url": url, "date_utc": now, "status": "failed", "note": f"{type(e).__name__}: {e}"})
        print("ERR", type(e).__name__, url)
        return
    name = _name_for("https://x/" + urllib.parse.quote(cd), ctype) if cd else _name_for(final, ctype)
    path = _unique(dest_dir / name)
    path.write_bytes(data)
    note = f"content-type {ctype}" + (f"; redirected to {final}" if final != url else "")
    record({"url": url, "date_utc": now, "file": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(), "status": "ok", "http_status": code, "note": note})
    print("OK", code, len(data), path.relative_to(ROOT))


if __name__ == "__main__":
    sub, urls = sys.argv[1], sys.argv[2:]
    for u in urls:
        fetch(sub, u)
