"""1-D sweep of the 3 real-strategy constants, each config in an isolated subprocess.

Holds the other two at baseline (0) while sweeping one. Baseline (0,0,0) == v010.
Robust gate: a config is a candidate only if it IMPROVES the mirror (our weakness) AND
does not regress ex/crustle/dragapult beyond noise. Weighted field score is a guide.
Usage: uv run python sweep.py [n_per_matchup]
"""
from __future__ import annotations
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
# field weights (from meta-watch shares; dragapult over-weighted as a stress test)
W = {"ex": 0.45, "mirror_v010": 0.30, "crustle": 0.13, "dragapult": 0.12}

SWEEP = [
    ("REVENGE_BONUS", [0, 50, 100, 130]),
    ("PRIZE_W",       [0, 300, 600, 1000]),
    ("BACKUP_CHARGE", [0, 1]),
]


def run(env_over, n):
    env = dict(os.environ, REVENGE_BONUS="0", PRIZE_W="0", BACKUP_CHARGE="0")
    env.update({k: str(v) for k, v in env_over.items()})
    p = subprocess.run([sys.executable, os.path.join(_HERE, "eval_one.py"), str(n)],
                       capture_output=True, text=True, env=env)
    line = [l for l in p.stdout.splitlines() if l.startswith("{")]
    if not line:
        print("FAILED:", env_over, p.stderr[-400:]); return None
    return json.loads(line[-1])


def field(m):
    return round(sum(W[k] * m[k]["wr"] for k in W), 3)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    print(f"# exp023 constant sweep, n={n}/matchup, subprocess-isolated. baseline(0,0,0)=v010\n")
    base = run({}, n)
    bm = base["matchups"]
    print(f"{'config':28s} {'mirror':>7s} {'ex':>6s} {'crus':>6s} {'drag':>6s} {'field':>6s} {'errs':>5s}")
    def show(tag, m):
        errs = sum(m[k]["err_self"] for k in W)
        print(f"{tag:28s} {m['mirror_v010']['wr']:7.3f} {m['ex']['wr']:6.3f} "
              f"{m['crustle']['wr']:6.3f} {m['dragapult']['wr']:6.3f} {field(m):6.3f} {errs:5d}")
    show("BASELINE(0,0,0)=v010", bm)
    print()
    results = {"baseline": base}
    for const, vals in SWEEP:
        for v in vals:
            if v == 0:
                continue
            r = run({const: v}, n)
            if r is None:
                continue
            results[f"{const}={v}"] = r
            show(f"{const}={v}", r["matchups"])
        print()
    json.dump(results, open(os.path.join(_HERE, "sweep_results.json"), "w"), indent=1)
    print("saved sweep_results.json")


if __name__ == "__main__":
    main()
