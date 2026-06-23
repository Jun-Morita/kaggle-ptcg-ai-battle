"""v009 discipline + SETUP-BENCH discipline (exp021) = v010 candidate.

Finding (official disc 708586 + code read): the base policy has NO scoring branch
for SETUP_BENCH_POKEMON, so every setup-bench option scores 0 and choose() returns
ranked[:maxCount] = it benches EVERY Basic in hand during setup. Per the official
host clarification, when select.minCount==0 you may bench a SUBSET (return []/fewer).

Thesis (prize-liability discipline, same as v009): each benched Basic is a future
1-prize KO target. Benching every Basic at setup over-commits before we've seen the
game; we can play needed Basics from hand on later turns instead. So we bench only
valued line pieces, capped at _SETUP_BENCH_CAP, but ALWAYS keep >=1 backup so a KO'd
active never loses us the game outright. vs a stall wall (Crustle) we still develop
fully (defer to base), because there we must race to set up, not ration.

Cap is read from env SETUP_BENCH_CAP (default 3) so the experiment can sweep it.
Everything else identical to v009 (exp018 discipline). PATCH_SRC is consumed by
scripts/build_submission.py.
"""
from __future__ import annotations
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
for _p in (os.path.join(_ROOT, "workspace", "exp001_harness"),
           os.path.join(_ROOT, "workspace", "exp013_router"),
           os.path.join(_ROOT, "workspace", "exp018_adaptive")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import discipline_policy as D  # exp018 v009 discipline (already includes router base)

_SETUP_BENCH_CAP = int(os.environ.get("SETUP_BENCH_CAP", "3"))

_SETUP_SRC = '''
# ===== exp021 setup-bench discipline (non-ex only) =====
_SETUP_BENCH_CAP = %d

def _setup_bench_priority(self, card):
    if card is None or not isinstance(card, Pokemon):
        return -1
    cid = card.id
    if cid == _PHANTUMP:   return 100   # Trevenant fuel: worth committing early
    if cid == _DUNSPARCE:  return 80    # draw engine
    if cid == _CRAMORANT:  return 40    # situational attacker
    if cid == _SNORLAX:    return 30    # one backup attacker
    return 10                           # any other Basic: low-value backup

_orig_choose_v010 = LucarioPolicy.choose
def _disc_setup_choose(self):
    if (self.context == SelectContext.SETUP_BENCH_POKEMON and _DECK_NONEX
            and not _opp_is_wall(self) and self.select.minCount == 0):
        scored = []
        for i, opt in enumerate(self.select.option):
            card = get_card(self.obs, opt.area, opt.index, opt.playerIndex)
            scored.append((_setup_bench_priority(self, card), i))
        scored.sort(key=lambda t: t[0], reverse=True)
        chosen = [i for s, i in scored if s > 0][:_SETUP_BENCH_CAP]
        if not chosen and scored:           # always keep one backup if a Basic exists
            chosen = [scored[0][1]]
        return chosen[: self.select.maxCount]
    return _orig_choose_v010(self)
LucarioPolicy.choose = _disc_setup_choose
''' % (_SETUP_BENCH_CAP,)

PATCH_SRC = D.PATCH_SRC + "\n" + _SETUP_SRC

_n = [0]


def make_agent(deck):
    import router_policy as R
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"setupb_{_n[0]}", os.path.join(R.POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(R.POLICIES)
        with open("deck.csv", "w") as f:
            f.write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    exec(PATCH_SRC, mod.__dict__)

    def agent(obs_dict):
        o = mod.to_observation_class(obs_dict)
        return list(deck) if o.select is None else mod.agent(obs_dict)
    return agent
