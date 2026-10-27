"""Print visible text of a saved HTML file (no scripts/styles). Parses text only."""
import sys
from html.parser import HTMLParser
class T(HTMLParser):
    def __init__(s): super().__init__(); s.skip=0; s.out=[]
    def handle_starttag(s,t,a):
        if t in ("script","style","noscript"): s.skip+=1
    def handle_endtag(s,t):
        if t in ("script","style","noscript") and s.skip: s.skip-=1
    def handle_data(s,d):
        if not s.skip and d.strip(): s.out.append(" ".join(d.split()))
t=T(); t.feed(open(sys.argv[1],encoding="utf-8",errors="replace").read()); print("\n".join(t.out))
