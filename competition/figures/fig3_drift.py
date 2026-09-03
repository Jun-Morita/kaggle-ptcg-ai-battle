"""Figure 3 -- the field rotates under a frozen agent, and it costs 60 rating points.

Two panels, one axis each (never a second y-scale). Left: share of the field by
archetype, emphasis form -- the two decks we lose to are in colour, everything else
recedes to gray. Right: our own measured matchup win rates applied to each day's
composition, with the agent held completely fixed.
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jpfont import use_jp
use_jp()
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
INK, INK2, MUTED, FAINT = "#0b0b0b", "#52514e", "#8a8880", "#cfcec8"
DRG, EBD, OURS = "#2a78d6", "#eb6834", "#184f95"

DAYS = ["08-08", "08-11", "08-13", "08-15"]
X = list(range(4))
SHARE = {
    "Dragapult ドラパルトex":  ([10.7, 18.9, 27.7, 34.2], DRG,   2.4),
    "ex-beatdown":          ([12.8,  9.9, 22.5, 27.3], EBD,   2.4),
    "Mixed-ex (ex4)":        ([18.9, 20.1,  9.3, 12.8], FAINT, 1.6),
    "Alakazam-type フーディン":  ([17.1, 14.1, 15.9, 12.8], FAINT, 1.6),
    "Grimmsnarl マリィのオーロンゲex (ours)": ([25.6, 18.6, 11.6,  6.1], MUTED, 1.8),
    "Lucario ex メガルカリオex": ([ 4.7, 11.7,  5.5,  3.1], FAINT, 1.6),
    "Crustle control イワパレス": ([ 6.0,  4.4,  6.7,  2.0], FAINT, 1.6),
}
WR_DAYS = ["08-09", "08-11", "08-13", "08-15"]
WR = [0.415, 0.403, 0.368, 0.334]
ELO = [0, -8, -35, -60]

fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.2, 6.3), dpi=220,
                               gridspec_kw={"width_ratios": [1.35, 1]})
fig.patch.set_facecolor(SURFACE)

# ------------------------------------------------------------------ left panel
axL.set_facecolor(SURFACE)
for y in (10, 20, 30):
    axL.axhline(y, color="#eeede9", lw=1, zorder=0)
# de-collide the right-hand labels: keep >= 2.4 units of vertical space
order = sorted(SHARE.items(), key=lambda kv: -kv[1][0][-1])
ypos, last = {}, None
for name, (vals, col, lw) in order:
    y = vals[-1] if last is None else min(vals[-1], last - 2.4)
    ypos[name] = y
    last = y
for name, (vals, col, lw) in SHARE.items():
    z = 3 if col in (DRG, EBD) else 2
    axL.plot(X, vals, "-", color=col, lw=lw, zorder=z, solid_capstyle="round")
    axL.plot([X[-1]], [vals[-1]], "o", ms=7 if z == 3 else 5, color=col, zorder=z,
             markeredgecolor=SURFACE, markeredgewidth=1.6)
    bold = z == 3
    axL.text(3.09, ypos[name], f"  {name}  {vals[-1]:.1f}%", va="center", fontsize=8.3,
             color=INK if bold else MUTED, fontweight="bold" if bold else "normal")

axL.text(0.02, 37.5, "the two decks we lose to:  23.5%  →  61.5%",
         fontsize=9.2, color=INK, fontweight="bold")
axL.set_xticks(X); axL.set_xticklabels(DAYS, fontsize=9, color=INK2)
axL.set_xlim(-0.08, 5.9); axL.set_ylim(0, 40)
axL.set_yticks([0, 10, 20, 30])
axL.set_yticklabels(["0", "10", "20", "30%"], fontsize=9, color=INK2)
axL.set_xlabel("2026", fontsize=9, color=MUTED, labelpad=6)
axL.set_title("The field rotated in one week", fontsize=11, color=INK,
              fontweight="bold", loc="left", pad=10)

# ----------------------------------------------------------------- right panel
axR.set_facecolor(SURFACE)
for y in (0.35, 0.40):
    axR.axhline(y, color="#eeede9", lw=1, zorder=0)
axR.plot(X, WR, "-o", color=OURS, lw=2.4, ms=9, zorder=3,
         markeredgecolor=SURFACE, markeredgewidth=2)
for x, (w, e) in enumerate(zip(WR, ELO)):
    axR.text(x, w + 0.0075, f"{w:.3f}", ha="center", fontsize=8.6, color=INK)
    if e:
        axR.text(x, w - 0.011, f"{e} Elo", ha="center", va="top", fontsize=8.3,
                 color=EBD, fontweight="bold")
axR.annotate("", xy=(2.78, 0.3385), xytext=(2.78, 0.4125),
             arrowprops=dict(arrowstyle="-|>", color=EBD, lw=1.4,
                             mutation_scale=11, shrinkA=3, shrinkB=3))
axR.text(2.67, 0.4285, "60 rating points, with the\nagent never touched",
         ha="right", va="top", fontsize=8.8, color=INK2, linespacing=1.5)

axR.set_xticks(X); axR.set_xticklabels(WR_DAYS, fontsize=9, color=INK2)
axR.set_xlim(-0.35, 3.35); axR.set_ylim(0.315, 0.435)
axR.set_yticks([0.35, 0.40])
axR.set_yticklabels(["0.35", "0.40"], fontsize=9, color=INK2)
axR.set_xlabel("2026", fontsize=9, color=MUTED, labelpad=6)
axR.set_title("A frozen agent's expected win rate", fontsize=11, color=INK,
              fontweight="bold", loc="left", pad=10)

for ax in (axL, axR):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#e6e5e0")
    ax.tick_params(length=0)

fig.suptitle("An evaluation result without a date on it does not reproduce",
             x=0.008, y=0.978, ha="left", fontsize=13, color=INK, fontweight="bold")
fig.text(0.008, 0.921,
         "The right panel holds our measured per-matchup win rates fixed and swaps "
         "only the field composition.",
         ha="left", fontsize=9, color=INK2)
fig.subplots_adjust(left=0.055, right=0.995, top=0.825, bottom=0.105, wspace=0.30)
out = __file__.replace(".py", ".png")
fig.savefig(out, facecolor=SURFACE)
print("wrote", out)
