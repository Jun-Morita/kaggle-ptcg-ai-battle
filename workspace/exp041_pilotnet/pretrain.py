"""exp041 Phase 2 -- supervised pretraining of the official transformer on
competent-pilot games (datagen_bc.py output): policy head <- BC on the pilot's
chosen candidate, value head <- final game outcome.

Design notes (SESSION_NOTES Phase 2):
- GAME-level train/val split via hash of (worker, game_idx) -- exp014 lesson:
  sample-level splits leak ~70 same-game samples across the boundary and
  inflate val metrics into meaninglessness.
- Streaming: chunks are read from disk every epoch (a full load would be
  10GB+ of python objects in RAM). Shuffling = file order + within-chunk;
  approximate but sufficient at this scale.
- Loss = the same Huber losses/format as exp040 train_mcts.train(), with
  NEUTRAL matchup weights (the data already contains winning crustle
  trajectories -- the exp040 Stage4 reweighting lesson is that weights can't
  fix missing positives, and now they aren't missing).
- BC policy targets: chosen candidate +1.0, others -1.0 (tanh head; the MCTS
  prior downstream is prob ~ exp(10*p), so a trained gap of ~1 gives a sharp
  but not literally one-hot prior).

Usage:
  uv run python pretrain.py --epochs 3 --tag pre1
  uv run python pretrain.py --limit-chunks 5 --epochs 1 --tag smoke   # smoke
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import pickle
import random
import re
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402  (native engine loads; unused here but keeps one code path)

BC_POS, BC_NEG = 1.0, -1.0
VAL_MOD = 20  # 1/20 of games -> val

# record layout from datagen_bc.py
EI, EV, EO, DI, DV, DO, NC, CH, TURN, OUT, MU, GID = range(12)

# Encoder word 22 = the opp_deck oracle bag (verified against data 2026-07-09:
# word21 = your_deck, 60 entries, IDENTICAL across matchups; word22 = 60 entries,
# VARIES by matchup). In a real ladder game the opponent decklist is unknown, so
# a net that depends on this oracle can't ship as-is -- training with stochastic
# dropout of this word teaches the net to also work oracle-free (feed an empty
# word at inference), closing the ship-blocker without an archetype detector.
OPPDECK_WORD = 22


def drop_oppdeck(r):
    """Return (ei, ev, eo) with the opp_deck word's entries removed."""
    eo = r[EO]
    s, e = eo[OPPDECK_WORD], eo[OPPDECK_WORD + 1]
    if s == e:
        return r[EI], r[EV], eo
    ei = r[EI][:s] + r[EI][e:]
    ev = r[EV][:s] + r[EV][e:]
    cut = e - s
    eo2 = [o if k <= OPPDECK_WORD else o - cut for k, o in enumerate(eo)]
    return ei, ev, eo2


def is_val(wid, gid):
    return (wid * 100003 + gid) % VAL_MOD == 0


def is_policy_only(path):
    """DAgger files: the policy label is the TEACHER's move, but the value label
    is the outcome of the NET's own (weaker) continuation -- training the value
    head on it teaches an inconsistent objective (dagger1's suspected failure
    cause (a)). Mark them so train_epoch zeroes their value loss."""
    return os.path.basename(path).startswith("dagger")


def iter_chunks(files, limit_chunks=None):
    n = 0
    for path in files:
        wid = int(re.search(r"_w(\d+)\.pkl$", path).group(1))
        pol_only = is_policy_only(path)
        with open(path, "rb") as f:
            while True:
                try:
                    chunk = pickle.load(f)
                except (EOFError, pickle.UnpicklingError):
                    break  # EOF, or a chunk a datagen worker is mid-writing
                yield wid, chunk, pol_only
                n += 1
                if limit_chunks and n >= limit_chunks:
                    return


