"""Figure 4 -- the deck's game plan as a mechanism, not a card list.

Two panels. Left: what the first two turns assemble, and the energy split that
makes the rest work. Right: the damage loop that converts 30-point chip damage
into prizes. One hue for our cards, gray for the opponent's board, one warm
accent reserved for damage.
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jpfont import use_jp
use_jp()
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8880"
OURS, OURS_L = "#184f95", "#dce9f9"
DMG = "#ec835a"                      # status: serious -- reserved for damage only
GRAYBOX = "#eeede9"

fig, ax = plt.subplots(figsize=(10.6, 5.6), dpi=220)
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
ax.set_xlim(0, 100); ax.set_ylim(0, 62); ax.axis("off")


def box(x, y, w, h, text, fc=OURS_L, ec=OURS, tc=INK, fs=8.6, bold=False, lw=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.6",
                                fc=fc, ec=ec, lw=lw, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, zorder=3, linespacing=1.45,
            fontweight="bold" if bold else "normal")


def arrow(x1, y1, x2, y2, color=OURS, lw=1.4, style="-|>", rad=0.0, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=11, color=color, lw=lw, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}", zorder=4,
                                 shrinkA=2, shrinkB=2))


# ---------------------------------------------------------------- panel titles
ax.text(0, 59.5, "1 · Turns 1–2 assemble the line", fontsize=10.5, color=INK,
        fontweight="bold")
ax.text(44, 59.5, "2 · Then the same loop runs every turn", fontsize=10.5,
        color=INK, fontweight="bold")
ax.plot([41.5, 41.5], [2, 57], color="#e6e5e0", lw=1.2, zorder=0)

# ------------------------------------------------------------------ left panel
box(0, 47.0, 12.2, 8.2, "Marnie's Impidimp  70\nマリィのベロバー", fs=7.6)
arrow(12.6, 51.1, 14.3, 51.1)
box(14.7, 47.0, 12.2, 8.2, "Marnie's Morgrem  100\nマリィのギモー", fs=7.6)
arrow(27.3, 51.1, 28.4, 51.1)
box(28.6, 45.5, 12.9, 11, "Marnie's Grimmsnarl ex\nマリィのオーロンゲex\nHP 320 · 2 Prize cards",
    bold=True, fc=OURS, ec=OURS, tc="#ffffff", fs=7.6)

ax.text(0, 43.6, "12 slots exist only to find these:\n"
                 "4 Spikemuth Gym · 4 Team Rocket's Petrel · 3 Rare Candy · 1 Dawn",
        fontsize=8.2, color=INK2, va="top", linespacing=1.5)

box(0, 29.5, 41.5, 8.5,
    "PUNK UP  ·  on evolving, search out up to 5 Basic {D}\nEnergy and attach to your Marnie's Pokémon",
    bold=True)
ax.text(11, 27.4, "The attacker never costs a hand attachment,\n"
                  "so the one per turn is free.",
        fontsize=8.4, color=INK2, va="top", linespacing=1.5)

arrow(5.5, 29.2, 5.5, 23.6)
box(2, 15.5, 37.5, 8,
    "your Energy attachment for the turn  →  MUNKIDORI マシマシラ\n(Adrena-Brain needs {D} attached)")
ax.text(20.7, 12.9, "median turn 2 · 145 of 145 winning seats",
        fontsize=8.4, color=INK, ha="center", fontweight="bold")
ax.text(20.7, 10.2, "and 40 of 40 games for our agent",
        fontsize=8.2, color=INK2, ha="center")

# ----------------------------------------------------------------- right panel
box(45.5, 45.0, 24.5, 10.5, "SHADOW BULLET\n180 to the Active Pokémon\n+30 to one Benched Pokémon",
    bold=True, fs=8.2)
box(74.5, 45.0, 24.0, 10.5, "FREEZING SHROUD · Froslass ユキメノコ\n1 damage counter on every Pokémon\nwith an Ability — both sides",
    fc=GRAYBOX, ec=MUTED, fs=7.8)
box(74.5, 26.5, 24.0, 10.0, "ADRENA-BRAIN · Munkidori マシマシラ\nmove up to 3 damage counters\nfrom ours to theirs",
    bold=True, fs=7.8)
box(45.5, 26.5, 24.5, 10.0, "their Benched Pokémon\nfall into Knock Out range", fc=SURFACE, ec=DMG)

arrow(70.4, 50.2, 74.1, 50.2, color=DMG)
arrow(86.5, 44.6, 86.5, 36.9, color=DMG)
arrow(74.1, 31.5, 70.4, 31.5, color=DMG)
arrow(57.7, 36.9, 57.7, 44.6, color=OURS, ls=(0, (3, 2)))
ax.text(58.8, 40.7, "next turn", fontsize=8, color=MUTED, ha="left")

ax.text(98.5, 24.0, "Freezing Shroud hits our own board too.\n"
                  "Adrena-Brain is how it gets exported.",
        fontsize=8.2, color=INK2, va="top", ha="right", linespacing=1.5)

# prize plan strip
box(46, 6.5, 52, 10.5, "", fc="#f5f4f0", ec="#e6e5e0", lw=1)
ax.text(48.5, 14.6, "THE PRIZE PLAN", fontsize=8.6, color=INK2, fontweight="bold")
ax.text(48.5, 12.4, "Three Knock Outs take all six Prize cards. 320 HP means the format\n"
                    "needs two turns to remove our attacker, while 180 + 30 + 10 + 30\n"
                    "is enough arithmetic that theirs often falls a turn early.",
        fontsize=8.4, color=INK, va="top", linespacing=1.55)

fig.suptitle("Marnie's Grimmsnarl ex — one Ability pays the Energy, two do the arithmetic",
             x=0.008, y=0.972, ha="left", fontsize=13, color=INK, fontweight="bold")
fig.subplots_adjust(left=0.012, right=0.988, top=0.90, bottom=0.02)
out = __file__.replace(".py", ".png")
fig.savefig(out, facecolor=SURFACE)
print("wrote", out)
