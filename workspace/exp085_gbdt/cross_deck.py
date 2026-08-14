"""Score candidates that play DIFFERENT DECKS on the same field.

The single-deck gate cannot compare across decks: its "mirror" cell means one
thing for a Grimmsnarl build and another for a Mega Lopunny ex build. Here every
row is the same seven opponents, and each candidate's own archetype is its 0.500
self-mirror.

Two weightings are printed on purpose. The observed one is what our own ladder
games actually contained (v059's 65 games); the 08-12 one is the whole field's
archetype mix that day, which is where the ladder is heading -- our archetype
fell 63.3% -> 14.1% in twelve days while dragapult went 4.0% -> 25.8%.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CELLS = ["ex3", "ex1", "ex4", "dragapult", "ebd", "crustle", "lucario"]
W_OBS = dict(ex3=.38, ex1=.22, ex4=.14, dragapult=.05, ebd=.03, crustle=.06, lucario=.05)
W_812 = dict(ex3=.141, ex1=.114, ex4=.158, dragapult=.258, ebd=.206, crustle=.053, lucario=.066)
# which archetype each build IS, so its own cell is the 0.500 self-mirror
DECK_OF = {"v10rL": "ex3", "v13": "ex3", "v9b": "ex3", "d0812": "ex3",
           "ex4c": "ex4", "ebd": "ebd", "drg": "dragapult",
           "luc": "lucario", "ak": "ex1"}


def read(tag, cell):
    for name in (f"gg_{tag}_{cell}.log", f"xd_{tag}_{cell}.log"):
        p = os.path.join(HERE, name)
        if os.path.exists(p):
            m = re.findall(r"wr (\d\.\d+)", open(p).read())
            if m:
                return float(m[-1])
    return None


def row(tag):
    v = {}
    for c in CELLS:
        v[c] = 0.500 if DECK_OF.get(tag) == c else read(tag, c)
    return v


def total(v, W):
    have = {c: x for c, x in v.items() if x is not None}
    s = sum(W[c] for c in have)
    return sum(W[c] * have[c] for c in have) / s if s else float("nan")


def main():
    tags = sys.argv[1:]
    rows = {t: row(t) for t in tags}
    print(f"  {'cell':<11}{'w_obs':>7}{'w_0812':>8}" + "".join(f"{t:>10}" for t in tags))
    for c in CELLS:
        print(f"  {c:<11}{W_OBS[c]:>7.2f}{W_812[c]:>8.3f}" +
              "".join(f"{rows[t][c]:>10.3f}" if rows[t][c] is not None else f"{'-':>10}"
                      for t in tags))
    print(f"  {'TOTAL obs':<11}{'':>15}" + "".join(f"{total(rows[t], W_OBS):>10.4f}" for t in tags))
    print(f"  {'TOTAL 0812':<11}{'':>15}" + "".join(f"{total(rows[t], W_812):>10.4f}" for t in tags))
    miss = {t: [c for c in CELLS if rows[t][c] is None] for t in tags}
    for t, m in miss.items():
        if m:
            print(f"  missing {t}: {m}")


if __name__ == "__main__":
    main()
