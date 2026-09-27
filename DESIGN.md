# Nesting design: cut for total cost, not yield

## Summary

- **Objective:** lowest total cost — metal bought, a setup for every piece of stock loaded, cutting time, adjusted for the value of drops used and offcuts kept. Not yield.
- **Offcut value:** what we expect to save by reusing it, minus the cost of keeping it, estimated from a year of orders. The smallest offcut worth keeping runs from 12″ square (1″ 7075) to 35″ square (1/8″ 6061). Nothing in 3/4″ 7075 is worth keeping at all.
- **Method:** plan each alloy and thickness separately. A quick greedy pass, then a wider search over two-stage guillotine patterns, then an integer program picks the cheapest combination.
- **Sample batch:** $15,934, against $16,339 for a yield objective and $16,606 for the quick pass alone.
- **A year replayed:** 158 plates and 12.9% scrap, against 161 plates and 15.4% scrap for the quick pass alone — about $2,500 less cash.
- **Ship first:** the planner, a monthly offcut-value table, and a log of what happens to every drop.

---

## 1. The objective

### 1.1 What a plan costs

```
plan cost =  plates bought × plate price
           + pieces of stock loaded × setup      (plates and drops alike)
           + cuts × cut cost                     (slower when thicker, and for 7075)
           + value of drops used
           − value of offcuts kept
```

- **Only the first three lines are cash.** The last two move value between batches: an offcut is credited when kept and charged at the same value when a later batch uses it. A drop is never free metal, and keeping one is never money in the bank.
- **The value is an expected saving, not the metal's price.** It already allows for the chance the offcut is never used. On this batch the credit is 30% of the metal inside those pieces.
- **Packing and leftovers are one decision,** so one objective covers both. Part revenue is identical across plans that ship on time, so it drops out.

### 1.2 Why not yield

Six 18 × 58″ parts, 1″ 6061, on a 60 × 120″ plate. Same metal used, so identical yield:

```
A · strips across the 60″ side        B · one strip across the 120″ side
┌───────┬───────┬───────┬──┐          ┌─────┬─────┬─────┬─────┬─────┬─────┬───────┐
│ 18×58 │ 18×58 │ 18×58 │  │ ← 5.6×58 │18×58│18×58│18×58│18×58│18×58│18×58│ 11×58 │
├───────┼───────┼───────┼──┤   ($16)  │     │     │     │     │     │     │ ($97) │
│ 18×58 │ 18×58 │ 18×58 │  │ ← 5.6×58 ├─────┴─────┴─────┴─────┴─────┴─────┴───────┤
├───────┴───────┴───────┴──┤   ($16)  │ 120 × 1.9 scrap                           │
│ 60 × 3.75 scrap          │          └───────────────────────────────────────────┘
└──────────────────────────┘
        kept: $32                                    kept: $97
```

B costs $69 less and yield cannot tell them apart. Yield also ignores setup: on this batch it loads 8 drops against the final plan's 5, some costing more to load than the metal they save.

### 1.3 What an offcut is worth

```
V = P(used within 12 months) × average saving per use − handling − storage
saving per use = metal it replaces − setup to load it − trim cuts
```

- **Chance of use:** count past orders of the same stock that would fit inside it, either orientation, kerf included, keeping only those where reuse actually saves money. Assume it wins half of them, since other drops and open plates compete.
- **"Fits inside", not "same size":** 167 of the 189 distinct sizes in the history were ordered only once.
- **Cost of keeping:** ~$7 to measure, tag and rack, plus $0.25/sq ft per month. Scrapped if untouched after 12 months.

Recomputed monthly as a lookup table of short × long side per stock:

| Stock | Orders/yr | Smallest square worth keeping | Low → high estimate |
|---|---|---|---|
| 6061 1/8″ | 47 | 35″ | 49″ → 29″ |
| 6061 1/4″ | 59 | 23″ | 31″ → 21″ |
| 6061 1/2″ | 54 | 16″ | 21″ → 15″ |
| 6061 3/4″ | 6 | 19″ | 25″ → 16″ |
| 6061 1″ | 9 | 15″ | 19″ → 11″ |
| 7075 1/8″ | 16 | 27″ | 43″ → 23″ |
| 7075 1/4″ | 14 | 21″ | 23″ → 16″ |
| 7075 1/2″ | 12 | 17″ | 19″ → 13″ |
| 7075 3/4″ | 0 | never | never |
| 7075 1″ | 3 | 12″ | 19″ → 11″ |

- **"Keep anything bigger than the smallest part" keeps far too much.** Smallest part ever ordered: 3 × 8″. Real thresholds are several times that.
- **Setup drives the threshold.** A 12 × 12″ piece of 1/8″ 6061 holds $7 of metal against $27 to load it; the same piece in 1″ 7075 holds $109. Cheap thin stock needs big offcuts; expensive thick stock can keep small ones.
- **No demand, no value.** 3/4″ 7075 was never ordered, so nothing in it is kept whatever its size.
- **Today's bin:** 15 of the 26 drops are worth keeping. The other 11 are too small to be used or too cheap to load.

