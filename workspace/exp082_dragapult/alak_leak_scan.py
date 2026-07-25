"""exp083 (in exp082 dir) -- ground-truth loss-mode diagnostic on koff's REAL
ladder replays (avoid the local!=ladder trap: diagnose from actual ladder games,
not local pilots). For koff's WINNABLE-but-underperforming matchups (Alakazam
mixed_ex1 ~0.46, non_ex ~0.50), split wins vs losses by the pre-terminal state:
is koff losing a prize RACE (opp takes 6 prizes before koff mills = structural,
like Grimmsnarl) or failing to CLOSE a mill it should (koff deck-out / stalled =
patchable mechanism leak, the v030-Dunsparce class)?

Usage: uv run python koff_leak_scan.py
"""
from __future__ import annotations
import os, sys, json, glob, collections, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
if "--crn" not in sys.argv:
    sys.argv.append("--crn")
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
sys.path.insert(0, EB.CRN)
from harness_crn import load_engine
sys.path.insert(0, os.path.join(WS, "exp011_meta_watch"))

REPLAY_DIR = os.path.join(ROOT, "references", "raw", "replays", "0725_54936709")
KOFF_DECK = [int(x) for x in open(os.path.join(WS, "exp057_pubalakazam", "agent", "deck.csv")).read().split()[:60]]


def deck_of(steps, seat):
    for st_ in steps:
        if seat < len(st_):
            a = (st_[seat] or {}).get("action")
            if isinstance(a, list) and len(a) == 60:
                return [int(x) for x in a]
    return None


def pre_terminal_state(steps, seat):
    """Walk backward to the last step with a usable observation; return
    (turn, my_deckCount, opp_deckCount, my_prize_left, opp_prize_left)."""
    from cg.api import to_observation_class
    for st_ in reversed(steps):
        if seat >= len(st_):
            continue
        obs_d = (st_[seat] or {}).get("observation")
        if not obs_d:
            continue
        try:
            o = to_observation_class(obs_d)
            cur = o.current
            if cur is None or cur.players is None:
                continue
            mi = cur.yourIndex
            ps = cur.players
            return (cur.turn, ps[mi].deckCount, ps[1 - mi].deckCount,
                    len(ps[mi].prize), len(ps[1 - mi].prize))
        except Exception:
            continue
    return None


def main():
    load_engine()
    import analyze as A
    from cg.api import all_card_data
    byid = {c.cardId: c for c in all_card_data()}

    files = sorted(glob.glob(os.path.join(REPLAY_DIR, "*.json")))
    print(f"replays={len(files)}  koff deck archetype={A.archetype(KOFF_DECK, byid)}", flush=True)

    by = collections.defaultdict(lambda: {"W": [], "L": []})
    self_play = 0
    for f in files:
        d = json.load(open(f))
        steps = d.get("steps", [])
        rw = d.get("rewards") or []
        tn = (d.get("info") or {}).get("TeamNames") or []
        if len(rw) < 2 or rw[0] is None or rw[1] is None:
            continue
        decks = [deck_of(steps, 0), deck_of(steps, 1)]
        if not decks[0] or not decks[1]:
            continue
        # our seat = the one whose deck matches koff (crustle_control with our exact list)
        our = 0 if collections.Counter(decks[0]) == collections.Counter(KOFF_DECK) else (
              1 if collections.Counter(decks[1]) == collections.Counter(KOFF_DECK) else -1)
        if our == -1:
            self_play += 1  # neither seat is our exact koff (shouldn't happen)
            continue
        opp = 1 - our
        opp_arch = A.archetype(decks[opp], byid)
        if collections.Counter(decks[opp]) == collections.Counter(KOFF_DECK):
            self_play += 1
            continue
        res = "W" if rw[our] > rw[opp] else ("L" if rw[our] < rw[opp] else "D")
        if res == "D":
            continue
        snap = pre_terminal_state(steps, our)
        by[opp_arch][res].append(snap)

    print(f"self-play/skipped={self_play}\n")
    print("koff real-ladder loss-mode by opponent archetype (median pre-terminal):")
    print(f"  {'archetype':18} {'W-L':>7} {'wr':>5} | {'turn':>10} {'myDeck':>8} {'oppDeck':>8} {'myPz':>6} {'oppPz':>6}")
    def med(rows, idx):
        vals = [r[idx] for r in rows if r]
        return st.median(vals) if vals else float("nan")
    for arch in sorted(by, key=lambda a: -(len(by[a]["W"]) + len(by[a]["L"]))):
        W, L = by[arch]["W"], by[arch]["L"]
        n = len(W) + len(L)
        wr = len(W) / n if n else 0
        for tag, rows in [("WIN ", W), ("LOSS", L)]:
            if not rows:
                continue
            print(f"  {arch:18} {tag} {len(rows):>2}     | turn~{med(rows,0):>5.0f} "
                  f"myDeck~{med(rows,1):>5.0f} oppDeck~{med(rows,2):>5.0f} "
                  f"myPz~{med(rows,3):>4.0f} oppPz~{med(rows,4):>4.0f}"
                  + (f"   [{arch} wr={wr:.2f} n={n}]" if tag == "WIN " else ""))
    print("\nRead: koff mills opp DECK to 0. LOSS with oppDeck HIGH + oppPz LOW = prize-race\n"
          "loss (structural). LOSS with oppDeck LOW (koff nearly milled) or myDeck 0 (koff\n"
          "decked ITSELF) = a closable/patchable mill (mechanism leak).")


if __name__ == "__main__":
    main()
