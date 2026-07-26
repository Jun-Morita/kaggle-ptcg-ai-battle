"""Confirm the SHIPPED tar resolves ENC_V3 from cg/arch.json the way the real
harness loads it (bare exec, no __file__), from a cwd that is NOT the repo.

If it silently fell back to ENC_V3=0 the agent would still run and never error --
it would just feed a v3-trained net v1 features. That is the exact silent-failure
class that arch.json exists to prevent, so it gets its own check.
"""
import os, sys, tarfile, tempfile

tarp = sys.argv[1]
d = tempfile.mkdtemp(prefix="encchk_")
with tarfile.open(tarp) as t:
    t.extractall(d)
os.chdir(d)
sys.path.insert(0, d)
ns = {}
exec(compile(open(os.path.join(d, "main.py")).read(), "main.py", "exec"), ns)
print(f"ENC_V3={ns['ENC_V3']}  NUM_WORDS_ENCODER={ns['NUM_WORDS_ENCODER']}  "
      f"MODEL={type(ns['MODEL']).__name__} d={ns['MODEL'].d} h={ns['MODEL'].h} "
      f"enc={ns['MODEL'].n_enc} dec={ns['MODEL'].n_dec}")
assert ns["ENC_V3"] == 1, "SHIPPED AGENT FELL BACK TO v1 FEATURES"
assert ns["NUM_WORDS_ENCODER"] == 26, ns["NUM_WORDS_ENCODER"]
assert ns["MODEL"].h == 4, ns["MODEL"].h
# and the encoder really emits 26 words on a real observation
import glob, json, zipfile
z = zipfile.ZipFile(sorted(glob.glob("/home/jun/kaggle-ptcg-ai-battle/references/raw/episodes_0722/*.zip"))[0])
for nm in [n for n in z.namelist() if n.endswith(".json")][:5]:
    ep = json.loads(z.read(nm))
    for st in ep.get("steps", []):
        for s in (0, 1):
            ob = (st[s] or {}).get("observation") or {}
            if not ob.get("select"):
                continue
            oc = ns["to_observation_class"](ob)
            if oc.select is None or oc.current is None:
                continue
            sv = ns["get_encoder_input"](oc, ns["my_deck"], None)
            assert len(sv.offset) == 26, len(sv.offset)
            print(f"live encoder OK: {len(sv.offset)} words, max dim {max(sv.index)}")
            raise SystemExit(0)
