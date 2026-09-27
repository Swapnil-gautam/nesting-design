"""
Is this offcut worth keeping as a drop, or is it scrap?

For an offcut of a given alloy / thickness / size, estimate:

    KEEP value = P(used within horizon) * (avg net saving per use)
                 - handling cost to store it
                 - expected storage cost while it waits

    net saving per use = material saved (parts cut from it instead of fresh plate)
                         - setup to load the drop
                         - trim cuts on the drop

Keep it if KEEP value > 0, otherwise scrap it.

Demand comes from order_history.json: which past order lines of the same
alloy + thickness would have fit inside the offcut. Groups with thin history
borrow the size distribution from all orders (shrinkage), see `demand_pool`.

Run:  python prototype/drop_value.py
"""
import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# ---- Assumptions (all tunable; stated in the design doc) --------------------
RATE_PER_HR = 80.0          # machine + labor, $/hr
SETUP_MIN = 20.0            # load/align/clamp one piece of stock
TRIM_CUTS = 2               # extra cuts to square a drop down to a part
CUT_MIN_BASE = 1.0          # minutes per cut at 1/2" 6061
HARDNESS = {"6061-T6": 1.0, "7075-T6": 1.5}
HANDLING_MIN = 5.0          # tag, measure, log, carry to rack
STORAGE_PER_SQFT_MONTH = 0.25  # rack space + inventory overhead, $/sq ft/month
HORIZON_MONTHS = 12.0       # unused drops get purged after this
CAPTURE = 0.5               # share of fitting orders this drop actually wins
                            # (other drops / open plates compete for the same order)
KERF = 0.125
SHRINK_K = 10               # pseudo-lines of pooled demand mixed into each group
DENSITY = {"6061-T6": 0.0975, "7075-T6": 0.1010}


def load():
    hist = json.loads((DATA / "order_history.json").read_text())
    inv = json.loads((DATA / "inventory.json").read_text())
    return hist, inv


def history_months(hist):
    d = sorted(r["ordered_at"] for r in hist)
    y0, m0, dd0 = map(int, d[0].split("-"))
    y1, m1, dd1 = map(int, d[-1].split("-"))
    return (y1 - y0) * 12 + (m1 - m0) + (dd1 - dd0) / 30.0


def price_per_sqin(alloy, thk, inv):
    plate = next(i for i in inv if i["kind"] == "plate"
                 and i["alloy"] == alloy and i["thickness_in"] == thk)
    return plate["unit_cost"] / (plate["width_in"] * plate["length_in"])


def cut_cost(alloy, thk):
    minutes = CUT_MIN_BASE * (thk / 0.5) * HARDNESS[alloy]
    return minutes * RATE_PER_HR / 60


def pieces_that_fit(s, l, ds, dl):
    """How many s x l parts fit in a ds x dl drop (simple grid, either orientation)."""
    a = math.floor((ds + KERF) / (s + KERF)) * math.floor((dl + KERF) / (l + KERF))
    b = math.floor((ds + KERF) / (l + KERF)) * math.floor((dl + KERF) / (s + KERF))
    return max(a, b)


def demand_pool(hist, alloy, thk):
    """(weight, line) pairs: the group's own lines, blended with all lines when history is thin."""
    own = [r for r in hist if r["alloy"] == alloy and r["thickness_in"] == thk]
    n = len(own)
    w_own = n / (n + SHRINK_K)
    pool = [(w_own / n, r) for r in own] if n else []
    pool += [((1 - w_own) / len(hist), r) for r in hist]
    return own, pool


