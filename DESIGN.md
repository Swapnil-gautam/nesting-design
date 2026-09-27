# Cut, keep, or scrap

**A design for deciding where every part comes from, and what the metal left behind is really worth.**

The obvious goal for a cutting shop is to waste as little metal as possible. That turns out to be the wrong goal. It ignores what it costs to put a piece of metal on the saw, and it cannot tell a leftover a future order will use from a sliver of scrap.

This document works out what to optimise instead — **total cost, with a price on every leftover** — and shows what that changes about how the batch gets cut.

Terms: a **leftover** is what the brief calls a *drop*, a piece from an earlier job sitting on the rack. A **plate** is fresh metal we buy.

> **Where the brief's five questions are answered:** the objective and the uncertainty in leftover value — §3 and §4. Assumptions — §1.2. The approach, how it scales and where it breaks — §4. Evaluation and baselines — §6. First version vs ambitious version — §7.

---

## 1. The problem

### 1.1 What we decide

Customers order rectangles in a given metal and thickness. We cut them with a saw from either a fresh plate, bought by weight, or a leftover on the rack. For every part we decide three things:

- **which piece of metal** it comes from,
- **where on it** the part sits,
- **which way round** it faces.

A part can only be cut from the same alloy and thickness, so the batch splits into independent problems — eight of them in the sample, from 10 orders and 86 parts.

### 1.2 What drives the cost, and what I assumed

| | Assumed | Where it comes from |
|---|---|---|
| Metal | $4.20/lb for 6061, $7.50/lb for 7075 | **The data** |
| Loading a piece of stock | 20 minutes | Brief's range, my pick |
| Machine + labour | $80/hr — so one load is about **$27** | Brief's range, my pick |
| Cutting | ~1 min per cut, slower when thicker and for 7075 | The brief |
| Saw blade | 1/8″ of metal lost per cut | Brief's range, my pick |
| Cuts | Edge to edge only; parts may turn 90° | The brief |
| Keeping a leftover | $7 to tag and rack, plus $0.25/sq ft per month | **My assumption** |
| Leftovers | Reused for our own orders or scrapped, never sold | The brief |
| Combining orders | All orders on hand are cut together; parts due later are held | The brief gives `jobs.json` as the batch to nest now |

No questions were needed — every open point has a defensible default, and changing one changes the numbers, not the approach. Two notes:

- **All 10 orders are cut together** even though their due dates span 16 days. Cutting a later order early is low risk: the parts wait on a shelf and still ship on time.
- **A 2-day hold, for live use only, not in the cost numbers.** In real operation a cut that would leave a new plate mostly empty could wait up to two days for a matching order. That only pays if one actually arrives: in the history another order of the same metal followed within two days 34% of the time for 1/4″ 6061 and 33% for 1/2″ 6061, but 13% for 1/8″ and rarely or never for thick or 7075. So the rule would be — hold only for metals above roughly 30%, and only below some plate-fullness threshold. That threshold needs the replay in §6 and is untuned.

**Three shop realities I do not model,** each of which would tighten the answer: fresh plate probably needs a trim cut on its mill edge; *locating* a particular leftover on the rack may cost more than loading it; and 7075 leftovers carry heat and lot numbers, so traceability may limit which orders can use them.

### 1.3 What the data says

**This batch is mostly partial plates.** Six of the eight metal groups do not fill even one plate. So the decisions that matter are not about packing full plates tightly — they are about which stock to use and what shape is left behind.

**A year of past orders tells us which leftovers get reused.** Three things stand out:

- **Thin 6061 dominates.** 1/4″ was ordered 73 times, 1/2″ 66 times, 1/8″ 63. Thick metal barely moves: 1″ twelve times, 3/4″ six. 6061 is about 80% of all orders.
- **Exact sizes almost never repeat.** 167 of the 189 distinct sizes were ordered only once. So the question is never "will this size come back" — it is "will a future part *fit inside* this piece".
- **Some metal has no demand at all.** 3/4″ 7075 was never ordered in the whole year.

---

## 2. My first idea, and where it breaks

The natural plan, and the one I started with:

1. **Fill whole plates** as tightly as possible.
2. **Cut the remaining parts from leftovers** on the rack.
3. **Cut whatever is still left from a new plate,** pushing the parts to one end so the remainder stays as one big piece.

