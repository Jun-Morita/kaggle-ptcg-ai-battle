"""Weighted gate total for a tag, against the builds already measured.

Weights are the opponent mix observed on the ladder, not a guess: v057's 77
games gave 42/19/16/8/5/3 and v059's 65 games gave 38/22/14/6/5/5, so they are
stable to about 4pp. Update only on a 5pp move.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
W = {"mirror": .42, "alakazam": .19, "ex4": .16, "crustle": .08,
     "lucario": .05, "dragapult": .03}
N = {"mirror": 1200, "alakazam": 800, "ex4": 1200, "crustle": 200,
     "lucario": 400, "dragapult": 200}
KNOWN = {
    "v056 (evicted)": dict(mirror=.547, alakazam=.875, ex4=.459, crustle=.755,
                           lucario=.668, dragapult=.885),
    "v058 (live)":    dict(mirror=.593, alakazam=.876, ex4=.507, crustle=.725,
                           lucario=.665, dragapult=.815),
    "v059 (live)":    dict(mirror=.593, alakazam=.880, ex4=.493, crustle=.790,
                           lucario=.652, dragapult=.885),
    "v14":            dict(mirror=.569, alakazam=.876, ex4=.488, crustle=.785,
                           lucario=.675, dragapult=.865),
}


def read(tag, cell):
    p = os.path.join(HERE, f"gg_{tag}_{cell}.log")
    if not os.path.exists(p):
        return None
    m = re.findall(r"wr (\d\.\d+)", open(p).read())
    return float(m[-1]) if m else None


def total(v):
    return sum(W[c] * v[c] for c in W) / sum(W.values())


def main():
    tag = sys.argv[1]
    got = {c: read(tag, c) for c in W}
    missing = [c for c, v in got.items() if v is None]
    if missing:
        print(f"  missing cells: {missing}")
        return
    rows = dict(KNOWN); rows[tag] = got
    sd = sum((W[c] * (0.5 / N[c]) ** 0.5) ** 2 for c in W) ** 0.5 / sum(W.values())
    print(f"\n  {'cell':<11}{'w':>6}" + "".join(f"{k:>16}" for k in rows))
    for c in W:
        print(f"  {c:<11}{W[c]:>6.2f}" + "".join(f"{rows[k][c]:>16.3f}" for k in rows))
    print(f"  {'TOTAL':<11}{'':>6}" + "".join(f"{total(rows[k]):>16.4f}" for k in rows))
    d = total(got) - total(KNOWN["v059 (live)"])
    print(f"\n  {tag} - v059 = {d:+.4f}   z {d/sd:+.2f}   "
          f"{'CANDIDATE' if d > 0 else 'below the bar'}")


if __name__ == "__main__":
    main()
