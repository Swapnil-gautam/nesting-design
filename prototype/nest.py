"""
Two-stage guillotine nesting that prices offcuts, run on data/jobs.json.

For each alloy + thickness group:

  1. Patterns. A pattern is one way to cut one piece of stock (the plate size,
     or one drop): full-width strips (first-stage cuts), parts side by side in
     each strip (second-stage cuts), and a trim cut for a part shorter than its
     strip. Parts can be rotated. Unused length stays as one full-width offcut.

  2. Price. pattern cost = stock cost + setup + cuts - value of offcuts kept.
     A plate costs its price. A drop costs its own keep value: using it spends
     the future saving it was kept for. Offcut value comes from drop_value.py.

  3. Choose. An integer program picks the cheapest set of patterns that cuts
     every part, using each drop at most once.

Candidate patterns come from two generators that share one pool:
  - column generation (Gilmore and Gomory): the linear relaxation's dual prices
    say what each part is worth, and two knapsacks (parts across a strip,
    strips along the stock) find the pattern that lowers cost the most;
  - a sequential pass: take the single best pattern for the parts still
    unassigned (valuing parts at their metal value), then repeat. It runs three
    ways (best stock first, plates only, drops first) and always yields
    complete plans; "fill the best plate first" is this rule.

Three objectives then choose from the same pool, so only the objective differs:
  yield            minimize metal bought; setup, cuts and offcuts ignored
  no offcut value  real setup and cut costs, but offcuts and drops worth $0
  proposed         real costs, and offcuts and drops valued from order history
A fourth method uses no optimizer at all:
  fixed rules      fill whole plates while the parts left fill at least 80% of a
                   plate, then cut from drops, then cut the rest from new plates

By default all orders in jobs.json are on hand and cut together; parts due later
are cut now and held. With --window-days N, orders are combined only when their
due dates are at most N days apart, and the windows are planned in date order:
an offcut kept in one window goes on the rack and can be used by a later window,
and a drop that is used leaves the rack. Every method uses the same windows and
the same keep rule (keep an offcut if its value is above $0).

Every plan is scored the same way: cash spent (plates, setups, cuts), plus the
value of drops used, minus the value of offcuts kept.

Run:  python prototype/nest.py          (needs numpy and scipy)
      python prototype/nest.py --low    the same, with the low offcut-value estimate
      python prototype/nest.py --window-days 2    only combine orders due at most 2 days apart
"""
import json
import math
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from functools import lru_cache

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp

import drop_value as dv

U = 8                                   # grid resolution: 1/8 inch
K = round(dv.KERF * U)                  # kerf in grid units
SETUP = dv.SETUP_MIN * dv.RATE_PER_HR / 60
HIST, INV = dv.load()
MONTHS = dv.history_months(HIST)
JOBS = json.loads((dv.DATA / "jobs.json").read_text())
WAIT_DAYS = None                        # None: all orders on hand are cut together (the brief).
                                        # A number: orders combine only if due at most that far apart.


@lru_cache(maxsize=None)
def history_value(alloy, thk, a, b):
    """Keep value of an a x b inch offcut (floored to whole inches); 0 if it is scrap."""
    s, l = sorted((math.floor(a + 1e-9), math.floor(b + 1e-9)))
    if s <= 0:
        return 0.0
    return max(0.0, dv.keep_value(alloy, thk, s, l, HIST, INV, MONTHS)["value"])


POLICIES = {
    "yield":           {"setup": 0.0,   "cut": 0.0, "value": lambda *a: 0.0},
    "no offcut value": {"setup": SETUP, "cut": 1.0, "value": lambda *a: 0.0},
    "proposed":        {"setup": SETUP, "cut": 1.0, "value": history_value},
}