### 1.4 Handling the uncertainty

- **Plan with the low estimate.** It assumes a drop wins 25% of fitting orders, storage costs $0.50/sq ft/month, and a future setup takes 30 min. Errors are asymmetric: overvaluing fills the rack with junk and can justify buying metal just to create offcuts; undervaluing only scraps a little more.
- **Decisions are stable.** Thresholds move ~30% between low and high, but their order never changes, and the low estimate buys and loads exactly the same stock in all 8 groups. One layout differs: 1″ 6061 splits its parts 7 and 2 instead of 6 and 3, leaving one 58 × 84″ offcut instead of three.
- **Thin history borrows.** 1″ 7075 has 3 past orders, 3/4″ 6061 has 6. Their size mix is blended with the shop-wide mix (their own lines count as n, the shop-wide mix as 10); their order *rate* stays their own.

---

## 2. Assumptions

No questions were needed — every open point has a defensible default, and changing one changes the numbers, not the approach.

| Item | Assumed | Basis |
|---|---|---|
| Machine + labor | $80/hr | README: dozens of $/hr |
| Setup | 20 min per piece of stock (~$27) | README: tens of minutes |
| Cut time | 1 min at 1/2″ 6061, scaled by thickness, ×1.5 for 7075 | README |
| Kerf | 0.125″ | README |
| Cuts | Two-stage guillotine, 90° rotation allowed | How a plate saw works |
| Plate size | Full listed size usable | Edge trim costs a fraction of an inch |
| Drops | Reused for our own orders or scrapped, never sold | README |
| Keeping a drop | $7 handling, $0.25/sq ft/month, purged at 12 months | Rack space priced as a cost, not a hard cap |
| Competition | A drop wins half the orders that fit it | Least certain number (§1.4) |
| Combining orders | All orders on hand are cut together; parts due later are held | README gives `jobs.json` as the batch to nest now |

- **All 10 orders are cut together** despite due dates spanning 16 days. Cutting early is low risk: parts wait on a shelf and still ship on time.
- **A 2-day hold is for live use and is not in the cost numbers.** Holding only pays if a matching order arrives. In the history another order of the same stock followed within 2 days 34% of the time for 1/4″ 6061 and 33% for 1/2″ 6061, 13% for 1/8″, and rarely or never for thick or 7075. Rule: hold only for stock above ~30%, and only when the plan would open a plate less than X% used. X needs the replay (§4) and is untuned.
- **Three shop realities we do not model,** each of which would tighten the answer: the mill edge on fresh plate probably needs a trim cut; *locating* a specific drop on the rack may cost more than loading it; and 7075 drops carry heat and lot numbers, so traceability may limit which orders can use them.

---

## 3. The method

### 3.1 What a layout is

```
          ┌───────┬───────┬───────┬──────────────┐
 strip 1  │ part  │ part  │ part  │  remnant     │  strip is as deep as its deepest part
          ├───────┴──┬────┴─────┬─┴──┬───────────┤
 strip 2  │ part     │ part     │part│  remnant  │  a shallower part gets one trim cut
          ├──────────┴──────────┴────┴───────────┤
          │  leftover: one full-width piece      │
          └──────────────────────────────────────┘
```

- **Two stages** because that is how a plate saw works: first cuts run edge to edge and make strips, second cuts split each strip into parts. Costs a few percent of yield against unrestricted guillotine cuts; three-stage is a later extension.
- **Strips can run along either side** and any part can turn 90°. Both are tried.
- **Kerf** is handled by adding the blade width to every dimension.
- **Each layout is priced** by §1.1: stock cost + setup + cuts − the value of every offcut it leaves. A plate costs its price; a drop costs its own offcut value.

### 3.2 One method, two passes

1. **Quick pass (greedy).** Take the fullest layout for the parts still unplaced, cut it, repeat. Run three ways: best stock first, plates only, drops first. Always yields complete plans.
2. **Search (column generation).** The linear relaxation's dual prices say what each part is currently worth; two knapsacks then build the layout that lowers cost most — parts across a strip, then strips along the stock, counting every offcut. Repeat until nothing new helps.
3. **Choose.** An integer program picks how many times to use each layout: every part cut as ordered, each drop at most once, lowest total cost.
4. **Output.** A cut list per piece of stock, plus which offcuts to label and rack.

The quick pass is not a discarded first attempt — its plans stay in the pool, so the search can only improve on them. They are reported separately below so the value of each is visible. Rules like "use drops first" are never hard-coded; they happen when they are cheaper.

### 3.3 Why not the exact methods