def make_batch(recs, device, opp_drop=0.0, vw_list=None):
    """Tensors in exactly train_mcts.train()'s format (64-candidate padding).
    opp_drop = probability of removing the opp_deck oracle word per record.
    vw_list = per-record value-loss weight (None -> all 1.0)."""
    bs = len(recs)
    ie, idd = tm.LearnInput(), tm.LearnInput()
    mask, le, ld = [], [], []
    vw = list(vw_list) if vw_list is not None else [1.0] * bs
    for r in recs:
        if opp_drop > 0.0 and random.random() < opp_drop:
            rei, rev, reo = drop_oppdeck(r)
        else:
            rei, rev, reo = r[EI], r[EV], r[EO]
        c = len(ie.index)
        ie.index.extend(rei); ie.value.extend(rev)
        for o in reo:
            ie.offset.append(o + c)
        c = len(idd.index)
        idd.index.extend(r[DI]); idd.value.extend(r[DV])
        for o in r[DO]:
            idd.offset.append(o + c)
        le.append(r[OUT])
        pol = [BC_NEG] * r[NC]
        pol[r[CH]] = BC_POS
        ld.extend(pol)
        mask.extend([1.0] * r[NC])
        for _ in range(64 - r[NC]):
            mask.append(0.0); ld.append(0.0)
            idd.offset.append(len(idd.index))
    t = lambda x, dt: torch.tensor(x, dtype=dt, device=device)
    return (t(ie.index, torch.int32), t(ie.value, torch.float32), t(ie.offset, torch.int32),
            t(idd.index, torch.int32), t(idd.value, torch.float32), t(idd.offset, torch.int32),
            t(mask, torch.float32).view(bs, -1), t(le, torch.float32).view(bs, -1),
            t(ld, torch.float32).view(bs, -1), t(vw, torch.float32).view(bs, -1))


def train_epoch(model, optimizer, files, device, batch_size, limit_chunks, opp_drop=0.0):
    loss_fn_enc = torch.nn.HuberLoss(reduction="none", delta=0.2)
    loss_fn_dec = torch.nn.HuberLoss(reduction="none", delta=0.1)
    model.train()
    total, n_batches = 0.0, 0
    carry = []  # (record, value_weight) pairs
    shuffled = list(files)
    random.shuffle(shuffled)
    for wid, chunk, pol_only in iter_chunks(shuffled, limit_chunks):
        w = 0.0 if pol_only else 1.0
        recs = [(r, w) for r in chunk if not is_val(wid, r[GID])]
        random.shuffle(recs)
        carry.extend(recs)
        while len(carry) >= batch_size:
            batch, carry = carry[:batch_size], carry[batch_size:]
            (iei, iev, ieo, idi, idv, ido, mt, lte, ltd, vw) = make_batch(
                [r for r, _ in batch], device, opp_drop, vw_list=[w for _, w in batch])
            optimizer.zero_grad()
            oe, od = model(iei, iev, ieo, idi, idv, ido)
            loss = ((loss_fn_enc(oe, lte) * vw).sum() / max(float(vw.sum()), 1.0)
                    + (loss_fn_dec(od, ltd) * mt).sum() / len(batch))
            loss.backward()
            optimizer.step()
            total += loss.item()
            n_batches += 1
    return total / max(n_batches, 1), n_batches


