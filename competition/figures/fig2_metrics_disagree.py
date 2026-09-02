"""Figure 2 -- our two internal metrics select different models.

Both are rates on the same 0-1 scale, so they share one axis (never two).
Four corpus sizes, held-out imitation accuracy against gate score. The point is
the crossing at the end: the most accurate imitator is not the best-scoring agent,
and neither metric has anything external to check it against.
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jpfont import use_jp
use_jp()
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8880"
ACC, GATE = "#2a78d6", "#eb6834"      # validated pair: CVD dE 24.7, all checks PASS

LABELS = ["236k", "458k", "1.4M", "2.4M"]
ACCV = [0.7096, 0.7054, 0.7098, 0.7323]
GATEV = [0.5886, 0.6279, 0.6604, 0.6455]
X = list(range(4))

fig, ax = plt.subplots(figsize=(8.2, 5.9), dpi=220)
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)

for y in (0.60, 0.65, 0.70):
    ax.axhline(y, color="#eeede9", lw=1, zorder=0)

ax.plot(X, ACCV, "-o", color=ACC, lw=2, ms=8, zorder=3,
        markeredgecolor=SURFACE, markeredgewidth=2)
ax.plot(X, GATEV, "-o", color=GATE, lw=2, ms=8, zorder=3,
        markeredgecolor=SURFACE, markeredgewidth=2)

for x, v in zip(X, ACCV):
    if x == 3:
        ax.text(x + 0.13, v, f"{v:.4f}", ha="left", va="center", fontsize=8.4, color=INK2)
    else:
        ax.text(x, v + 0.0085, f"{v:.4f}", ha="center", fontsize=8.4, color=INK2)
for x, v in zip(X, GATEV):
    ax.text(x, v - 0.0135, f"{v:.4f}", ha="center", fontsize=8.4, color=INK2)

# ring the winner of each metric -- they are different models
ax.plot([3], [ACCV[3]], "o", ms=17, mfc="none", mec=ACC, mew=1.6, zorder=2)
ax.plot([2], [GATEV[2]], "o", ms=17, mfc="none", mec=GATE, mew=1.6, zorder=2)
ax.annotate("most accurate imitator", xy=(3, ACCV[3] + 0.011), xytext=(2.55, 0.752),
            fontsize=8.6, color=ACC, ha="center",
            arrowprops=dict(arrowstyle="-", color=ACC, lw=1, shrinkA=1, shrinkB=6))
ax.annotate("strongest agent", xy=(2 + 0.055, GATEV[2] + 0.009), xytext=(2.62, 0.684),
            fontsize=8.6, color=GATE, ha="center",
            arrowprops=dict(arrowstyle="-", color=GATE, lw=1, shrinkA=1, shrinkB=4))

ax.text(3.30, 0.605, "the last step moves\nthem in opposite\ndirections",
        fontsize=8.4, color=INK2, va="center", ha="left", linespacing=1.5)

from matplotlib.lines import Line2D
ax.legend(handles=[
    Line2D([], [], marker="o", ls="-", lw=2, ms=7, color=ACC,
           label="held-out imitation accuracy (top-k)"),
    Line2D([], [], marker="o", ls="-", lw=2, ms=7, color=GATE,
           label="offline gate score"),
], loc="upper left", frameon=False, fontsize=9, labelcolor=INK2,
   handletextpad=0.6, borderaxespad=0.1, bbox_to_anchor=(-0.02, 1.03))

ax.set_xticks(X); ax.set_xticklabels(LABELS, fontsize=9.5, color=INK)
ax.set_xlabel("training decisions in the corpus", fontsize=9.5, color=INK2, labelpad=8)
ax.set_xlim(-0.30, 4.30)
ax.set_ylim(0.565, 0.775)
ax.set_yticks([0.60, 0.65, 0.70, 0.75])
ax.set_yticklabels(["0.60", "0.65", "0.70", "0.75"], fontsize=9, color=INK2)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color("#e6e5e0")
ax.tick_params(length=0)

fig.suptitle("Our two internal metrics pick different models",
             x=0.012, y=0.972, ha="left", fontsize=13, color=INK, fontweight="bold")
fig.text(0.012, 0.915,
         "Neither is checked against anything outside our own machine. "
         "The gate turned out to be the wrong one (Figure 1).",
         ha="left", fontsize=9, color=INK2)
fig.subplots_adjust(left=0.080, right=0.984, top=0.846, bottom=0.112)
out = __file__.replace(".py", ".png")
fig.savefig(out, facecolor=SURFACE)
print("wrote", out)
