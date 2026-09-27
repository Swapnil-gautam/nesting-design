# Nesting take-home

Deciding which stock each ordered part is cut from, where it sits and which way it faces — when the leftovers have a future value that is real but uncertain.

**The short version:** optimize total cost, not yield. Metal bought, plus a setup for every piece of stock loaded, plus cutting time, adjusted for the value of drops used and offcuts kept. The value of an offcut is estimated from a year of order history, and it changes which layout you pick.

## What is here

| File | |
|---|---|
| **[DESIGN.md](DESIGN.md)** | The design document — the submission. Objective, assumptions, method, evaluation, first vs ambitious version. |
| **[Cut, Keep, or Scrap.pdf](Cut,%20Keep,%20or%20Scrap.pdf)** | Slides telling the same story with diagrams. The quickest way in. |
| `prototype/` | Three scripts, run against the provided data. |
| [BRIEF.md](BRIEF.md) | The original problem statement. |

The `data/` folder is deliberately not in this repo. Drop the provided `jobs.json`, `inventory.json` and `order_history.json` into `data/` and the scripts run as-is.

## Running the prototype

```
python prototype/drop_value.py     # what each offcut is worth, and the keep/scrap threshold per stock
python prototype/nest.py           # the planner on jobs.json, four objectives, with cut lists
python prototype/replay.py proposed   # a year of order history, replayed from an empty rack
```

`drop_value.py` needs only the standard library. `nest.py` and `replay.py` need `numpy` and `scipy`.

Useful flags: `nest.py --low` uses the cautious offcut-value estimate; `nest.py --window-days 2` only combines orders whose due dates are within two days.

## Headline results

- **Sample batch:** $15,934, against $16,339 for a yield objective.
- **A year of order history replayed:** 158 plates and 12.9% scrap, against 161 plates and 15.4% for a greedy planner without the search step.
- **Today's drop rack:** 15 of the 26 drops are worth keeping; the other 11 cost more to store and load than they will ever save.