Judged by **yield** — the share of the plate that ends up as parts. More is better.

The packing rule here is sound, and it survives into the final method. What breaks is the *scoring*.

### Same yield, different leftovers

Six 18 × 58″ parts, 1″ 6061, on a 60 × 120″ plate. Both use the same metal, so yield scores them identically:

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

**B is $69 cheaper, and yield cannot tell them apart.** One leaves two thin strips; the other leaves a clean piece a future order can use.

### It also ignores loading

Every piece of metal on the saw costs about $27, whether it is a $4,363 plate or a scrap off the rack. Yield counts none of that, so it happily loads a leftover to save a few dollars of metal. On this batch it loads 8 leftovers against the final plan's 5.

---

## 3. What a leftover is worth

This is the heart of the problem, and it is the number everything else depends on.

```
leftover value  =  chance it gets used  ×  saving if used  −  cost of keeping it

saving if used  =  metal it replaces  −  $27 to load it  −  trim cuts
```

- **Chance it gets used.** Count past orders of the same metal that would fit inside it — either orientation, kerf included — and keep only those where using it actually saves money. Assume it wins half of them, since other leftovers and already-open plates compete for the same order. That gives a rate, and from it the chance of use within 12 months.
- **Cost of keeping it.** About $7 to measure, tag and rack, plus $0.25 per square foot for every month it waits. Unused after 12 months, it is scrapped.

**A worked example.** An 18 × 43″ leftover of 1/4″ 6061. Of the 59 past orders in that metal, **45 would have fit inside it** — so it is near certain to be used. But:

| | |
|---|---|
| Chance of use | ~100% |
| Saving if used | $19.20 (after the $27 load) |
| Cost of keeping | $7.60 |
| **Worth** | **$11.60** |

It holds **$79 of metal** and is worth **$12** to keep. The load eats almost all of it.

### What this tells us: most small leftovers are scrap

Running that calculation across every metal gives the smallest square piece worth keeping:

| Metal | Orders last year | Smallest square worth keeping |
|---|---|---|
| 6061 1/8″ | 47 | 35″ |
| 7075 1/8″ | 16 | 27″ |
| 6061 1/4″ | 59 | 23″ |
| 7075 1/4″ | 14 | 21″ |
| 6061 3/4″ | 6 | 19″ |
| 7075 1/2″ | 12 | 17″ |
| 6061 1/2″ | 54 | 16″ |
| 6061 1″ | 9 | 15″ |
| 7075 1″ | 3 | 12″ |
| 7075 3/4″ | 0 | **never** |

Three things follow, and they were not what I expected:

- **"Keep anything bigger than the smallest part" keeps far too much.** The smallest part ever ordered is 3 × 8″. The real thresholds are several times that.
- **Loading cost decides it, not demand.** A 12 × 12″ piece of 1/8″ 6061 holds $7 of metal against $27 to load it — it can never pay for itself. The same piece in 1″ 7075 holds $109. Cheap thin metal needs big leftovers; expensive thick metal can keep small ones.
- **No demand, no value.** 3/4″ 7075 is never ordered, so none of it is worth keeping however large the piece.

**Applied to the rack today: 15 of the 26 leftovers are worth keeping.** The other 11 cost more to store and load than they will ever save. That conclusion needs no software at all.

### How uncertain is this?

Very. It rests on a year of history and several assumed rates. Three things keep it usable:

- **Plan with the cautious estimate.** Assume a leftover wins only 25% of fitting orders, storage costs $0.50/sq ft/month, and a future load takes 30 minutes. The errors are not symmetric: overvaluing leftovers fills the rack with junk and can even justify buying metal to create them, while undervaluing only scraps a little more.
- **The decisions hold anyway.** The thresholds move about 30% between cautious and optimistic, but their *order* never changes — and on this batch the cautious estimate buys and loads exactly the same stock in all eight groups. Only one layout differs.
- **Borrow when history is thin.** 1″ 7075 has three past orders, 3/4″ 6061 has six. For those, the *shape* of demand is blended with the shop-wide mix; the *rate* stays their own.

---

## 4. How I pick a plan

### 4.1 The cost rule

```
plan cost =  plates bought × plate price
           + pieces of stock loaded × $27
           + cuts × cut cost
           + value of leftovers used up
           − value of leftovers kept
```