- **They exist and they are mature.** Arc-flow is state of the art for exactly our two-stage guillotine case (Macedo et al. 2010); branch-and-price on the Gilmore–Gomory model has closed instances of several hundred items (Mrad et al. 2013). Both prove optimality. We generate columns then solve over the ones we have, which does not.
- **Our objective breaks their structure.** They need a clean linear cost. We add a setup charge per piece loaded, one-of-a-kind drops, and an offcut value that is a *lookup on the leftover's dimensions*. That last term is the obstacle — and it is why the one published model of guillotine cutting *with usable leftovers* ran from seconds to nearly three hours on 11–37 part instances and concluded heuristics are needed (Andrade et al. 2016).
- **Machine learning is not a candidate.** Hard geometric constraints, and no record of what happened to past drops to learn from. Listed in §5 as something the first version's logs would enable.

### 3.4 Results on the sample batch

| Objective | Plates | Drops | Cash | Drop value used | Offcut value kept | Plan cost |
|---|---|---|---|---|---|---|
| Yield (metal only) | 10 | 8 | $18,720 | $268 | $2,649 | $16,339 |
| Real costs, offcuts worth $0 | 10 | 4 | $18,605 | $228 | $2,793 | $16,039 |
| **Proposed** | **10** | **5** | **$18,634** | **$137** | **$2,837** | **$15,934** |
| Quick pass only, no search | 10 | 7 | $18,709 | $235 | $2,338 | $16,606 |

- **Counting setup.** 1/8″ 6061: yield loads a 20 × 22″ drop *and* opens a plate ($242); the plan uses the plate alone ($217). 3/4″ 6061: the quick pass loads a 13 × 38″ and an 11 × 24″ drop for five 10 × 10″ parts that fit on plates already being opened — two loads plus $29 of drop value, **$238** wasted.
- **Which drops.** Nobody buys a $943 plate for the thirteen 10 × 10″ parts in 1/2″ 6061. The plan spends $118 of drop value — a 22 × 22″ ($14), a 29 × 45″ ($104) and a 10 × 15″ ($0) holding exactly one part. Ignoring offcut value takes *both* 29 × 45″ drops ($209): cheaper today, but it spends the pieces future orders most want.
- **Where the leftovers land.** 1″ 7075, eight 6 × 24″ parts, one plate, same metal and cuts either way: the quick pass mixes orientations and leaves four awkward pieces; after the search every part faces the same way and two clean rectangles worth $870 remain. **$240**, purely from what is left behind.
- **What the search adds:** $672 over the quick pass, but only **$75** of it cash — nearly all is better offcuts. On 1/4″ 6061 the quick pass already lands on the final plan. Counting setup is worth more than valuing offcuts here ($300 vs $105).
- **How far from the floor?** Part area over plate area gives a lower limit of **10 plates** with no drops at all, or 8 if every drop could be used perfectly. The plan buys 10. The bound is loose — it ignores that drops are one-of-a-kind and awkwardly shaped — but it caps the remaining prize on metal at two plates, not ten.
- **Speed:** under 5 seconds per group, all four runs together.
- **A bug worth recording.** An earlier version could only repeat *whole* rows, so thirteen parts that fit four to a row forced a second plate. Both passes improved when fixed, the quick pass more. Lesson: a comparison between passes is only as trustworthy as the layout code they share.

**If orders could only combine when due within 2 days** (windows Jun 13–15, 20–22, 24, 27–29, offcuts carried forward), everything costs more and the full method comes out **$229 worse than its own quick pass** — in window 1 it splits a 1″ offcut into medium pieces its value table likes, and by window 3 it must buy an extra $2,948 plate. Valuing offcuts one at a time, one window at a time, can be short-sighted. Run: `--window-days 2`.

### 3.5 Where it breaks down

- **Many distinct sizes, quantity 1.** The relaxation guides pattern generation poorly. Plans stay complete but quality drops; a local search is the fix.
- **Two stages only** — a few percent of yield against three-stage or unrestricted guillotine.
- **One batch at a time.** No look-ahead. The 2-day result above is what that costs.
- **Offcut values are independent.** Each is valued as if alone and used once, so the model can prefer several medium pieces to one large one (7075 1/2″ keeps three).
- **No tight bound.** The area floor above is loose, and the prototype's pricing does not prove optimality. Exact pricing would close that.
- **Scale:** groups run in parallel; knapsacks grow with part *types* and plate size, not piece count; each drop adds a small pricing problem, so a rack of hundreds needs pre-filtering to drops that can hold at least one part.

---

## 4. Evaluation

**The year replay is implemented.** `prototype/replay.py` runs all 220 order lines over 166 days in about a minute. Each order appears on the day it was placed, so the planner never sees the future. The rack starts **empty**, so every drop used was created earlier in the same year by the same method.