def keep_value(alloy, thk, ds, dl, hist, inv, months):
    ds, dl = min(ds, dl), max(ds, dl)
    p_in2 = price_per_sqin(alloy, thk, inv)
    setup = SETUP_MIN * RATE_PER_HR / 60
    trim = TRIM_CUTS * cut_cost(alloy, thk)
    own, pool = demand_pool(hist, alloy, thk)
    lines_per_month = len(own) / months

    # Weighted share of order lines that would profitably use this drop, and their avg saving.
    w_use, w_saving = 0.0, 0.0
    for w, r in pool:
        s, l = sorted((r["width_in"], r["length_in"]))
        n = min(r["quantity"], pieces_that_fit(s, l, ds, dl))
        if n == 0:
            continue
        saving = n * s * l * p_in2 - setup - trim
        if saving > 0:                       # shop would not bother otherwise
            w_use += w
            w_saving += w * saving
    avg_saving = w_saving / w_use if w_use else 0.0

    lam = CAPTURE * lines_per_month * w_use  # useful arrivals per month for this drop
    p_used = 1 - math.exp(-lam * HORIZON_MONTHS)
    months_held = (p_used / lam) if lam > 0 else HORIZON_MONTHS
    storage = STORAGE_PER_SQFT_MONTH * (ds * dl / 144) * months_held
    handling = HANDLING_MIN * RATE_PER_HR / 60
    value = p_used * avg_saving - handling - storage
    return {
        "p_used": p_used, "avg_saving": avg_saving, "storage": storage,
        "handling": handling, "value": value,
        "material": ds * dl * p_in2, "hist_lines": len(own),
    }


def main():
    hist, inv = load()
    months = history_months(hist)
    groups = sorted({(p["alloy"], p["thickness_in"]) for p in inv if p["kind"] == "plate"})
    sizes = [(4, 8), (4, 24), (6, 12), (6, 24), (9, 12), (12, 12), (12, 24),
             (18, 24), (24, 24), (24, 48), (48, 60)]

    print(f"History covers {months:.1f} months. Setup ${SETUP_MIN*RATE_PER_HR/60:.0f}/load, "
          f"handling ${HANDLING_MIN*RATE_PER_HR/60:.2f}, storage ${STORAGE_PER_SQFT_MONTH}/sqft/mo, "
          f"capture {CAPTURE:.0%}, horizon {HORIZON_MONTHS:.0f} mo\n")

    print("1) Net value of KEEPING an offcut, by size ($; negative = scrap it)\n")
    head = f"{'group':<16}{'lines/yr':>9} " + "".join(f"{f'{s}x{l}':>8}" for s, l in sizes)
    print(head)
    print("-" * len(head))
    for a, t in groups:
        row = f"{a[:4]+' '+str(t)+'in':<16}"
        own = sum(1 for r in hist if r["alloy"] == a and r["thickness_in"] == t)
        row += f"{own*12/months:>9.0f} "
        for s, l in sizes:
            v = keep_value(a, t, s, l, hist, inv, months)["value"]
            row += f"{v:>8.0f}"
        print(row)

    print("\n2) Smallest keepable offcut per group (break-even square side, and min length at 6in wide)\n")
    for a, t in groups:
        sq = next((x for x in range(2, 61) if keep_value(a, t, x, x, hist, inv, months)["value"] > 0), None)
        strip = next((x for x in range(6, 121) if keep_value(a, t, 6, x, hist, inv, months)["value"] > 0), None)
        print(f"  {a} {t:<5}  square >= {str(sq)+'in' if sq else 'never':<7}  6in strip: length >= {str(strip)+'in' if strip else 'never'}")

    print("\n3) Current drops in the bin: keep or scrap?\n")
    print(f"  {'id':<10}{'stock':<16}{'size':>9}{'material $':>11}{'P(used 12mo)':>13}{'keep value $':>13}  verdict")
    for d in (i for i in inv if i["kind"] == "drop"):
        k = keep_value(d["alloy"], d["thickness_in"], d["width_in"], d["length_in"], hist, inv, months)
        print(f"  {d['id']:<10}{d['alloy'][:4]+' '+str(d['thickness_in'])+'in':<16}"
              f"{str(d['width_in'])+'x'+str(d['length_in']):>9}{k['material']:>11.0f}"
              f"{k['p_used']:>13.0%}{k['value']:>13.0f}  {'KEEP' if k['value'] > 0 else 'scrap'}")

    print("\n4) Offcuts from the 1in 6061 example (plate 2)\n")
    for s, l in [(60, 62), (15, 58), (9, 26), (5.75, 120), (11.4, 58)]:
        k = keep_value("6061-T6", 1, s, l, hist, inv, months)
        print(f"  {s}x{l:<6} material ${k['material']:>6.0f}  P(used) {k['p_used']:>4.0%}  "
              f"keep value ${k['value']:>6.0f}  {'KEEP' if k['value'] > 0 else 'scrap'}")


if __name__ == "__main__":
    main()