**Only the first three lines are cash.** The last two move value between jobs: a piece is credited when kept, and charged the same amount when a later job uses it. So a leftover is never free metal, and keeping one is never money in the bank. On this batch the credit works out at 30% of the metal inside those pieces, because it already allows for the chance they are never used.

**One real decision.** Thirteen 10 × 10″ parts in 1/2″ 6061:

| Way to cut them | Pay today | Leftovers used | Leftovers kept | **Total** |
|---|---|---|---|---|
| Buy a new plate | $990 | $0 | $218 | **$772** |
| The two biggest leftovers | $76 | $209 | $33 | **$252** |
| **Three smaller leftovers** | **$104** | **$118** | **$12** | **$210** |

The middle row is **cheapest to cut today**, but it spends the two pieces future orders are most likely to want. The bottom row pays $27 for one more load and saves them — a 22 × 22″ worth $14, and a 10 × 15″ worth nothing that happens to hold exactly one part.

### 4.2 What the saw can actually cut

```
          ┌───────┬───────┬───────┬──────────────┐
 strip 1  │ part  │ part  │ part  │  remnant     │  a strip is as deep as its deepest part
          ├───────┴──┬────┴─────┬─┴──┬───────────┤
 strip 2  │ part     │ part     │part│  remnant  │  a shallower part gets one trim cut
          ├──────────┴──────────┴────┴───────────┤
          │  leftover: one full-width piece      │
          └──────────────────────────────────────┘
```

The saw cuts edge to edge, so a layout is **strips across the plate**, each strip then cut into parts. Strips can run along either side and any part can turn 90°, so the same parts have many possible layouts. Jigsaw-style nesting, where parts interlock, is not available — no straight cut would free a single part.

This costs a few percent of packing against unrestricted cuts. Three-stage patterns are a later extension.

### 4.3 The method: a quick pass, then a wider search

**Step 1 — the quick pass.** Take the fullest layout for the parts not yet placed, cut it, repeat. This is the packing rule from §2, run three ways: best stock first, plates only, leftovers first. It always produces complete plans, and it is fast.

Its one weakness: it commits to each piece of metal before seeing how the rest will fall.

**Step 2 — the search.** Build many more layouts for every plate and leftover, guided by what each part is currently worth to the plan. Price each with the cost rule.

**Step 3 — choose.** An optimiser picks the cheapest *combination*: every part cut exactly once, each leftover used at most once.

The quick pass is not a discarded first attempt — **its plans stay in the pool, so the search can only improve on them.** Rules like "use leftovers first" are never hard-coded; they happen when they are cheaper. For the 1/4″ 6061 order this builds 45 layouts and uses 4, in about three seconds.

*(Technically: two-stage guillotine patterns, column generation with two knapsacks, then an integer program.)*

### 4.4 Why not the methods that prove the best answer

They exist and they are mature. **Arc-flow** is state of the art for exactly our two-stage guillotine case (Macedo et al. 2010), and **branch-and-price** on the Gilmore–Gomory model has closed instances of several hundred items (Mrad et al. 2013). Both prove optimality; we do not.

**Our objective breaks them.** They need a clean linear cost. We add a setup charge per piece loaded, leftovers that are one of a kind, and a leftover value that is a *lookup on the piece's dimensions*. That last term is the obstacle — and it is why the one published model of guillotine cutting *with usable leftovers* ran from seconds to nearly three hours on instances of 11 to 37 parts, and concluded that heuristics are needed (Andrade et al. 2016).

Machine learning is not a candidate either: hard geometric constraints, and no record of what happened to past leftovers to learn from.

### 4.5 Where this breaks down

- **Many distinct sizes, quantity one.** The search guides itself less well. Plans stay complete but quality drops; a local search would fix it.
- **One batch at a time.** No look-ahead to future orders. §5 shows what that costs.
- **Leftovers are valued one at a time,** as if each were alone and used once. So the model can prefer several medium pieces to one large one.
- **No tight bound.** Part area over plate area says at least 10 plates are needed with no leftovers at all, or 8 if every leftover could be used perfectly. The plan buys 10 — so the remaining prize on metal is at most two plates. That is a loose floor; exact pricing would tighten it.
- **Scale.** Groups run in parallel. The search grows with the number of part *types* and the plate size, not the piece count. Each leftover adds a small sub-problem, so a rack of hundreds needs pre-filtering.

