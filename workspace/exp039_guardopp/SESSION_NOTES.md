# exp039 — v014 turn-beam base + archetype-matched opponent-reply doom-veto

## Hypothesis
v013's opponent-reply guard (exp029/guard_policy.py) already supports
GUARD_BASE=turnbeam (v014 as base), and this combo was measured at n=200 back
in exp029: total 2.61, below v014 alone (2.67). Per-matchup it hurt crustle/
dragapult/archaludon (opponent runs a DIFFERENT deck) while helping mirror_chq
(SAME deck) -- the fingerprint of a mismatched opponent-reply simulation:
guard_policy's `roll_opp` was plain revenge_policy (OUR OWN deck's policy)
pretending to be the opponent. exp038 built (and, after 11 bug fixes, still
didn't ship) an archetype-matched opponent model with exclusion-based hidden-
info sampling -- the ONE part of that experiment that worked reliably. This
experiment reuses v013's PROVEN categorical doom-veto criteria UNCHANGED
(never the continuous eval_fn+margin design that exp038 couldn't make work)
and only swaps the opponent-reply rollout policy for exp038's OpponentModel,
plus carries over the state-contamination protections (generic module
snapshot/restore, game-boundary reset) exp038 needed.

## Result (n=100/matchup, chunked, `run_guardopp.sh`)

| matchup | exp039 | v014 alone | old mismatched combo (exp029) |
|---|---:|---:|---:|
| ex_lucario | **0.83** | 0.77 | 0.775 |
| dragapult | 0.17 | 0.22 | 0.160 |
| archaludon | 0.10 | 0.195 | 0.185 |
| mirror_chq | 0.60 | 0.58 | 0.620 |
| crustle | **0.91** | 0.905 | 0.870 |
| **field total** | **2.61** | **2.67** | **2.61** |
| paired vs v012 | **0.57** | 0.53 | (n/a) |
| paired vs v014 | **0.49** | -- | -- |

Fire rate is low and controlled throughout (checked/fired ratios in the 1-15%
range depending on matchup, much closer to v013/v014's proven ~1-3% style than
exp038's 20-50%), confirming the categorical doom-veto criteria (not a
continuous eval comparison) is the right kind of qualification for this
design shape.

## Interpretation
- Real, clean gains on crustle (+0.005, effectively matching v014's already-
  strong number) and ex_lucario (+0.06) over v014 alone -- and a genuinely
  better ex_lucario/crustle than the OLD mismatched combo too, confirming the
  archetype-matched opponent model IS a real improvement over "guess with our
  own deck's policy" for those matchups.
- archaludon regressed notably (0.195 -> 0.10), even below the old mismatched
  combo's 0.185. Since archaludon is already one of our structurally weakest,
  most swingy matchups (exp025/026: HP300 + confirmed-KO 220dmg + non-ex
  bypass = genuinely hard for us regardless of piloting), this may not be
  about opponent-model accuracy at all -- it could be that in an
  already-losing race, MOST decision points look "doomed" in some sense,
  making the categorical veto fire on noise specific to that structural
  disadvantage rather than genuine tactical error.
- Net: field total (2.61) ties the OLD flawed combo and sits BELOW v014 alone
  (2.67). **Paired head-to-head vs v014 is 0.49 (n=100)** -- statistically
  indistinguishable from a coin flip (SE~0.05 at this n). This is NOT a clear
  win over v014.

## Ship decision: DO NOT SHIP as a v014 replacement. This is a fundamentally
different (much healthier) result than exp038's outright negative -- it's
roughly at PARITY with v014, with a genuinely different matchup profile
(stronger ex-heavy/wall coverage, weaker vs archaludon specifically). Worth
keeping as a documented, working alternative design (unlike exp038, this one
is crash-safe, low-fire-rate, and internally consistent) rather than a
negative result to shelve outright.

## Possible next step (not yet executed, optional)
If archaludon's regression is specifically an artifact of "doom-veto noise in
an already-losing structural matchup" rather than a real behavioral mistake,
gating the guard OFF specifically when the opponent is detected as Archaludon
(reusing the same archetype detection already used for opponent modeling)
might recover that matchup back to v014's level or better, potentially pushing
the field total above 2.67 for the first time. Not attempted this session.

## Follow-up: archaludon-detection gate (2026-07-05)

Implemented `if opp_model._archetype == "Archaludon ex": return base_sel`
(env `GO_GATE_ARCH`, default on) -- disable the guard entirely and defer to
v014 alone whenever the opponent is detected as Archaludon ex. A quick n=20
speed-check showed archaludon recovering from 0.10 to 0.20, so a full
n=100/matchup chunked re-verification (`run_guardopp.sh`, `chunks_go/`) was
run to confirm at scale.

### Result (n=100/matchup, with archaludon gate)

| matchup | exp039+gate | v014 alone | exp039 (no gate) |
|---|---:|---:|---:|
| archaludon | **0.19** | 0.195 | 0.10 |
| crustle | 0.90 | 0.905 | 0.91 |
| dragapult | 0.17 | 0.220 | 0.17 |
| ex_lucario | 0.78 | 0.770 | 0.83 |
| mirror_chq | 0.59 | 0.580 | 0.60 |
| **field total** | **2.63** | **2.67** | 2.61 |
| paired vs v012 | 0.49 | -- | 0.57 |
| paired vs v014 | 0.52 | -- | 0.49 |

The gate worked exactly as intended: archaludon recovered from 0.10 to 0.19,
back in line with v014's 0.195. But two things moved in the opposite
direction at this larger n:

- **ex_lucario's headline "+0.06" (0.83) did NOT reproduce**: at this second
  n=100 pass it's 0.78, essentially flat vs v014's 0.770 (+0.01). This is the
  SAME reproducibility trap already flagged in `ex_lucario.md` for v013's
  "0.86" claim -- a good single n=100 read on a categorical-veto design is not
  yet a confirmed effect; it needs a second independent measurement before
  being trusted. Duly noted there now too.
- crustle/mirror_chq stayed flat (within noise of their no-gate values).

Net: field total 2.63 vs v014's 2.67 -- a -0.04 gap, well within noise for
n=100/matchup (SE roughly 0.04-0.05 per matchup, larger when summed). Paired
head-to-head vs v014 is 0.52 (n=100) -- still a coin flip.

## Final ship decision: DO NOT SHIP as a v014 replacement.

Even with the archaludon gate fixing the one clear regression, the design is
at **genuine parity** with v014, not an improvement -- and the apparent
ex_lucario edge that motivated shipping consideration in the first place
evaporated on a second measurement. Combined with exp038's 11-bug-fix outright
negative, this closes out the "read the opponent's hand deeper via search"
research line for this session: the categorical doom-veto (v013's original
design) already captures what a shallow verified search *can* profitably
capture; going deeper (exp038) or making the opponent model more accurate
(exp039) does not add net value on top of it, at least not without a further,
currently unidentified idea. v014 remains the strongest verified pilot and
the correct thing to keep shipping.

Dragapult remains the one unambiguous, unaddressed regression under the guard
(0.17 vs v014's 0.220, in BOTH gated and ungated runs) -- a dragapult-specific
gate (same pattern as archaludon) was never tried this session and is the
most likely next lever if this line is revisited, but given the parity
verdict above, doing so is now de-prioritized versus other work.