def windows(days=None):
    """Orders grouped by due date: a window holds the orders due within `days` of its first.
    days=None puts every order in one window."""
    if days is None:
        return [list(JOBS)]
    out, start = [], None
    for o in sorted(JOBS, key=lambda o: o["due_date"]):
        d = date.fromisoformat(o["due_date"])
        if start is None or (d - start).days > days:
            out.append([])
            start = d
        out[-1].append(o)
    return out


def initial_rack():
    """Drops on hand, per alloy and thickness."""
    rack = defaultdict(list)
    for d in INV:
        if d["kind"] == "drop":
            rack[(d["alloy"], d["thickness_in"])].append(
                {"id": d["id"], "W": d["width_in"], "L": d["length_in"], "cap": d["quantity"]})
    return rack


class Group:
    """One alloy + thickness: the parts ordered and the stock that can cut them."""

    def __init__(self, alloy, thk, orders=None, rack=None):
        """orders: the orders planned together (default: all); rack: drops on hand (default: inventory)."""
        self.alloy, self.thk = alloy, thk
        demand = Counter()
        for o in (JOBS if orders is None else orders):
            for p in o["parts"]:
                if p["alloy"] == alloy and p["thickness_in"] == thk:
                    demand[tuple(sorted((p["width_in"], p["length_in"])))] += p["quantity"]
        self.parts = sorted(demand)                       # (short, long) in inches
        self.demand = np.array([demand[p] for p in self.parts])
        plate = next(i for i in INV if i["kind"] == "plate"
                     and i["alloy"] == alloy and i["thickness_in"] == thk)
        self.stocks = [{"id": plate["id"], "W": plate["width_in"], "L": plate["length_in"],
                        "cap": None, "price": plate["unit_cost"]}]
        for d in (initial_rack()[(alloy, thk)] if rack is None else rack):
            if d["cap"] > 0:
                self.stocks.append({**d, "price": None})
        self.cut = dv.cut_cost(alloy, thk)                 # $ per cut
        per_sqin = dv.price_per_sqin(alloy, thk, INV)
        self.metal = np.array([w * l * per_sqin for w, l in self.parts])

    def stock_cost(self, s, pol):
        st = self.stocks[s]
        if st["price"] is not None:
            return st["price"]
        return pol["value"](self.alloy, self.thk, st["W"], st["L"])

    def orientations(self, s):
        W, L = self.stocks[s]["W"], self.stocks[s]["L"]
        return [(round(a * U) + K, round(b * U) + K) for a, b in {(W, L), (L, W)}]

    def items(self, A, B):
        """(part, across, along) in grid units, both rotations, that fit an A x B piece."""
        out = set()
        for i, (w, l) in enumerate(self.parts):
            for a, b in ((w, l), (l, w)):
                a, b = round(a * U) + K, round(b * U) + K
                if a <= A and b <= B:
                    out.add((i, a, b))
        return sorted(out)


def evaluate(g, s, orient, strips, pol):
    """Parts cut, cost under a policy, number of cuts and offcuts (inches) of one pattern."""
    A, B = orient
    counts = np.zeros(len(g.parts), dtype=int)
    cuts, offcuts, used_len = 0, [], 0
    for h, row in strips:
        cuts += 1
        used_len += h
        used_w = 0
        for i, a, b in row:
            counts[i] += 1
            cuts += 1
            used_w += a
            if b < h:
                cuts += 1
                if h - b - K > 0:
                    offcuts.append(((a - K) / U, (h - b - K) / U))
        if A - used_w - K > 0:
            offcuts.append(((A - used_w - K) / U, (h - K) / U))
    if B - used_len - K > 0:
        offcuts.append(((A - K) / U, (B - used_len - K) / U))
    kept = sum(pol["value"](g.alloy, g.thk, a, b) for a, b in offcuts)
    cost = g.stock_cost(s, pol) + pol["setup"] + pol["cut"] * g.cut * cuts - kept
    return counts, cost, cuts, offcuts


