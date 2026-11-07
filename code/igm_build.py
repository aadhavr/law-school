import sys, csv, datetime, collections
sys.path.insert(0, 'code')
import read_rda
objs = read_rda.load('data/raw/16_econpanel/data/igm.rda')
c = read_rda.to_columns(objs['igm'])
n = len(c['id'])
rows = [{k: c[k][i] for k in c} for i in range(n)]
epoch = datetime.date(1970, 1, 1)
for r in rows:
    r['d'] = epoch + datetime.timedelta(days=int(r['date']))
print('rows', n, 'dates', min(r['d'] for r in rows), max(r['d'] for r in rows))
print('vote values', collections.Counter(r['vote'] for r in rows))
print('question values', collections.Counter(r['question'] for r in rows).most_common(8))
g = collections.defaultdict(list)
for r in rows: g[(r['id'], r['d'], r['question'], r['statement'])].append(r)
print('questions', len(g))
# compare with the independent gist: Apr 7 2015 monetary policy
for key, v in g.items():
    if key[1] == datetime.date(2015, 4, 7):
        for r in v[:10]: print(key[0], r['panelist'], r['vote'], r['confidence'])
        break

# ---- agreement per question ----
OPINION = {'Strongly Agree': 'A', 'Agree': 'A', 'Uncertain': 'U', 'Disagree': 'D', 'Strongly Disagree': 'D'}
out = []
for (qid, d, q, st), v in sorted(g.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
    vs = [r for r in v if r['vote'] in OPINION]
    if not vs: continue
    n_all = len(v); n_op = len(vs)
    ua = sum(1 for r in vs if OPINION[r['vote']] == 'A') / n_op
    ud = sum(1 for r in vs if OPINION[r['vote']] == 'D') / n_op
    wt = sum((r['confidence'] or 0) for r in vs)
    wa = sum((r['confidence'] or 0) for r in vs if OPINION[r['vote']] == 'A') / wt if wt else float('nan')
    wd = sum((r['confidence'] or 0) for r in vs if OPINION[r['vote']] == 'D') / wt if wt else float('nan')
    out.append(dict(id=qid, date=d.isoformat(), part=q, topic=v[0]['topic'], n_panelists=n_all, n_with_opinion=n_op,
                    unweighted_agree=round(ua, 3), unweighted_disagree=round(ud, 3),
                    weighted_agree=round(wa, 3), weighted_disagree=round(wd, 3), statement=st))
print('questions with votes', len(out))
cut = datetime.date(2016, 10, 29)
def cnt(f, lab):
    s = [o for o in out if f(o)]
    print(lab, len(s), ' (full 10-yr window by 2026-10-29:', sum(1 for o in s if datetime.date.fromisoformat(o['date']) <= cut), ')')
cnt(lambda o: o['weighted_agree'] >= 0.8, 'weighted agree >= 0.80')
cnt(lambda o: o['weighted_disagree'] >= 0.8, 'weighted disagree >= 0.80')
cnt(lambda o: o['unweighted_agree'] >= 0.8, 'unweighted agree >= 0.80')
cnt(lambda o: o['unweighted_disagree'] >= 0.8, 'unweighted disagree >= 0.80')
cnt(lambda o: o['weighted_agree'] >= 0.8 and o['unweighted_agree'] < 0.8, 'weighted-only agree (rule sensitivity)')
cnt(lambda o: o['weighted_disagree'] >= 0.8 and o['unweighted_disagree'] < 0.8, 'weighted-only disagree (rule sensitivity)')
print('n panelists range', min(o['n_panelists'] for o in out), max(o['n_panelists'] for o in out))
import os
os.makedirs('data/derived/igm', exist_ok=True)
keep = [o for o in out if o['weighted_agree'] >= 0.8 or o['weighted_disagree'] >= 0.8 or o['unweighted_agree'] >= 0.8 or o['unweighted_disagree'] >= 0.8]
for o in keep: o['direction'] = 'agree' if max(o['weighted_agree'], o['unweighted_agree']) >= 0.8 else 'disagree'
with open('data/derived/igm/igm_consensus_candidates.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(keep[0].keys())); w.writeheader(); w.writerows(keep)
with open('data/derived/igm/igm_all_questions.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print('wrote', len(keep), len(out))
by_year = collections.Counter(o['date'][:4] for o in keep); print(sorted(by_year.items()))
