"""Build v006: NON-EX attacker deck (the apex archetype) + crash-safety.
Deck = charmq's exact non-ex list (Hop's Trevenant + Dudunsparce engine, all
single-prize), replicated from LB #4's replays. Policy = generic lucario_v2
(pilots it cleanly, 0 errors). Beats ex (0.67) AND Crustle (0.83) locally =
the rock-paper-scissors apex. Sole weakness: dragapult spread (rare)."""
import json, os, re, shutil, tarfile
HERE = os.path.dirname(__file__); REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
POL = os.path.join(REPO, 'workspace', 'exp002_baselines', 'policies', 'lucario_v2.py')
CG = os.path.join(REPO, 'data', 'sim_sample', 'cg'); BUILD = os.path.join(HERE, 'build_v006')
DECK = json.load(open(os.path.join(HERE, 'charmq_deck.json')))
SAFETY = '''

# ===== crash-safety wrapper (v006) =====
def _legal_fallback(select):
    n=len(select.option)
    return [] if n==0 else list(range(min(max(1,select.minCount),n)))
def _valid(sel,select):
    n=len(select.option)
    if not isinstance(sel,list) or any((not isinstance(i,int)) or i<0 or i>=n for i in sel): return False
    if len(set(sel))!=len(sel): return False
    return select.minCount<=len(sel)<=select.maxCount
def agent(obs_dict):
    try: obs=to_observation_class(obs_dict)
    except Exception:
        return list(my_deck) if obs_dict.get("select") is None else [0]
    if obs.select is None: return list(my_deck)
    try:
        sel=_base_agent(obs_dict)
        return sel if _valid(sel,obs.select) else _legal_fallback(obs.select)
    except Exception:
        return _legal_fallback(obs.select)
'''
src = open(POL).read(); src = re.sub(r"\bdef agent\(", "def _base_agent(", src)
os.makedirs(BUILD, exist_ok=True)
open(os.path.join(BUILD, 'main.py'), 'w').write(src.rstrip() + "\n" + SAFETY)
assert len(DECK) == 60, len(DECK)
open(os.path.join(BUILD, 'deck.csv'), 'w').write("\n".join(map(str, DECK)) + "\n")
dst = os.path.join(BUILD, 'cg')
if os.path.exists(dst): shutil.rmtree(dst)
shutil.copytree(CG, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
tarp = os.path.join(BUILD, 'submission.tar.gz')
with tarfile.open(tarp, 'w:gz') as tar:
    tar.add(os.path.join(BUILD, 'main.py'), arcname='main.py')
    tar.add(os.path.join(BUILD, 'deck.csv'), arcname='deck.csv')
    for root, _d, files in os.walk(dst):
        for fn in files:
            if fn.endswith(('.pyc', '.pyo')): continue
            full = os.path.join(root, fn); tar.add(full, arcname=os.path.join('cg', os.path.relpath(full, dst)))
names = tarfile.open(tarp).getnames()
assert {'main.py', 'deck.csv', 'cg/api.py', 'cg/libcg.so'} <= set(names)
print('built', tarp, '| top:', sorted(n for n in names if '/' not in n), 'files', len(names))
