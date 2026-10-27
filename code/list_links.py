"""Print hrefs in a saved HTML file that match a regex. Parses text only."""
import re, sys
from html.parser import HTMLParser
from urllib.parse import urljoin
class P(HTMLParser):
    def __init__(s): super().__init__(); s.links=[]; s.cur=None; s.txt=""
    def handle_starttag(s,t,a):
        if t=="a": s.cur=dict(a).get("href"); s.txt=""
    def handle_data(s,d):
        if s.cur is not None: s.txt+=d
    def handle_endtag(s,t):
        if t=="a" and s.cur: s.links.append((s.cur," ".join(s.txt.split())[:90])); s.cur=None
path, base, pat = sys.argv[1], sys.argv[2], sys.argv[3]
p=P(); p.feed(open(path,encoding="utf-8",errors="replace").read())
seen=set()
for h,t in p.links:
    u=urljoin(base,h)
    if re.search(pat,u+" "+t,re.I) and u not in seen: seen.add(u); print(u,"|",t)
