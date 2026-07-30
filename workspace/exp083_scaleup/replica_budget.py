"""exp083d: sandbox replica that reproduces the REAL constraint -- a 600s bank
per agent per game (disc729219, confirmed on our ladder replays), injected as
observation['remainingOverageTime'] the way kaggle_environments does.

sandbox_replica.py drives the engine directly, and cg.game's observation does
NOT carry remainingOverageTime -- so an agent that budgets its search off that
field never sees it drain and never throttles. That made the plain replica
measure the UNTHROTTLED cost (638s for a self-play game) and silently skip the
safety mechanism entirely.

Caveat kept honest: both seats share one module instance here, so the search
cost estimator (_SEARCH_COST) is shared between them; on the real ladder each
agent is its own process. Per-seat banks are tracked separately regardless.

Usage: uv run python replica_budget.py <submission.tar.gz> [--bank 600] [--slow 2.0]
"""
from __future__ import annotations
import os, sys, tarfile, tempfile, time, traceback

tarp = os.path.abspath(sys.argv[1])
BANK = float(sys.argv[sys.argv.index("--bank") + 1]) if "--bank" in sys.argv else 600.0
# --slow models the sandbox being slower than this dev box (host: 1.6 vCPU)
SLOW = float(sys.argv[sys.argv.index("--slow") + 1]) if "--slow" in sys.argv else 1.0

d = tempfile.mkdtemp(prefix="sbxb_")
with tarfile.open(tarp) as t:
    t.extractall(d)
os.chdir(d)
sys.path.insert(0, d)
main = type(sys)("main")           # bare module, no __file__ (matches the real loader)
exec(compile(open(os.path.join(d, "main.py")).read(), "<string>", "exec"), main.__dict__)

from cg.game import battle_start, battle_select, battle_finish  # noqa: E402

deck = [int(x) for x in open("deck.csv").read().split()]
obs, sd = battle_start(list(deck), list(deck))
assert sd.battlePtr, f"battle_start failed err={sd.errorType}"

bank = [BANK, BANK]
searched = [0, 0]
nact, tmax = 0, 0.0
t_game = time.time()
while ((obs.get("current") or {}).get("result", -1) < 0) and nact < 2000:
    seat = (obs.get("current") or {}).get("yourIndex", 0)
    obs["remainingOverageTime"] = bank[seat]
    ta = time.time()
    sel = main.agent(obs)
    dt = (time.time() - ta) * SLOW
    bank[seat] -= dt
    tmax = max(tmax, dt)
    if getattr(main, "_SEARCH_COST", [0, 0])[1] > searched[0] + searched[1]:
        searched[seat] += 1
    if bank[seat] < 0:
        print(f"BANK EXHAUSTED for seat {seat} at act #{nact} -- would be a timeout loss")
        break
    try:
        obs = battle_select(sel)
    except Exception:
        print(f"ENGINE REJECTED selection at act #{nact}: sel={sel}")
        traceback.print_exc()
        break
    nact += 1

print(f"\nacts={nact}  wall={time.time()-t_game:.1f}s  max_act={tmax:.2f}s  slow_factor={SLOW}")
for s in (0, 1):
    print(f"  seat{s}: used {BANK - bank[s]:6.1f}s of {BANK:.0f}  "
          f"({(BANK-bank[s])/BANK*100:.1f}%)  searched acts={searched[s]}")
print("VERDICT:", "OK -- both seats finished inside the bank"
      if min(bank) > 0 else "FAIL -- ran the clock out")
battle_finish()
