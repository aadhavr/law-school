"""Search text of a PDF for a regex; print page and line. Reads text only."""
import re, sys
from pypdf import PdfReader
r = PdfReader(sys.argv[1]); pat = re.compile(sys.argv[2], re.I)
print(sys.argv[1], "pages:", len(r.pages))
for i, p in enumerate(r.pages, 1):
    for line in (p.extract_text() or "").splitlines():
        if pat.search(line): print(f"  p{i}: {line.strip()[:160]}")
