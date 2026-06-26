"""Decode the TR-engine tutor chain from a top player's cached replays.

For each TO_HAND (search) decision, record WHAT card they fetch, plus per-game tutor
PLAY rates. Shows the target fetch-priority our _score_to_hand must reproduce.
Usage: uv run python decode_tutor.py <replay_dir> <name_substring>
"""
from __future__ import annotations
import csv, glob, json, os, sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
names = {}
with open(os.path.join(ROOT, "data", "raw", "EN_Card_Data.csv")) as f:
    for r in csv.DictReader(f):
        names[int(r["Card ID"])] = r["Card Name"]
cn = lambda c: names.get(c, f"#{c}")

T_PLAY = 7
TUTORS = {1134: "Transceiver", 1219: "Petrel", 1225: "Hilda", 1092: "SecretBox",
          1122: "Pokegear", 1152: "PokePad", 1115: "HopsBag", 1227: "Lillie", 1197: "Xerosic"}


def pidx(d, sub):
    tn = (d.get("info") or {}).get("TeamNames") or []
    return next((i for i, n in enumerate(tn) if sub.lower() in str(n).lower()), None)


def main():
    pdir, sub = sys.argv[1], sys.argv[2]
    files = sorted(glob.glob(os.path.join(ROOT, "references", "raw", "replays", pdir, "*.json")))
    fetched = Counter()           # card fetched in TO_HAND (context 2)
    tutor_plays = Counter()
    ngames = 0
    for path in files:
        try: d = json.load(open(path))
        except Exception: continue
        idx = pidx(d, sub)
        if idx is None: continue
        ngames += 1
        for st in d.get("steps", []):
            if idx >= len(st): continue
            ag = st[idx]; obs, act = ag.get("observation"), ag.get("action")
            if not isinstance(obs, dict) or not act: continue
            sel = obs.get("select")
            if not sel: continue
            ctx = sel.get("context"); opts = sel.get("option", [])
            if not opts or len(opts) == 60: continue
            cur = obs.get("current") or {}
            me = (cur.get("players") or [None, None])[idx]
            if me is None: continue
            # TO_HAND search fetches (context 2)
            if ctx == 2:
                for ci in act:
                    if isinstance(ci, int) and ci < len(opts):
                        o = opts[ci]
                        c = o.get("cardId") or o.get("id")
                        if c: fetched[cn(int(c))] += 1
            # tutor PLAYS (context 0)
            if ctx == 0:
                hand = me.get("hand") or []
                for ci in act:
                    if isinstance(ci, int) and ci < len(opts):
                        o = opts[ci]
                        if o.get("type") == T_PLAY:
                            hi = o.get("index")
                            cid = hand[hi].get("id") if (hi is not None and hi < len(hand)) else None
                            if cid in TUTORS: tutor_plays[TUTORS[cid]] += 1
    print(f"=== {sub}: {ngames} games ===")
    print("\ntutor PLAYS per game:")
    for k, v in tutor_plays.most_common():
        print(f"  {k:14s} {v/ngames:.2f}/game ({v})")
    print("\nTO_HAND fetches (what they search out):")
    tot = sum(fetched.values()) or 1
    for k, v in fetched.most_common(20):
        print(f"  {k:28s} {v:4d} ({100*v//tot}%)")


if __name__ == "__main__":
    main()
