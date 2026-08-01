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
import math
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


def is_value_only(path):
    """"seat*" files: decisions made by a seat piloting some OTHER archetype.

    build_multi.py only ever recorded seats playing OUR archetype, so the net has
    never seen a position from an Alakazam/Crustle/Lucario player's own point of
    view. MCTS asks it for exactly that at every opponent node -- roughly half the
    tree, in the ~54% of ladder games that are not the mirror -- and the value head
    is what the search consumes (zeroing it drops self-play strength to 0.308).

    Their MOVES are not a target: we pilot Grimmsnarl, and imitating an Alakazam
    player's choices would blur the policy head with decisions we will never face.
    Their OUTCOMES are, so these files train the value head only."""
    return os.path.basename(path).startswith("seat")


def file_weights(path):
    """(policy weight, value weight) for every record in this file."""
    if is_policy_only(path):
        return 1.0, 0.0
    if is_value_only(path):
        return 0.0, 1.0
    return 1.0, 1.0


def iter_chunks(files, limit_chunks=None):
    n = 0
    for path in files:
        wid = int(re.search(r"_w(\d+)\.pkl$", path).group(1))
        pw, vw = file_weights(path)
        fid = os.path.basename(path)   # game ids restart per file, so (wid, gid)
                                       # alone is not unique once several corpora
                                       # are mixed; callers key per-game state on
                                       # fid. The val split keeps using wid so an
                                       # existing corpus splits exactly as before.
        with open(path, "rb") as f:
            while True:
                try:
                    chunk = pickle.load(f)
                except (EOFError, pickle.UnpicklingError):
                    break  # EOF, or a chunk a datagen worker is mid-writing
                yield wid, fid, chunk, pw, vw
                n += 1
                if limit_chunks and n >= limit_chunks:
                    return


def make_batch(recs, device, opp_drop=0.0, vw_list=None, pw_list=None):
    """Tensors in exactly train_mcts.train()'s format (64-candidate padding).
    opp_drop = probability of removing the opp_deck oracle word per record.
    vw_list / pw_list = per-record value- / policy-loss weight (None -> all 1.0)."""
    bs = len(recs)
    ie, idd = tm.LearnInput(), tm.LearnInput()
    mask, le, ld = [], [], []
    vw = list(vw_list) if vw_list is not None else [1.0] * bs
    pw = list(pw_list) if pw_list is not None else [1.0] * bs
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
        # exp083e: a 13th element carries a SOFT search policy (per-candidate
        # advantage from MCTS, already in [-1,1]) instead of the one-hot BC
        # label. Search is a measurably stronger policy than the net that guides
        # it (0.825 vs raw argmax, z=+5.81), so where we have it, it is the
        # better target. Records without it keep the old +-1 behaviour.
        if len(r) > 12 and r[12] is not None:
            pol = list(r[12])[:r[NC]]
            pol += [BC_NEG] * (r[NC] - len(pol))
        else:
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
            t(ld, torch.float32).view(bs, -1), t(vw, torch.float32).view(bs, -1),
            t(pw, torch.float32).view(bs, -1))