---

## 5. What it does on the data

### On this batch

| Objective | Plates | Leftovers loaded | Cash | **Total cost** |
|---|---|---|---|---|
| Waste least metal (yield) | 10 | 8 | $18,720 | **$16,339** |
| Real costs, leftovers worth $0 | 10 | 4 | $18,605 | **$16,039** |
| **Full method** | **10** | **5** | **$18,634** | **$15,934** |
| Quick pass only, no search | 10 | 7 | $18,709 | **$16,606** |

**Three things the cost rule catches:**

- **Loads that never pay.** For 3/4″ 6061 the quick pass pulls a 13 × 38″ and an 11 × 24″ leftover off the rack for five 10 × 10″ parts that fit on plates already being opened — two loads plus $29 of leftover value, **$238** it did not need to spend.
- **Which leftovers to spend.** Nobody buys a $943 plate for the thirteen 10 × 10″ parts. But ignoring leftover value takes *both* 29 × 45″ pieces — cheaper today, and it spends exactly what future orders want most.
- **Where the leftovers land.** 1″ 7075, eight 6 × 24″ parts, one plate, same metal and same cutting either way. The quick pass mixes orientations and leaves four awkward pieces; after the search every part faces the same way and two clean rectangles worth $870 remain. **$240, purely from what is left behind.**

**Honestly, on one batch the search is marginal:** $672 better than the quick pass, but only **$75** of that is cash. On 1/4″ 6061 the quick pass already lands on the same plan. Counting the loading cost is worth more here than valuing leftovers ($300 against $105).

### Where the metal went

Across all 15 pieces of metal the plan cuts: **53% became parts, 40% went back on the rack as leftovers worth keeping, 7% was scrap** including saw cuts. Five of those 15 pieces were leftovers rather than new plates, and the 1/2″ 6061 order needed no new plate at all.

Many plates are barely touched, because the order only needed a little of that metal. That is exactly why what is left behind matters.

### A year of orders, replayed

One batch hides the effect, because the rack barely turns over. So I replayed the whole year — 220 order lines over 166 days, each order appearing on the day it was placed, the rack starting **empty**:

| Method | Plates bought | Cash | Parts / on rack / scrap |
|---|---|---|---|
| **Full method** | **158** | **$144,230** | 72.8% / 14.3% / **12.9%** |
| Real costs, leftovers worth $0 | 160 | $146,487 | 72.0% / 14.6% / 13.5% |
| Quick pass only, no search | 161 | $146,710 | 71.5% / 13.1% / **15.4%** |

Over a year it buys **three fewer plates**, scraps **2.5 points less** of the metal it buys, and spends about **$2,500 less cash**. Roughly ten times the gap on a single batch.

**Is that worth building?** $2,480 a year is **1.7% of metal spend** — thin against a few weeks of engineering, and worth saying out loud. Three things make the case anyway:

- The sample data is illustrative. What transfers to real volume is the **percentage**, not the dollars.
- **Scrap falling 2.5 points** is the number a shop feels, and it compounds as the rack fills.
- **The cheapest win is not the optimiser at all.** It is the threshold table in §3: stop racking 11 of the 26 leftovers on hand. That needs no software.

**One honest failure.** If orders could only be combined when due within two days, the full method comes out **$229 worse than its own quick pass** — in the first window it splits a 1″ leftover into medium pieces its value table likes, and by the third it must buy an extra $2,948 plate. Valuing leftovers one at a time, one window at a time, can be short-sighted.

---

## 6. How I would know it is working

**The year replay above is the main test, and it is implemented.** All methods see the same order stream, obey the same saw rules and are scored the same way. Success means lower cost per part without the rack growing without limit.

**Why order history and not past leftover records.** Customers order the same parts whichever method cuts them, so order history is a fair yardstick. Past leftovers reflect the method that made them, so a test built on them would favour that method.

**What the replay does not cover yet:**

- **On-time delivery.** The history has no due dates, so nothing is held and lateness cannot be measured. Tuning the 2-day hold needs dates the sample does not have.
- **A steady state.** The year ends with 14% of the metal bought still on the rack. A second year would show whether the rack settles at a size or keeps growing — the real test of a policy that deliberately keeps material.
- **Leftover age.** Tracked but not reported. A piece untouched for twelve months is a cost, not a saving.

