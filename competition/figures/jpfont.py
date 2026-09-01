"""Register a Japanese-capable font so card names render in both languages.

matplotlib's bundled DejaVu Sans has no CJK glyphs, so Japanese card names come out
as empty boxes with a UserWarning. This looks for a font on the machine rather than
committing a 10 MB binary to the repo; if none is found the figures still build, in
English only, and say so.
"""
import os
from matplotlib import font_manager, rcParams

# Regular first, then any matching bold face -- a single variable font (Noto's VF)
# renders Japanese but loses every fontweight="bold" in the figures, so prefer
# families that ship a real bold.
CANDIDATES = [
    ("/mnt/c/Windows/Fonts/meiryo.ttc", "/mnt/c/Windows/Fonts/meiryob.ttc"),
    ("/mnt/c/Windows/Fonts/YuGothR.ttc", "/mnt/c/Windows/Fonts/YuGothB.ttc"),
    ("/mnt/c/Windows/Fonts/NotoSansJP-VF.ttf", None),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
     "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    ("/usr/share/fonts/truetype/fonts-japanese-gothic.ttf", None),
    ("/System/Library/Fonts/ttf/HiraginoSans-W3.ttc", None),
]


def use_jp() -> bool:
    """Put a CJK font at the front of the sans-serif stack. True if one was found."""
    for path, bold in CANDIDATES:
        if not os.path.exists(path):
            continue
        try:
            font_manager.fontManager.addfont(path)
            name = font_manager.FontProperties(fname=path).get_name()
            if bold and os.path.exists(bold):
                font_manager.fontManager.addfont(bold)
        except Exception:
            continue
        rcParams["font.family"] = "sans-serif"
        rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
        rcParams["axes.unicode_minus"] = False
        return True
    print("  ! no CJK font found; Japanese names will not render")
    return False