@torch.no_grad()
def evaluate(model, files, device, batch_size, limit_chunks, max_val=200000, opp_drop=0.0):
    """Val metrics: policy top-1 accuracy (overall/per-matchup/multi-candidate-
    only) + value AUC by game-phase quartile (phase = turn / game max turn).
    opp_drop=1.0 evaluates the ORACLE-FREE condition (opp_deck word removed)."""
    model.eval()
    # eval on the ORIGINAL pilot data only: DAgger files' value labels are
    # net-continuation outcomes (not comparable), and their (wid, gid) keys
    # collide with the samples_ files' game numbering.
    files = [p for p in files if not is_policy_only(p)]
    val = []
    game_maxturn = {}
    for wid, chunk, _pol in iter_chunks(files, limit_chunks):
        for r in chunk:
            if is_val(wid, r[GID]):
                key = (wid, r[GID])
                game_maxturn[key] = max(game_maxturn.get(key, 0), r[TURN])
                val.append((wid, r))
        if len(val) >= max_val:
            break  # chunk boundary only, so no game's maxturn is cut mid-way
    acc = Counter(); acc_n = Counter()
    auc_data = defaultdict(list)  # phase bucket -> (score, label)
    for i in range(0, len(val), batch_size):
        part = val[i:i + batch_size]
        recs = [r for _, r in part]
        (iei, iev, ieo, idi, idv, ido, mt, lte, ltd, _vw) = make_batch(recs, device, opp_drop)
        oe, od = model(iei, iev, ieo, idi, idv, ido)
        od = od.masked_fill(mt == 0, -1e9)
        pred = od.argmax(dim=1).tolist()
        vals = oe.view(-1).tolist()
        for (wid, r), p, v in zip(part, pred, vals):
            hit = int(p == r[CH])
            acc["all"] += hit; acc_n["all"] += 1
            acc[r[MU]] += hit; acc_n[r[MU]] += 1
            if r[NC] > 1:
                acc["multi"] += hit; acc_n["multi"] += 1
            mx = max(game_maxturn[(wid, r[GID])], 1)
            bucket = min(int(4 * r[TURN] / mx), 3)
            auc_data[bucket].append((v, 1 if r[OUT] > 0 else 0))
    def auc(pairs):
        pairs = sorted(pairs)
        pos = sum(l for _, l in pairs)
        neg = len(pairs) - pos
        if not pos or not neg:
            return None
        rank_sum = 0.0
        for j, (_, l) in enumerate(pairs):
            if l:
                rank_sum += j + 1
        return (rank_sum - pos * (pos + 1) / 2) / (pos * neg)
    out = {"n_val": len(val),
           "acc": {k: round(acc[k] / acc_n[k], 4) for k in acc_n},
           "auc_by_phase": {f"q{b+1}": (round(a, 4) if (a := auc(auc_data[b])) is not None else None)
                            for b in sorted(auc_data)}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=3e-4)  # matches the official sample's AdamW(3e-4)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--glob", default="data/samples_turnbeam_w*.pkl")
    ap.add_argument("--limit-chunks", type=int, default=0, help="smoke: cap chunks/epoch")
    ap.add_argument("--tag", default="pre1")
    ap.add_argument("--d-model", type=int, default=128)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--resume", default="", help="path to model .pth to continue from")
    ap.add_argument("--opp-drop", type=float, default=0.0,
                    help="train-time dropout prob of the opp_deck oracle word (word 22)")
    args = ap.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    files = sorted(p for pat in args.glob.split(",")
                   for p in glob.glob(os.path.join(HERE, pat)))
    assert files, f"no data files match {args.glob}"
    n_pol_only = sum(1 for p in files if is_policy_only(p))
    if n_pol_only:
        print(f"{n_pol_only}/{len(files)} files are policy-only (DAgger; value loss zeroed)")
    out_dir = os.path.join(HERE, "results", args.tag)
    os.makedirs(out_dir, exist_ok=True)
    lim = args.limit_chunks or None

    model = tm.MyModel(args.d_model, 2, args.d_model * 2, 1, 1).to(device)
    if args.resume:
        model.load_state_dict(torch.load(args.resume, map_location=device))
        print(f"resumed from {args.resume}")
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    print(f"device={device} files={len(files)} tag={args.tag}")

    history = []
    for ep in range(args.epochs):
        t0 = time.time()
        loss, nb = train_epoch(model, optimizer, files, device, args.batch_size, lim,
                               opp_drop=args.opp_drop)
        metrics = evaluate(model, files, device, args.batch_size, lim)
        row = {"epoch": ep, "loss": round(loss, 4), "batches": nb,
               "sec": round(time.time() - t0), **metrics}
        if args.opp_drop > 0.0:
            nofree = evaluate(model, files, device, args.batch_size, lim, opp_drop=1.0)
            row["oracle_free"] = {"acc": nofree["acc"], "auc_by_phase": nofree["auc_by_phase"]}
        history.append(row)
        print(json.dumps(row), flush=True)
        torch.save(model.state_dict(), os.path.join(out_dir, f"model_ep{ep}.pth"))
        json.dump(history, open(os.path.join(out_dir, "history.json"), "w"), indent=1)
    print("done.")


if __name__ == "__main__":
    main()