**Checking the leftover values themselves.** Fit them on months 1–6, then check months 7–12 in bands: if pieces predicted at 60% are used about 60% of the time, the values are calibrated. **If history were thinner**, borrow the shop-wide size mix (already done for 1″ 7075 and 3/4″ 6061), pool neighbouring thicknesses for the shape of demand but not its rate, and stay on the cautious estimate until enough history builds up.

**In production**, run in shadow mode first: the planner recommends, operators cut as usual, and every override is logged with a reason. Overrides are the best source of constraints we have not modelled.

---

## 7. What I would ship first, and what I would build with a bigger budget

### First version — a few weeks, small team

- The planner from §4, on an off-the-shelf solver.
- A leftover-value table per metal, refreshed monthly, on the cautious estimate.
- All orders on hand nested together; the 2-day hold for 1/4″ and 1/2″ 6061 only.
- Operators see each plan with its cost breakdown and can override it with a reason.
- **A log of every leftover:** created, used, scrapped. This is what makes everything below possible.
- *Deliberately left out:* planning across days, three-stage patterns, simulated leftover values, learned models, a hard cap on rack space.

Why this first: it is the smallest change that captures the three effects that matter — loading cost, which leftover to spend, and the shape of what is left behind — it is easy to measure against today, and it produces the data the next version needs.

### With a bigger budget

**The biggest remaining cost is loading and unloading,** and it is also what makes small leftovers not worth using:

- **Automate loading.** Mobile robots fetch the right piece from the rack; a robot arm loads the saw. If setup drops from 20 minutes to 5, the smallest leftover worth keeping shrinks by a third or more — 1/2″ 6061 goes from 16″ to 10″ — so far more leftovers get reused.
- **A cutter that is not limited to straight cuts.** A waterjet or laser can follow any path, so parts nest tighter and leftovers come out bigger. Waterjet suits thick aluminium better than laser; worth testing on real parts.
- **Decide per order whether to cut now or wait,** from the measured chance a matching order arrives in time.
- **Value leftovers by simulation** over forecast demand, including repeated reuse and how full the rack is. This fixes the one-at-a-time bias in §4.5.
- **Learned models** for reuse probability and for real cut and setup times, trained on the first version's logs.
- **Manage the rack as inventory:** storage cost rises as it fills, and pieces whose value has fallen below their storage cost get cleared out.
- **Feed true cost back into quoting** — for example, discount an ordered size that happens to fit a leftover already on the rack.

**The gap between the two is data, not algorithms.** The ambitious version needs leftover records and machine timings that do not exist yet. The first version saves money now and starts collecting them.

---

## Prototype

- `prototype/drop_value.py` — leftover values from order history; prints the keep/scrap threshold per metal and a verdict on every leftover on the rack. Standard library only.
- `prototype/nest.py` — the planner on `jobs.json` under all four objectives, with full cut lists. Add `--low` for the cautious estimate, or `--window-days 2` for the two-day what-if. Needs numpy and scipy.
- `prototype/replay.py` — the full year from an empty rack.

*This went past the brief's "keep it tiny".* It grew because the claims in §5 are comparisons, and a comparison between methods is worth nothing unless both run on the same code. The reasoning stands without it; the numbers do not.

## References

- Gilmore, Gomory. *Multistage cutting stock problems of two and more dimensions.* Operations Research 13, 1965.
- Macedo, Alves, Valério de Carvalho. *Arc-flow model for the two-dimensional guillotine cutting stock problem.* Computers & OR 37, 2010.
- Mrad, Meftahi, Haouari. *A branch-and-price algorithm for the two-stage guillotine cutting stock problem.* JORS 64, 2013.
- Andrade, Birgin, Morabito. *Two-stage two-dimensional guillotine cutting stock problems with usable leftover.* ITOR 23, 2016.
- Iori, de Lima, Martello, Miyazawa, Monaci. *Exact solution techniques for two-dimensional cutting and packing.* EJOR 289, 2021.
- Cherri, Arenales, Yanasse, Poldi, Vianna. *The one-dimensional cutting stock problem with usable leftovers: a survey.* EJOR 236, 2014.
