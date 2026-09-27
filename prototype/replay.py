"""Replay a year of order history through the nester: each day's order lines are cut that day,
the rack starts empty, kept offcuts carry forward. Writes a JSON summary per method."""
import json
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nest as n

OUT = os.path.dirname(os.path.abspath(__file__))

days = defaultdict(list)
for r in n.HIST:
    days[r["ordered_at"]].append(r)


def run(method):
    t0 = time.time()
    rack = defaultdict(list)
    G = defaultdict(lambda: defaultdict(float))
    tot = defaultdict(float)
    for di, day in enumerate(sorted(days)):
        lines = days[day]
        orders = [{"order_id": f"{day}-{i}", "parts": [l]} for i, l in enumerate(lines)]
        for alloy, thk in sorted({(l["alloy"], l["thickness_in"]) for l in lines}):
            g = n.Group(alloy, thk, orders, rack[(alloy, thk)])
            pieces = n.plan(g, method)
            sc = n.score(g, pieces)
            k = f"{alloy} {thk}"
            nlines = sum(1 for l in lines if (l["alloy"], l["thickness_in"]) == (alloy, thk))
            new_plate = False
            for s, o, st in pieces:
                stock = g.stocks[s]
                counts = n.evaluate(g, s, o, st, n.POLICIES["proposed"])[0]
                pa = sum(c * w * l for c, (w, l) in zip(counts, g.parts))
                pc = int(counts.sum())
                if stock["price"] is not None:
                    new_plate = True
                    G[k]["plates"] += 1
                    G[k]["bought"] += stock["W"] * stock["L"]
                    G[k]["parts_from_plates"] += pc
                else:
                    G[k]["leftovers_used"] += 1
                    G[k]["parts_from_leftovers"] += pc
                G[k]["parts_area"] += pa
            G[k]["lines"] += nlines
            if not new_plate:
                G[k]["lines_no_new_plate"] += nlines
            for key in ("total", "cash", "drop value used", "offcut value kept"):
                tot[key] += sc[key]
            n.update_rack(g, pieces, rack[(alloy, thk)], day)
        if di % 20 == 0:
            print(method, di, day, f"{time.time() - t0:.0f}s", flush=True)
    for (alloy, thk), drops in rack.items():
        k = f"{alloy} {thk}"
        G[k]["rack_end_area"] = sum(d["W"] * d["L"] for d in drops if d["cap"] > 0)
        G[k]["rack_end_count"] = sum(1 for d in drops if d["cap"] > 0)
    for k in G:
        G[k]["scrap_area"] = G[k]["bought"] - G[k]["parts_area"] - G[k]["rack_end_area"]
    res = {"groups": {k: dict(v) for k, v in G.items()}, "totals": dict(tot), "seconds": time.time() - t0}
    json.dump(res, open(f"{OUT}\\replay_{method.replace(' ', '_')}.json", "w"), indent=1)
    print(method, "done", f"{time.time() - t0:.0f}s", json.dumps(dict(tot)), flush=True)


for m in sys.argv[1:]:
    run(m)
