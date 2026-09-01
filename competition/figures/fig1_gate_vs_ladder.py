"""Figure 1 -- what our offline gate predicted vs what the ladder actually did.

Dumbbell (the "before -> after per item" form): one row per opponent archetype,
one hue in two shades, direct labels on both ends because the light shade sits
below 3:1 on the surface. Sorted by the archetype's share of the real field, so
the reader's eye lands on the two rows that matter most.

Data: 6,292 ladder games, 2026-08-13..15, restricted to seats running our exact
60-card list (matchup_matrix.py). Gate values are the frozen 6-cell gauntlet.
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jpfont import use_jp
use_jp()
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8880"
GATE, REAL = "#6da7ec", "#184f95"      # validated pair: CVD dE 28.8, band+chroma PASS

#  label                    gate    real    n    field share %
ROWS = [
    ("Dragapult\nドラパルトex",        0.865, 0.341, 264, 34.2),
    ("ex-beatdown",                 None, 0.193, 238, 27.3),
    ("Mixed-ex (ex4)",             0.514, 0.371, 213, 12.8),
    ("Alakazam-type\nフーディン",      0.864, 0.421, 183, 12.8),
    ("Mirror\nマリィのオーロンゲex",    0.580, 0.474, 173,  6.1),
    ("Lucario ex\nメガルカリオex",     0.685, 0.524,  42,  3.1),
    ("Crustle control\nイワパレス",    0.800, 0.619,  42,  2.0),
]

fig, ax = plt.subplots(figsize=(9.6, 5.0), dpi=220)
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

ys = list(range(len(ROWS)))[::-1]
for y, (name, gate, real, n, share) in zip(ys, ROWS):
    if gate is not None:
        ax.plot([real, gate], [y, y], color="#d9d8d3", lw=2, zorder=1,
                solid_capstyle="round")
        ax.plot([gate], [y], "o", ms=9, color=GATE, zorder=3,
                markeredgecolor=SURFACE, markeredgewidth=2)
        ax.text(gate + 0.018, y, f"{gate:.3f}", va="center", ha="left",
                fontsize=8.5, color=INK2)
    ax.plot([real], [y], "o", ms=9, color=REAL, zorder=3,
            markeredgecolor=SURFACE, markeredgewidth=2)
    ax.text(real - 0.018, y, f"{real:.3f}", va="center", ha="right",
            fontsize=8.5, color=INK, fontweight="bold")

ax.axvline(0.5, color="#e6e5e0", lw=1.5, zorder=0)
ax.text(0.5, len(ROWS) - 0.35, "even", fontsize=8, color=MUTED, ha="center")

# the row with no gate cell at all is the point of the figure -- say so on the row
ax.annotate("no cell in the gate at all — and it was 27.3% of the field",
            xy=(0.215, ys[1]), xytext=(0.30, ys[1]),
            fontsize=9, color=INK2, va="center", ha="left",
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=1,
                            shrinkA=0, shrinkB=4))

ax.set_yticks(ys)
ax.set_yticklabels([r[0] for r in ROWS], fontsize=9.0, color=INK,
                   linespacing=1.4)
ax.set_xlim(0.10, 1.02)
ax.set_ylim(-0.9, len(ROWS) - 0.05)
ax.set_xticks([0.2, 0.4, 0.5, 0.6, 0.8, 1.0])
ax.set_xticklabels(["0.2", "0.4", "0.5", "0.6", "0.8", "1.0"], fontsize=9, color=INK2)
ax.set_xlabel("win rate with our exact 60 cards", fontsize=9.5, color=INK2, labelpad=8)

# field share as a right-hand annotation column, not a second axis
for y, r in zip(ys, ROWS):
    ax.text(1.055, y, f"{r[4]:.1f}%", transform=ax.get_yaxis_transform(),
            va="center", ha="right", fontsize=8.5,
            color=INK if r[4] >= 12 else MUTED)
ax.text(1.055, len(ROWS) - 0.55, "share of\nthe field", transform=ax.get_yaxis_transform(),
        va="center", ha="right", fontsize=8, color=MUTED, linespacing=1.4)

for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color("#e6e5e0")
ax.tick_params(axis="both", length=0)
ax.grid(False)

ax.legend(handles=[
    Line2D([], [], marker="o", ls="", ms=8, color=GATE, label="our offline gate predicted"),
    Line2D([], [], marker="o", ls="", ms=8, color=REAL, label="measured on the real ladder"),
], loc="upper left", frameon=False, fontsize=9, labelcolor=INK2,
   handletextpad=0.5, borderaxespad=0.0, bbox_to_anchor=(-0.01, 1.02))

fig.suptitle("Every cell overstated us, and not by the same amount",
             x=0.012, y=0.975, ha="left", fontsize=13.5, color=INK, fontweight="bold")
fig.text(0.012, 0.905,
         "6,292 ladder games, 2026-08-13..15, seats running our exact list. "
         "Field-weighted true win rate: 0.33.",
         ha="left", fontsize=9, color=INK2)

fig.subplots_adjust(left=0.215, right=0.90, top=0.83, bottom=0.13)
out = __file__.replace(".py", ".png")
fig.savefig(out, facecolor=SURFACE)
print("wrote", out)
