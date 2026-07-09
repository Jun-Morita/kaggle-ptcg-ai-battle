"""Faithful sandbox replica: extract the built tar, cwd=agent dir, sys.path only
sees the SHIPPED cg (not the repo harness), self-play both seats with main.agent
(exactly what Kaggle validation does). Prints per-call timing and any failure.

CRITICAL (found 2026-07-10 after 4 straight silent Kaggle failures): the real
kaggle_environments harness loads main.py via
kaggle_environments.agent.get_last_callable, which does `exec(code_object, env)`
on the raw SOURCE TEXT in a bare namespace -- __file__ is NEVER defined there.
An earlier version of this script used `importlib.util.spec_from_file_location`
+ `exec_module`, which DOES set __file__ like a normal import -- so it silently
passed while every real submission crashed at import with
`NameError: name '__file__' is not defined` (npmcts_policy.py used __file__ to
locate weights_pure.pkl). Below replicates the ACTUAL loading mechanism
(bare exec, no __file__) so this class of bug is caught locally again.

Usage: python sandbox_replica.py <submission.tar.gz>
"""
import sys, os, tarfile, tempfile, time, traceback
import faulthandler
faulthandler.dump_traceback_later(90, repeat=True)

tarp = sys.argv[1]
d = tempfile.mkdtemp(prefix="sbx_")
with tarfile.open(tarp) as t:
    t.extractall(d)
os.chdir(d)
sys.path.insert(0, d)

t0 = time.time()
with open(os.path.join(d, "main.py")) as f:
    _src = f.read()
main = type(sys)("main")  # bare module object, no __file__ attribute set
exec(compile(_src, "<string>", "exec"), main.__dict__)  # matches kaggle_environments.agent.get_last_callable
print(f"import main (bare exec, no __file__): {time.time()-t0:.1f}s", flush=True)

from cg.game import battle_start, battle_select, battle_finish

deck = [int(x) for x in open("deck.csv").read().split()]
obs, sd = battle_start(list(deck), list(deck))
assert sd.battlePtr, f"battle_start failed err={sd.errorType}"

nact = 0
tmax = 0.0
t_game = time.time()
while ((obs.get("current") or {}).get("result", -1) < 0) and nact < 2000:
    ta = time.time()
    sel = main.agent(obs)
    dt = time.time() - ta
    tmax = max(tmax, dt)
    nopt = len((obs.get("select") or {}).get("option", []) or []) if isinstance(obs.get("select"), dict) else -1
    print(f"  act #{nact}: {dt:.2f}s opts={nopt} sel={sel[:5]}", flush=True)
    try:
        obs = battle_select(sel)
    except Exception:
        print(f"ENGINE REJECTED selection at act #{nact}: sel={sel}")
        traceback.print_exc()
        break
    nact += 1

print(f"game done: winner={obs.get('winner')} acts={nact} "
      f"total={time.time()-t_game:.1f}s max_act={tmax:.2f}s", flush=True)
battle_finish()