| Method | Plates | Cash | Of metal bought: parts / rack / scrap |
|---|---|---|---|
| **Proposed** | **158** | **$144,230** | 72.8% / 14.3% / **12.9%** |
| Real costs, offcuts worth $0 | 160 | $146,487 | 72.0% / 14.6% / 13.5% |
| Quick pass only, no search | 161 | $146,710 | 71.5% / 13.1% / **15.4%** |

**Is it worth building?** $2,480 a year is **1.7% of metal spend** — thin against a few weeks of engineering, and worth saying out loud. Three things make the case anyway:

- The sample data is illustrative; what transfers to real volume is the **percentage**, not the dollars.
- **Scrap falls 2.5 points**, which is the number a shop feels, and it compounds as the rack fills.
- **The cheapest win is not the search at all.** It is the §1.3 threshold table: stop racking 11 of the 26 drops on hand. That needs no optimizer, just the lookup.

**What the replay does not yet cover:**
- **On-time delivery** — the history has no due dates, so nothing is held and lateness cannot be measured. Tuning the 2-day hold needs dates the sample lacks.
- **A steady state** — the year ends with 14% of metal bought still on the rack. A second year would show whether the rack settles or grows, which is the real test of a keep-more policy.
- **Drop age** — tracked but not reported. An offcut untouched for 12 months is a cost, not a saving.

**Also needed:**
- **Offcut values, out of time.** Fit on months 1–6, then check months 7–12 in bands: if pieces predicted at 60% are used ~60% of the time, the values are calibrated.
- **Plan quality.** Exhaustive search on small groups; longer runs and three-stage patterns on large ones.
- **Why order history, not past drop records.** Customers order the same parts whichever method cuts them. Past drops reflect the method that made them, so a test built on them favours that method.
- **In production:** shadow mode first — the planner recommends, operators cut as usual, every override logged with a reason. Overrides are the best source of missing constraints.

---

## 5. First version and ambitious version

**First version — a few weeks, small team:**
- The §3 planner: two-stage patterns, quick pass plus column generation, off-the-shelf solver.
- A monthly offcut-value table per stock, on the low estimate.
- All orders on hand nested together; a 2-day hold for 1/4″ and 1/2″ 6061 only, threshold set by replay.
- Operators see each plan with its cost breakdown and can override with a reason.
- **A log of every drop:** created, used, scrapped. This is what makes everything below possible.
- *Deliberately excluded:* planning across days, three-stage patterns, simulated offcut values, learned models, a hard rack cap.

Why first: smallest change that captures setup, drop choice and offcut shape; easy to measure; and it produces the data the next version needs.

**Ambitious version:**
- **Cut now or wait, per order,** from the chance a matching order arrives in time.
- **Offcut value by simulation** over forecast demand, including repeated reuse and rack fullness — fixes the independence bias above.
- **Learned models:** reuse probability (survival model) and cut/setup times from machine logs.
- **Three-stage patterns and exact bounds.**
- **Manage the rack as inventory:** storage cost rises as it fills; purge drops whose value has fallen below their storage cost.
- **Feed true cost back into quoting** — for example discount an ordered size that fits an existing drop.

**The gap is data, not algorithms.** The ambitious version needs drop records and machine timings that do not exist yet. The first version saves money now and starts collecting them.

---

## 6. Prototype

- `drop_value.py` (stdlib only) — offcut values from order history; prints keep thresholds and a keep/scrap call for every drop on hand. `python prototype/drop_value.py`
- `nest.py` (numpy, scipy) — the §3 planner on `jobs.json` under all four runs, with cut lists. `python prototype/nest.py`, plus `--low` or `--window-days 2`.
- `replay.py` — the full year from an empty rack.

*This went past the brief's "keep it tiny".* It grew because the claims in §3.4 and §4 are comparisons, and a comparison between methods is worth nothing unless both run on the same code. The reasoning stands without it; the numbers do not.

## References

- Gilmore, Gomory. *Multistage cutting stock problems of two and more dimensions.* Operations Research 13, 1965.
- Macedo, Alves, Valério de Carvalho. *Arc-flow model for the two-dimensional guillotine cutting stock problem.* Computers & OR 37, 2010.
- Mrad, Meftahi, Haouari. *A branch-and-price algorithm for the two-stage guillotine cutting stock problem.* JORS 64, 2013.
- Andrade, Birgin, Morabito. *Two-stage two-dimensional guillotine cutting stock problems with usable leftover.* ITOR 23, 2016.
- Iori, de Lima, Martello, Miyazawa, Monaci. *Exact solution techniques for two-dimensional cutting and packing.* EJOR 289, 2021.
- Cherri, Arenales, Yanasse, Poldi, Vianna. *The one-dimensional cutting stock problem with usable leftovers: a survey.* EJOR 236, 2014.
