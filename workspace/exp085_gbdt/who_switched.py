"""Did the top players we learn from switch decks, or did new players arrive?

The archetype mix moved hard -- mixed_ex3 (Grimmsnarl / オーロンゲ) went 71.5% on
07-31 to 25.6% on 08-08 -- but a share can fall two ways, and they mean opposite
things:

  the same strong pilots moved off it   -> they found something better, follow
  new players arrived on other decks    -> the field widened, our deck is fine

Episodes carry info.TeamNames, so the same team can be tracked across days. For
each team this records the archetype they piloted and the ladder score attached
to that seat, in an EARLY window and a LATE window, and reports the teams that
changed.

Usage: uv run python who_switched.py [--early 07-28,07-29,07-30,07-31]
                                     [--late 08-06,08-07,08-08] [--cap 500]
"""
from __future__ import annotations
import glob, json, os, sys, zipfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def collect(days, cap):
    """team -> Counter(archetype), and team -> best score seen."""
    arch = defaultdict(Counter)
    best = defaultdict(float)
    for day in days:
        p = os.path.join(HERE, "indices", f"2026-{day}.json")
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        z = zipfile.ZipFile(d["zip"])
        # one entry per (member, seat); the same episode can appear twice
        seen_member = {}
        for (m, seat, a, sc) in d["teachers"][:cap]:
            if m not in seen_member:
                try:
                    seen_member[m] = json.loads(z.read(m))["info"]["TeamNames"]
                except Exception:
                    seen_member[m] = None
            names = seen_member[m]
            if not names or seat >= len(names):
                continue
            t = names[seat]
            arch[t][a] += 1
            if sc is not None:
                best[t] = max(best[t], float(sc))
    return arch, best


def main():
    early = (arg("--early", "07-28,07-30,07-31")).split(",")
    late = (arg("--late", "08-06,08-07,08-08")).split(",")
    cap = int(arg("--cap", "500"))
    ea, eb = collect(early, cap)
    la, lb = collect(late, cap)
    both = [t for t in ea if t in la]
    print(f"early {early} teams={len(ea)}   late {late} teams={len(la)}   "
          f"seen in both={len(both)}")

    # teams that were on OUR archetype early
    was_grimm = [t for t in both if ea[t].most_common(1)[0][0] == "mixed_ex3"]
    now = Counter(la[t].most_common(1)[0][0] for t in was_grimm)
    print(f"\nof the {len(was_grimm)} teams piloting mixed_ex3 in the early window,"
          f" what they mainly play now:")
    for a, n in now.most_common():
        print(f"   {a:<20}{n:>5}{n/len(was_grimm):>8.1%}")

    stayed = now.get("mixed_ex3", 0)
    print(f"\n  stayed on mixed_ex3: {stayed}/{len(was_grimm)} "
          f"({stayed/max(1,len(was_grimm)):.1%})")

    # where the NEW top scores are
    print("\ntop 15 teams by late-window score, and their archetype")
    for t in sorted(lb, key=lambda x: -lb[x])[:15]:
        e = ea[t].most_common(1)[0][0] if t in ea else "-"
        l = la[t].most_common(1)[0][0]
        mark = "  SWITCHED" if (t in ea and e != l) else ""
        print(f"   {lb[t]:>7.1f}  {t[:24]:<25} {e:<18} -> {l:<18}{mark}")


if __name__ == "__main__":
    main()