def train_epoch(model, optimizer, files, device, batch_size, limit_chunks, opp_drop=0.0,
                sched=None, clip=0.0, teacher=None, distill=0.0,
                policy_loss="huber", margin=0.5, ce_scale=8.0, smoothing=0.1):
    """sched, if given, is stepped PER BATCH (warmup needs step granularity, not
    epoch granularity -- exp083: the official post-norm arch trains badly at 2+
    layers without a warmup ramp).

    teacher/distill (exp083b): blend the hard BC label with the TEACHER's own
    outputs, target = (1-distill)*hard + distill*teacher. The heads are tanh +
    Huber regression (not softmax), so the teacher's output vector IS the soft
    target -- no temperature needed. Rationale: sc083_d128ctl showed that at this
    capacity, more training raises label top-1 (0.6238 -> 0.6577) without raising
    strength (0.525 vs the old net), while the big teacher DID get stronger
    (0.665, z=+4.67). Hard labels only say which candidate was picked; the
    teacher also says how good every OTHER candidate is, which is the part a
    capacity-limited student may actually be able to use."""
    loss_fn_enc = torch.nn.HuberLoss(reduction="none", delta=0.2)
    loss_fn_dec = torch.nn.HuberLoss(reduction="none", delta=0.1)
    # exp083b policy-loss forms. The default ("huber") regresses EVERY candidate
    # to +-1 independently, i.e. it asserts "the observed move is right and all
    # ~5 alternatives are wrong" -- but the player only ever gets to pick from
    # the cards they happened to draw, so several alternatives may be equally
    # fine and the label is one noisy sample, not ground truth.
    #   margin: only penalises candidates the model ranks ABOVE the observed
    #           move. Anything already ranked below contributes zero loss, so
    #           "we cannot judge these" is expressed as no supervision at all.
    #           This is the masked-loss idea in a form that still has contrast.
    #   ce:     softmax cross-entropy (+ label smoothing). Contrast comes from
    #           normalisation, so alternatives are only pushed down RELATIVE to
    #           the chosen one, never to an absolute -1.
    # Pure masking (drop the negatives entirely) is degenerate: with nothing
    # pushing anything down, all-+1 is optimal and argmax becomes arbitrary.
    model.train()
    total, n_batches = 0.0, 0
    carry = []  # (record, policy_weight, value_weight) triples
    shuffled = list(files)
    random.shuffle(shuffled)
    for wid, _fid, chunk, fpw, fvw in iter_chunks(shuffled, limit_chunks):
        recs = [(r, fpw, fvw) for r in chunk if not is_val(wid, r[GID])]
        random.shuffle(recs)
        carry.extend(recs)
        while len(carry) >= batch_size:
            batch, carry = carry[:batch_size], carry[batch_size:]
            (iei, iev, ieo, idi, idv, ido, mt, lte, ltd, vw, pw) = make_batch(
                [r for r, _, _ in batch], device, opp_drop,
                vw_list=[v for _, _, v in batch], pw_list=[p for _, p, _ in batch])
            ch = ltd.argmax(dim=1)  # from the HARD label (+1 > 0 pad > -1)
            td = None
            if teacher is not None and distill > 0.0:
                with torch.no_grad():
                    te, td = teacher(iei, iev, ieo, idi, idv, ido)
                # Same inputs (incl. the same opp_drop draw), so the teacher sees
                # exactly what the student sees. Padded slots are masked by mt.
                lte = (1.0 - distill) * lte + distill * te
                if policy_loss == "huber":
                    ltd = (1.0 - distill) * ltd + distill * td
            optimizer.zero_grad()
            oe, od = model(iei, iev, ieo, idi, idv, ido)
            # Normalising the policy term by pw.sum() rather than len(batch) keeps
            # value-only records from silently shrinking the policy gradient. With
            # no seat* files pw is all ones and this is the old expression exactly.
            pwn = max(float(pw.sum()), 1.0)
            if policy_loss == "huber":
                dec_loss = (loss_fn_dec(od, ltd) * mt * pw).sum() / pwn
            else:
                if policy_loss == "margin":
                    s_ch = od.gather(1, ch.view(-1, 1))
                    viol = torch.relu(margin - (s_ch - od)) * mt
                    viol = viol.scatter(1, ch.view(-1, 1), 0.0)
                    dec_loss = (viol * pw).sum() / pwn
                else:  # ce -- tanh outputs are bounded, so scale them into a
                       # usable logit range before softmax.
                    logits = (od * ce_scale).masked_fill(mt == 0, -1e9)
                    logp = torch.log_softmax(logits, dim=1)
                    nval = mt.sum(1, keepdim=True).clamp(min=1.0)
                    tgt = mt * (smoothing / nval)
                    tgt = tgt.scatter_add(1, ch.view(-1, 1),
                                          torch.full_like(ch, 1.0 - smoothing,
                                                          dtype=tgt.dtype).view(-1, 1))
                    dec_loss = -((tgt * logp).sum(1, keepdim=True) * pw).sum() / pwn
                if td is not None:
                    # keep the distillation signal as its own regression term
                    dec_loss = ((1.0 - distill) * dec_loss
                                + distill * (loss_fn_dec(od, td) * mt * pw).sum() / pwn)
            loss = ((loss_fn_enc(oe, lte) * vw).sum() / max(float(vw.sum()), 1.0)
                    + dec_loss)
            loss.backward()
            if clip:
                torch.nn.utils.clip_grad_norm_(model.parameters(), clip)
            optimizer.step()
            if sched is not None:
                sched.step()
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
    for wid, fid, chunk, fpw, _fvw in iter_chunks(files, limit_chunks):
        for r in chunk:
            if is_val(wid, r[GID]):
                key = (fid, r[GID])
                game_maxturn[key] = max(game_maxturn.get(key, 0), r[TURN])
                val.append((fid, r, fpw))
        if len(val) >= max_val:
            break  # chunk boundary only, so no game's maxturn is cut mid-way
    acc = Counter(); acc_n = Counter()
    auc_data = defaultdict(list)  # phase bucket -> (score, label)
    for i in range(0, len(val), batch_size):
        part = val[i:i + batch_size]
        recs = [r for _, r, _ in part]
        (iei, iev, ieo, idi, idv, ido, mt, lte, ltd, _vw, _pw) = make_batch(recs, device, opp_drop)
        oe, od = model(iei, iev, ieo, idi, idv, ido)
        od = od.masked_fill(mt == 0, -1e9)
        pred = od.argmax(dim=1).tolist()
        vals = oe.view(-1).tolist()
        for (fid, r, fpw), p, v in zip(part, pred, vals):
            mx = max(game_maxturn[(fid, r[GID])], 1)
            bucket = min(int(4 * r[TURN] / mx), 3)
            label = 1 if r[OUT] > 0 else 0
            auc_data[bucket].append((v, label))
            # seat* records exist to train the value head; their moves are another
            # archetype's and are not what the policy head is asked to reproduce,
            # so they are scored separately (own = our pilot, other = their seats).
            auc_data[("other" if fpw == 0.0 else "own", bucket)].append((v, label))
            if fpw == 0.0:
                continue
            hit = int(p == r[CH])
            acc["all"] += hit; acc_n["all"] += 1
            acc[r[MU]] += hit; acc_n[r[MU]] += 1
            if r[NC] > 1:
                acc["multi"] += hit; acc_n["multi"] += 1
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
    phases = [b for b in auc_data if isinstance(b, int)]
    out = {"n_val": len(val),
           "acc": {k: round(acc[k] / acc_n[k], 4) for k in acc_n},
           "auc_by_phase": {f"q{b+1}": (round(a, 4) if (a := auc(auc_data[b])) is not None else None)
                            for b in sorted(phases)}}
    seats = sorted({s for s in auc_data if isinstance(s, tuple)})
    if any(s[0] == "other" for s in seats):
        out["auc_by_seat"] = {
            f"{s}_q{b+1}": (round(a, 4) if (a := auc(auc_data[(s, b)])) is not None else None)
            for s, b in seats}
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
    # exp083: the arch used to be hardwired to heads=2, 1 encoder + 1 decoder layer,
    # d_ff=2*d_model. Those knobs are what "scale the policy network" needs.
    ap.add_argument("--heads", type=int, default=2)
    ap.add_argument("--enc-layers", type=int, default=1)
    ap.add_argument("--dec-layers", type=int, default=1)
    ap.add_argument("--d-ff", type=int, default=0, help="0 = 2*d_model (the old default)")
    ap.add_argument("--cosine", action="store_true",
                    help="cosine-decay the LR over --epochs (for long runs)")
    ap.add_argument("--warmup-steps", type=int, default=0,
                    help="linear LR warmup over N optimizer steps; required for the "
                         "post-norm arch at >1 layer (exp083)")
    ap.add_argument("--clip", type=float, default=0.0,
                    help="clip_grad_norm_ threshold (0=off); stabilises the deeper configs")
    ap.add_argument("--steps-per-epoch", type=int, default=8044,
                    help="only used to size the warmup+cosine schedule (10-day corpus @bs128)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--resume", default="", help="path to model .pth to continue from")
    ap.add_argument("--opp-drop", type=float, default=0.0,
                    help="train-time dropout prob of the opp_deck oracle word (word 22)")
    ap.add_argument("--teacher", default="",
                    help="distillation: teacher .pth (arch read from its sibling arch.json)")
    ap.add_argument("--policy-loss", default="huber", choices=("huber", "margin", "ce"),
                    help="policy-head loss form (see train_epoch)")
    ap.add_argument("--margin", type=float, default=0.5, help="margin loss: required gap")
    ap.add_argument("--ce-scale", type=float, default=8.0, help="ce loss: tanh->logit scale")
    ap.add_argument("--smoothing", type=float, default=0.1, help="ce loss: label smoothing")
    ap.add_argument("--distill", type=float, default=0.0,
                    help="blend weight on the teacher's outputs (0=pure hard labels, 1=pure teacher)")
    args = ap.parse_args()
    d_ff = args.d_ff or args.d_model * 2

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    files = sorted(p for pat in args.glob.split(",")
                   for p in glob.glob(os.path.join(HERE, pat)))
    assert files, f"no data files match {args.glob}"
    n_pol_only = sum(1 for p in files if is_policy_only(p))
    if n_pol_only:
        print(f"{n_pol_only}/{len(files)} files are policy-only (DAgger; value loss zeroed)")
    n_val_only = sum(1 for p in files if is_value_only(p))
    if n_val_only:
        print(f"{n_val_only}/{len(files)} files are value-only (other archetypes' "
              f"seats; policy loss zeroed)")
    out_dir = os.path.join(HERE, "results", args.tag)
    os.makedirs(out_dir, exist_ok=True)
    lim = args.limit_chunks or None

    model = tm.MyModel(args.d_model, args.heads, d_ff,
                       args.enc_layers, args.dec_layers).to(device)
    if args.resume:
        model.load_state_dict(torch.load(args.resume, map_location=device))
        print(f"resumed from {args.resume}")
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    sched = None
    if args.warmup_steps or args.cosine:
        total = max(1, args.epochs * args.steps_per_epoch)
        wu = args.warmup_steps

        def lr_at(step):  # multiplier on args.lr, stepped per batch
            if wu and step < wu:
                return (step + 1) / wu
            if not args.cosine:
                return 1.0
            prog = min(1.0, max(0.0, (step - wu) / max(1, total - wu)))
            return 0.5 * (1.0 + math.cos(math.pi * prog))

        sched = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_at)
    # The arch is no longer implied by d_model alone -- record it so npnet/export and
    # any later reload can rebuild the exact model without guessing.
    arch = {"d_model": args.d_model, "heads": args.heads, "d_ff": d_ff,
            "enc_layers": args.enc_layers, "dec_layers": args.dec_layers,
            # ship side selects the feature encoder from this -- a v3-trained net
            # fed v1 features is a silently different function, never a crash
            "enc_version": (4 if getattr(tm, "ENC_V4", 0) else (3 if tm.ENC_V3 else 1))}
    if args.policy_loss != "huber":
        arch["policy_loss"] = args.policy_loss
    json.dump(arch, open(os.path.join(out_dir, "arch.json"), "w"), indent=1)
    n_par = sum(p.numel() for p in model.parameters())
    print(f"device={device} files={len(files)} tag={args.tag} arch={arch} params={n_par/1e6:.1f}M")

    teacher = None
    if args.teacher:
        tcfg = {"d_model": 128, "heads": 2, "d_ff": 256, "enc_layers": 1, "dec_layers": 1}
        tarch = os.path.join(os.path.dirname(os.path.abspath(args.teacher)), "arch.json")
        if os.path.exists(tarch):
            tcfg.update(json.load(open(tarch)))
        tcfg.setdefault("d_ff", tcfg["d_model"] * 2)
        teacher = tm.MyModel(tcfg["d_model"], tcfg["heads"], tcfg["d_ff"],
                             tcfg["enc_layers"], tcfg["dec_layers"]).to(device)
        teacher.load_state_dict(torch.load(args.teacher, map_location=device))
        teacher.eval()
        for p in teacher.parameters():
            p.requires_grad_(False)
        arch["distill"] = {"teacher": args.teacher, "teacher_arch": tcfg, "weight": args.distill}
        json.dump(arch, open(os.path.join(out_dir, "arch.json"), "w"), indent=1)
        print(f"distill: teacher={args.teacher} arch={tcfg} weight={args.distill}")

    history = []
    for ep in range(args.epochs):
        t0 = time.time()
        loss, nb = train_epoch(model, optimizer, files, device, args.batch_size, lim,
                               opp_drop=args.opp_drop, sched=sched, clip=args.clip,
                               teacher=teacher, distill=args.distill,
                               policy_loss=args.policy_loss, margin=args.margin,
                               ce_scale=args.ce_scale, smoothing=args.smoothing)
        metrics = evaluate(model, files, device, args.batch_size, lim)
        row = {"epoch": ep, "loss": round(loss, 4), "batches": nb,
               "lr": round(optimizer.param_groups[0]["lr"], 7),
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
