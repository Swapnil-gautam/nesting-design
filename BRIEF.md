# Nesting Design Take-Home

A design-first take-home built around a real cutting/nesting problem, with a small sample dataset to ground it. It is role-agnostic on purpose: a clean, sensible answer is a good answer, and there is plenty of room to go deep if you enjoy it.

---

## The problem

We run a metal shop. The core daily decision is **how to nest parts onto stock**.

- Customers order **rectangular parts**: each is a width and a length, in a given alloy and thickness, in some quantity.
- We cut parts out of larger **rectangular stock** with a saw.
- Stock comes in two forms:
  - **Fresh plates** we buy. These are priced by weight.
  - **Drops**: leftover rectangles from earlier jobs, sitting in a bin. Cutting a part from a drop means we did not have to buy fresh material for it.

Given a batch of ordered parts plus the stock on hand, you decide which stock each part is cut from, where it sits, and its orientation.

## What "good" means (this is the heart of it, and we want you to define it)

A good layout is **not** simply the one that wastes the least material today. We want you to work out what we should actually be optimizing, and state it concretely. The pieces in play:

- **Material costs money**, priced by weight. Wasted material is expensive.
- **Machine and labor time costs money.** Every plate you load has setup time. Every cut takes time, and thicker or harder material is slower to cut. Packing more parts onto one plate spreads the setup cost over more parts.
- **The parts have value** because you are filling an order.
- **The offcuts are not pure waste.** A leftover above some minimum size becomes a new drop that a *future* order might use, which makes it worth something today. But only if a future order can actually use it. A leftover that is an awkward size nobody orders is effectively scrap.

That last point is where the real judgment lives. How much is a given offcut actually worth to you today, and how should that worth change which layout you pick? A layout that looks slightly more wasteful right now can be the better business decision if it leaves behind drops you will reuse, and worse if it leaves behind junk. Pinning down what an offcut is worth, and being honest about how uncertain that number is, is a big part of this exercise.

## The data

The `data/` folder has three files, described in `data/DATA.md`:

- **`data/jobs.json`**: the batch of orders you need to nest. This is the input to your decision.
- **`data/inventory.json`**: the stock on hand. Plates are fresh material you can buy in any quantity at the listed size and price; drops are a finite bin of one-of-a-kind remnants.
- **`data/order_history.json`**: about a year of past orders. Use it to reason about which drop sizes are likely to be reused, which is what tells you how much a drop is worth.

You do not have to use the data exhaustively. It is there to make the problem concrete, to anchor your assumptions, and to run a prototype against if you build one.

## Some realities of the shop floor

You may simplify any of these, but tell us when you do and why:

- The saw has a **kerf**: every cut destroys a thin strip of material.
- Many machines can only make **guillotine cuts**, where a cut runs all the way across the current piece, edge to edge. Layouts that need free-form interior cuts may not be manufacturable, or may cost more.
- Parts can be **rotated** 90 degrees.
- You can **combine multiple orders** onto one plate to share setup.
- A leftover is only worth storing as a drop **above some minimum size**.
- We treat parts and stock as plain **rectangles**. If you think that approximation matters or breaks down, say so.

These are the constraints we care about. If you think of others, like grain or rolling direction or machine throughput limits, feel free to note them, but you may treat them as out of scope.

## Things you may assume

The data gives you material prices, densities, and demand. For everything else, here are reasonable values to anchor on. Use them, or substitute your own and say so:

- **Machine + labor rate**: an all-in rate somewhere in the range of a typical shop, on the order of dozens of dollars per hour.
- **Plate setup**: pulling, loading, aligning, and clamping a plate takes on the order of tens of minutes.
- **Cut time**: grows with the length of the cut and with material thickness and hardness. A single straight cut is on the order of a minute, and on a small job the plate setup usually dominates the total cutting time.
- **Kerf**: the blade removes a thin strip on every cut, on the order of a tenth of an inch.
- **Minimum keepable drop**: a leftover is only worth keeping above some minimum short-side dimension, on the order of a few inches. You pick the threshold.

## Things you may ask us

Treat us like the customer. If something is ambiguous, email us with your assumptions or your questions. We would much rather see clearly stated, reasonable assumptions than a request for a full spec. Showing good judgment about what to assume is part of what we are looking at.

## Pretend you have a big budget

We want to see both your ceiling and your realism. So tell us two things:

1. **The ambitious version.** If resources were not the constraint, what would you build? The whole system, the data you would gather, the techniques you would reach for.
2. **The first version.** Given a small team and a deadline, what would you ship first, and why that? What does it deliberately leave out?

The gap between those two, and how you reason about it, tells us as much as either one alone.

## What to hand back

A **design document**. No fixed length: clarity beats volume, a few clear pages is plenty, and a diagram where it helps is welcome but never required. We would like it to cover:

- **The objective.** In concrete terms, what makes one layout better than another? How do you handle the uncertainty in the value of offcuts?
- **Assumptions and questions.** What you assumed, and anything you asked us and how you resolved it.
- **The approach.** How you would actually compute good layouts, and why that approach. How it scales as the number of parts and stock grows, and where it breaks down.
- **Evaluation.** How would you know the thing is actually good? What would you measure, and against what baseline? Include how you would estimate the worth of a drop from the order history, and what you would do if that history were thin.
- **Ambitious version vs. first version**, as above.

Optionally, include a **small prototype** in any language, run against the provided data, that demonstrates one idea you think matters. Keep it tiny: a short script that illustrates a single idea, for example how the value you put on offcuts changes which layout you pick, is exactly right. Do not build a production packer. We care about your reasoning far more than runnable code or polish, so skip the prototype if you are short on time.

## Logistics

You have a couple of days of calendar time so you can fit this around your schedule. We do not expect more than a few hours of real work, and we will not reward volume over judgment. Go deeper only if you genuinely enjoy it; we do not score length, and we will not think less of a submission that stops at the few-hours mark. A tight, clear submission is exactly what we are hoping for.