def knapsack(cands, values, bounds, cap):
    """Bounded knapsack on exact capacity. Returns best[u] and a function listing the items."""
    best = np.full(cap + 1, -np.inf)
    best[0] = 0.0
    stages = []
    for item, v, bnd in zip(cands, values, bounds):
        a = item[1]
        left, step = min(bnd, cap // a), 1
        while left > 0 and v > 0:
            take = min(step, left)
            left -= take
            step *= 2
            w = a * take
            cand = best[:cap + 1 - w] + v * take
            took = np.zeros(cap + 1, dtype=bool)
            took[w:] = cand > best[w:]
            best = best.copy()
            best[w:] = np.where(took[w:], cand, best[w:])
            stages.append((item, take, w, took))

    def items_at(u):
        out = []
        for item, take, w, took in reversed(stages):
            if took[u]:
                out += [item] * take
                u -= w
        return out
    return best, items_at


def price(g, s, orient, pi, mu, pol, bound):
    """Most valuable pattern for stock s given part values pi. Returns (reduced cost, strips)."""
    A, B = orient
    items = [it for it in g.items(A, B) if bound[it[0]] > 0]
    if not items:
        return 0.0, None
    val = pol["value"]
    strips = {}
    for h in sorted({b for _, _, b in items}):
        cands = [it for it in items if it[2] <= h]
        values = []
        for i, a, b in cands:
            v = pi[i] - pol["cut"] * g.cut
            if b < h:
                v -= pol["cut"] * g.cut
                if h - b - K > 0:
                    v += val(g.alloy, g.thk, (a - K) / U, (h - b - K) / U)
            values.append(v)
        best, items_at = knapsack(cands, values, [int(bound[i]) for i, _, _ in cands], A)
        best[0] = -np.inf                                  # a strip needs a part
        rem = np.array([val(g.alloy, g.thk, (A - u - K) / U, (h - K) / U)
                        if A - u - K > 0 else 0.0 for u in range(A + 1)])
        tot = best + rem
        u = int(np.argmax(tot))
        v = tot[u] - pol["cut"] * g.cut                    # its first-stage cut
        if np.isfinite(v) and v > 1e-9:
            strips[h] = (v, items_at(u))
    if not strips:
        return 0.0, None
    # Strips along the stock: a bounded knapsack. A strip may repeat until it covers the demand
    # (rounding up, so 13 parts in rows of 4 can use a 4th row); parts beyond demand are trimmed.
    hs = list(strips)
    bounds = [min(-(-int(bound[i]) // c) for i, c in Counter(i for i, _, _ in strips[h][1]).items())
              for h in hs]
    dp, strips_at = knapsack([(h, h) for h in hs], [strips[h][0] for h in hs], bounds, B)
    end = np.array([val(g.alloy, g.thk, (A - K) / U, (B - u - K) / U)
                    if B - u - K > 0 else 0.0 for u in range(B + 1)])
    tot = dp + end
    tot[0] = -np.inf
    u = int(np.argmax(tot))
    if not np.isfinite(tot[u]):
        return 0.0, None
    rc = g.stock_cost(s, pol) + pol["setup"] - tot[u] - mu[s]
    layout = [(h, list(strips[h][1])) for h, _ in strips_at(u)]
    return rc, trim(layout, Counter({i: int(bound[i]) for i in range(len(g.parts))}))


def trim(layout, allowed):
    """Drop parts beyond what is allowed, from the last strips first; drop empty strips."""
    left = Counter(allowed)
    out = []
    for h, row in layout:
        kept = []
        for it in row:
            if left[it[0]] > 0:
                left[it[0]] -= 1
                kept.append(it)
        if kept:
            out.append((h, kept))
    return out


def key(s, orient, strips):
    return (s, orient, tuple(sorted((h, tuple(sorted(row))) for h, row in strips)))


def master(g, cols, pol, integer):
    """Cheapest mix of patterns that cuts at least every part ordered."""
    evals = [evaluate(g, *col, pol) for col in cols]
    c = np.array([e[1] for e in evals])
    A_dem = np.array([e[0] for e in evals], dtype=float).T
    caps = [(s, st["cap"]) for s, st in enumerate(g.stocks) if st["cap"] is not None]
    A_cap = np.array([[1.0 if col[0] == s else 0.0 for col in cols] for s, _ in caps])
    b_cap = np.array([cap for _, cap in caps], dtype=float)
    if integer:
        cons = [LinearConstraint(A_dem, lb=g.demand, ub=np.inf)]
        if caps:
            cons.append(LinearConstraint(A_cap, lb=-np.inf, ub=b_cap))
        res = milp(c, constraints=cons, integrality=np.ones(len(cols)), bounds=Bounds(0, np.inf),
                   options={"time_limit": 60})
        return np.round(res.x).astype(int)
    A_ub = np.vstack([-A_dem, A_cap]) if caps else -A_dem
    b_ub = np.concatenate([-g.demand, b_cap]) if caps else -g.demand.astype(float)
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=(0, None), method="highs")
    m = len(g.parts)
    pi, mu = -res.ineqlin.marginals[:m], np.zeros(len(g.stocks))
    for k, (s, _) in enumerate(caps):
        mu[s] = res.ineqlin.marginals[m + k]
    return pi, mu


def column_generation(g, pol, pool, rounds=100):
    for _ in range(rounds):
        cols = list(pool.values())
        pi, mu = master(g, cols, pol, integer=False)
        new = 0
        for s in range(len(g.stocks)):
            for orient in g.orientations(s):
                rc, strips = price(g, s, orient, pi, mu, pol, g.demand)
                if strips and rc < -1e-6 and key(s, orient, strips) not in pool:
                    pool[key(s, orient, strips)] = (s, orient, strips)
                    new += 1
        if not new:
            return


def sequential(g, pol, pool, values, phases):
    """Best single pattern for the parts still unassigned, repeated until all are assigned.
    phases: the stock allowed in each phase, e.g. drops first and then anything."""
    left = g.demand.copy()
    avail = {s: st["cap"] for s, st in enumerate(g.stocks) if st["cap"] is not None}
    zero = np.zeros(len(g.stocks))
    for allowed in phases:
        while left.sum() > 0:
            best = None
            for s in allowed:
                if avail.get(s, 1) <= 0:
                    continue
                for orient in g.orientations(s):
                    rc, strips = price(g, s, orient, values, zero, pol, left)
                    if strips and (best is None or rc < best[0]):
                        best = (rc, s, orient, strips)
            if best is None:
                break
            _, s, orient, strips = best
            pool.setdefault(key(s, orient, strips), (s, orient, strips))
            left -= evaluate(g, s, orient, strips, pol)[0]
            if s in avail:
                avail[s] -= 1


def choose(g, pol, pool):
    """Integer program over the shared pool, then cut exactly what was ordered."""
    cols = list(pool.values())
    x = master(g, cols, pol, integer=True)
    pieces = [cols[j] for j in range(len(cols)) for _ in range(x[j])]
    left = Counter({i: int(d) for i, d in enumerate(g.demand)})
    out = []
    for s, orient, strips in pieces:
        strips = trim(strips, left)
        for i, n in Counter(i for _, row in strips for i, _, _ in row).items():
            left[i] -= n
        if strips:
            out.append((s, orient, strips))
    return out


def score(g, pieces):
    """The same yardstick for every plan: cash + drop value used - offcut value kept."""
    real = POLICIES["proposed"]
    t = defaultdict(float)
    for s, orient, strips in pieces:
        counts, cost, cuts, offcuts = evaluate(g, s, orient, strips, real)
        st = g.stocks[s]
        if st["price"] is not None:
            t["cash"] += st["price"]
            t["plates"] += 1
        else:
            t["drop value used"] += g.stock_cost(s, real)
            t["drops"] += 1
        t["cash"] += SETUP + g.cut * cuts
        t["cuts"] += cuts
        t["offcut value kept"] += sum(history_value(g.alloy, g.thk, a, b) for a, b in offcuts)
    t["total"] = t["cash"] + t["drop value used"] - t["offcut value kept"]
    return t


def describe(g, pieces):
    lines = []
    same = Counter(key(*p) for p in pieces)
    piece = {key(*p): p for p in pieces}
    for k, n in same.items():
        s, orient, strips = piece[k]
        st = g.stocks[s]
        A = (orient[0] - K) / U
        rows = Counter()
        for h, row in strips:
            txt = " + ".join(f"{c}x {(a - K) / U:g}x{(b - K) / U:g}" for (i, a, b), c in Counter(row).items())
            rows[((h - K) / U, txt)] += 1
        _, _, _, offcuts = evaluate(g, s, orient, strips, POLICIES["proposed"])
        kept = [f"{a:.1f}x{b:.1f} (${history_value(g.alloy, g.thk, a, b):.0f})"
                for a, b in offcuts if history_value(g.alloy, g.thk, a, b) > 0]
        lines.append(f"    {n}x {st['id']} {st['W']:g}x{st['L']:g}, strips run across the {A:g}in side")
        for (depth, txt), c in sorted(rows.items(), key=lambda t: -t[0][0]):
            lines.append(f"        {c}x strip {depth:g}in deep: {txt}")
        lines.append(f"        offcuts kept: {', '.join(kept) if kept else 'none'}")
    return "\n".join(lines)


def rule_plan(g):
    """Fixed rules, no optimizer: fill whole plates while the parts left fill at least 80% of a
    plate, then cut from drops, then cut the rest from new plates. Each piece is packed as full
    as possible (most part area) with the same saw patterns as the optimizer."""
    Y, zero = POLICIES["yield"], np.zeros(len(g.stocks))
    left = g.demand.copy()
    avail = {s: st["cap"] for s, st in enumerate(g.stocks) if st["cap"] is not None}
    plate_area = g.stocks[0]["W"] * g.stocks[0]["L"]
    out = []

    def fullest(stocks):
        best = None
        for s in stocks:
            if avail.get(s, 1) <= 0:
                continue
            for orient in g.orientations(s):
                _, strips = price(g, s, orient, g.metal, zero, Y, left)
                if strips:
                    area = sum(c * w * l for c, (w, l) in zip(evaluate(g, s, orient, strips, Y)[0], g.parts))
                    if best is None or area > best[0]:
                        best = (area, s, orient, strips)
        return best

    def take(best):
        _, s, orient, strips = best
        out.append((s, orient, strips))
        left[:] = left - evaluate(g, s, orient, strips, Y)[0]
        if s in avail:
            avail[s] -= 1

    while left.sum() > 0 and (b := fullest([0])) and b[0] >= 0.8 * plate_area:
        take(b)
    while left.sum() > 0 and (b := fullest(range(1, len(g.stocks)))):
        take(b)
    while left.sum() > 0:
        take(fullest([0]))
    return out


METHODS = ["yield", "no offcut value", "proposed", "fixed rules"]


def plan(g, method):
    """Cutting plan for one group under one method."""
    if method == "fixed rules":
        return rule_plan(g)
    pool = {}
    every, plates, drops = range(len(g.stocks)), [0], range(1, len(g.stocks))
    for pol in POLICIES.values():                        # one shared pool of candidates
        for phases in ([every], [plates], [drops, every]):
            sequential(g, pol, pool, g.metal, phases)
        column_generation(g, pol, pool)
    for pol in POLICIES.values():                        # trimmed pieces become candidates too
        for p in choose(g, pol, pool):
            pool.setdefault(key(*p), p)
    g.candidates = len(pool)
    return choose(g, POLICIES[method], pool)


def update_rack(g, pieces, rack, window):
    """Used drops leave the rack; offcuts worth keeping join it."""
    for s, orient, strips in pieces:
        st = g.stocks[s]
        if st["price"] is None:
            for d in rack:
                if d["id"] == st["id"]:
                    d["cap"] -= 1
        for a, b in evaluate(g, s, orient, strips, POLICIES["proposed"])[3]:
            if history_value(g.alloy, g.thk, a, b) > 0:
                rack.append({"id": f"new-w{window}-{len(rack)}", "W": round(a, 3), "L": round(b, 3), "cap": 1})


def simulate(method):
    """Plan every window in date order under one method. Returns one record per window and group."""
    rack, records = initial_rack(), []
    for w, orders in enumerate(windows(WAIT_DAYS), 1):
        groups = sorted({(p["alloy"], p["thickness_in"]) for o in orders for p in o["parts"]})
        for alloy, thk in groups:
            t0 = time.time()
            g = Group(alloy, thk, orders, rack[(alloy, thk)])
            pieces = plan(g, method)
            records.append({"window": w, "orders": [o["order_id"] for o in orders], "group": (alloy, thk),
                            "g": g, "pieces": pieces, "score": score(g, pieces), "seconds": time.time() - t0})
            update_rack(g, pieces, rack[(alloy, thk)], w)
    return records


def main():
    if "--low" in sys.argv:                                # the pessimistic offcut values
        dv.CAPTURE, dv.STORAGE_PER_SQFT_MONTH, dv.SETUP_MIN = 0.25, 0.50, 30.0
        print("Offcut values: low estimate (competition 25%, storage $0.50/sq ft/month, future setup 30 min)")
    global WAIT_DAYS
    if "--window-days" in sys.argv:
        WAIT_DAYS = int(sys.argv[sys.argv.index("--window-days") + 1])
        print(f"Orders combine only if due at most {WAIT_DAYS} days apart. Windows, planned in date order:")
    else:
        print("All orders on hand are cut together (parts due later are cut now and held).")
    for w, orders in enumerate(windows(WAIT_DAYS), 1):
        print(f"  window {w}: " + ", ".join(f"{o['order_id']} (due {o['due_date']})" for o in orders))
    print("Each plan: cash (plates + setups + cuts) + value of drops used - value of offcuts kept.\n")
    results = {m: simulate(m) for m in METHODS}
    for m in METHODS:
        print(f"== {m}")
        for r in results[m]:
            g, sc = r["g"], r["score"]
            used = Counter(g.stocks[s]["id"] for s, _, _ in r["pieces"])
            print(f"  w{r['window']} {g.alloy} {g.thk:g}in  total ${sc['total']:>6,.0f} = cash ${sc['cash']:>6,.0f}"
                  f" + drops ${sc['drop value used']:>4,.0f} - offcuts ${sc['offcut value kept']:>4,.0f}"
                  f"   uses {', '.join(f'{c}x {k}' for k, c in sorted(used.items()))}  ({r['seconds']:.1f}s)")
    print("\n== proposed plans")
    for r in results["proposed"]:
        g = r["g"]
        parts = ", ".join(f"{d}x {w:g}x{l:g}" for (w, l), d in zip(g.parts, g.demand))
        print(f"window {r['window']} {g.alloy} {g.thk:g}in   {parts}   ({g.candidates} candidate patterns)")
        print(describe(g, r["pieces"]))
    print("\nTotals")
    cols = ["total", "cash", "plates", "drops", "cuts", "drop value used", "offcut value kept"]
    print("  " + f"{'method':<17}" + "".join(f"{c:>18}" for c in cols))
    for m in METHODS:
        t = defaultdict(float)
        for r in results[m]:
            for k, v in r["score"].items():
                t[k] += v
        print("  " + f"{m:<17}" + "".join(f"{t[c]:>18,.0f}" for c in cols))


if __name__ == "__main__":
    main()
