from common import *
import re, sys
pat = re.compile(sys.argv[1], re.I)
cc=collections.Counter()
seen=set()
for r in rows:
    k=(r["city"],r["family_id"],r["industry"])
    for a in parts(r):
        if pat.search(a):
            cc[(r["city"],r["industry"],a,smap.get(a),year(r)//1)]+=1
agg=collections.defaultdict(lambda: collections.Counter())
for (c,i,a,s,y),n in cc.items():
    agg[(c,i,a,s)][y]+=n
for k in sorted(agg):
    print(k, dict(sorted(agg[k].items())), "total", sum(agg[k].values()))
