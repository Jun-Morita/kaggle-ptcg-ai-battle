"""Figure 5 -- the ledger of what we tested.

More than seven rows that all carry meaning, so this is a table rather than a
chart, with a small shared axis for the rows that were scored on the same
gauntlet. Bar = the score of the build we were trying to beat (0.6640).
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jpfont import use_jp
use_jp()
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8880"
PASS_C, FAIL_C = "#0ca30c", "#eb6834"      # status: good / the rejected lanes
BAR = 0.6640

#  lane, what changed, tries, gate score or None, verdict text, passed
ROWS = [
    ("Corpus size",   "12 → 46 days of teacher games",        "8",  0.6604, "best still short of the bar", False),
    ("Features",      "+118 opponent-card columns",           "5",  0.6438, "cost 0.020",                  False),
    ("Model capacity","more leaves, more rounds",             "—",  None,   "no effect either way",        False),
    ("Rival decks",   "our features piloting 5 other decks",  "5",  None,   "best clone 0.542 vs our 0.718", False),
    ("Corpus mix",    "match opponent shares to the field",   "1",  None,   "z −3.06, significantly worse", False),
    ("Row weights",   "×3 on one losing matchup (15%)",       "1",  0.6806, "+0.0167 — the only pass",     True),
    ("Row weights",   "stronger, and on three matchups",      "2",  0.6627, "past the optimum, falls back", False),
    ("Search",        "lookahead on top of the ranker",       "2",  None,   "made the agent weaker",       False),
    ("Neural policy", "behaviour-cloned transformer",         "—",  None,   "negative on the real ladder", False),
    ("Evaluation",    "paired shuffle seeds (CRN)",           "1",  None,   "4.66× less variance — adopted", True),
]

fig, ax = plt.subplots(figsize=(11.4, 5.0), dpi=220)
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
ax.set_xlim(0, 100); ax.set_ylim(6, 100); ax.axis("off")

TOP, ROWH = 82.0, 7.3
X_LANE, X_WHAT, X_N, X_AX0, X_AX1, X_NOTE = 1.0, 15.0, 44.5, 48.5, 66.5, 68.5


def sx(v):                       # gauntlet score -> x on the mini axis
    lo, hi = 0.630, 0.690
    return X_AX0 + (v - lo) / (hi - lo) * (X_AX1 - X_AX0)


# header
ax.text(X_LANE, TOP + 5.2, "LANE", fontsize=8.2, color=MUTED, fontweight="bold")
ax.text(X_WHAT, TOP + 5.2, "WHAT WE CHANGED", fontsize=8.2, color=MUTED, fontweight="bold")
ax.text(X_N + 1.4, TOP + 5.2, "TRIES", fontsize=8.2, color=MUTED, fontweight="bold", ha="center")
ax.text((X_AX0 + X_AX1) / 2, TOP + 5.2, "GAUNTLET SCORE", fontsize=8.2, color=MUTED,
        fontweight="bold", ha="center")
ax.text(X_NOTE, TOP + 5.2, "OUTCOME", fontsize=8.2, color=MUTED, fontweight="bold")
ax.plot([X_LANE, 99], [TOP + 3.4, TOP + 3.4], color="#dcdbd6", lw=1)

# the bar we were trying to beat
ybot = TOP - len(ROWS) * ROWH + ROWH - 2.2
ax.plot([sx(BAR), sx(BAR)], [ybot - 3.0, TOP + 2.0], color="#dcdbd6", lw=1.2, zorder=0)
ax.text(sx(BAR), ybot - 4.6, "the build we had to beat: 0.6640",
        fontsize=7.8, color=MUTED, ha="center")

for i, (lane, what, n, score, note, ok) in enumerate(ROWS):
    y = TOP - i * ROWH
    if i % 2 == 0:
        ax.add_patch(Rectangle((X_LANE - 0.6, y - 2.6), 99.2, ROWH - 0.7,
                               fc="#f6f5f1", ec="none", zorder=0))
    ax.text(X_LANE, y, lane, fontsize=9, color=INK, va="center",
            fontweight="bold" if ok else "normal")
    ax.text(X_WHAT, y, what, fontsize=8.7, color=INK2, va="center")
    ax.text(X_N + 1.4, y, n, fontsize=8.7, color=INK2, va="center", ha="center")
    if score is not None:
        c = PASS_C if ok else FAIL_C
        ax.plot([sx(score)], [y], "o", ms=8.5, color=c, zorder=3,
                markeredgecolor=SURFACE, markeredgewidth=1.8)
        ax.text(sx(score), y - 3.1, f"{score:.4f}", fontsize=7.6, color=c, ha="center")
    else:
        rowbg = "#f6f5f1" if i % 2 == 0 else SURFACE
        ax.text((X_AX0 + X_AX1) / 2, y, "not comparable", fontsize=7.8, color=MUTED,
                va="center", ha="center", style="italic", zorder=3,
                bbox=dict(fc=rowbg, ec="none", pad=1.5))
    ax.text(X_NOTE, y, note, fontsize=8.7, va="center",
            color=PASS_C if ok else INK2, fontweight="bold" if ok else "normal")

fig.suptitle("Ten lanes tested, one clean pass on our own gauntlet",
             x=0.008, y=0.968, ha="left", fontsize=13, color=INK, fontweight="bold")
fig.text(0.008, 0.902,
         "Every lane was judged by the gauntlet in Figure 1, which is the point of "
         "this report. Only the evaluation lane was judged by something else.",
         ha="left", fontsize=9, color=INK2)
fig.subplots_adjust(left=0.008, right=0.995, top=0.86, bottom=0.02)
out = __file__.replace(".py", ".png")
fig.savefig(out, facecolor=SURFACE)
print("wrote", out, "| recorded runs:", sum(int(r[2]) for r in ROWS if r[2].isdigit()))
