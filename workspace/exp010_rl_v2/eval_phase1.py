"""Evaluate the Phase-1 BC net (greedy, no search) vs the pool + Crustle control."""
from __future__ import annotations
import json, os, sys, time
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
for p in ["../exp001_harness", "../exp002_baselines", "../exp004_mcts", "../exp006_bc", "../exp007_anti_crustle"]:
    ap = os.path.abspath(os.path.join(HERE, p))
    if ap not in sys.path:
        sys.path.insert(0, ap)
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import train_mcts as T  # noqa
from train_bc import enumerate_actions  # noqa
import baselines as B  # noqa
import anti_crustle as AC  # noqa

DECK = AC.LUCARIO_DECK


def make_bc_agent(deck, model):
    def agent(obs_dict):
        try:
            obs = T.to_observation_class(obs_dict)
            if obs.select is None:
                return list(deck)
            actions = enumerate_actions(obs.select)
            if len(actions) == 1:
                return actions[0]
            _, policy = T.eval_nn(T.get_encoder_input(obs, deck),
                                  T.get_decoder_input(obs, actions), model)
            best = max(range(len(actions)), key=lambda i: policy[i])
            sel = actions[best]
            s = obs.select
            if all(0 <= i < len(s.option) for i in sel) and len(set(sel)) == len(sel) \
                    and s.minCount <= len(sel) <= s.maxCount:
                return sel
        except Exception:
            pass
        try:
            s = T.to_observation_class(obs_dict).select
            return list(range(min(max(1, s.minCount), len(s.option))))
        except Exception:
            return [0]
    return agent


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "results", "bc_v003_multi.pth")
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = T.MyModel(128, 2, 256, 1, 1).to(device)
    model.load_state_dict(torch.load(path, map_location=device)); model.eval()
    print(f"loaded {os.path.basename(path)}; n={n}/opp")
    opps = {"crustle": AC.make_crustle_agent, "lucario_v2": lambda: B.make_policy_agent("lucario_v2"),
            "dragapult": lambda: B.make_policy_agent("dragapult"),
            "random": lambda: B.make_random_agent_with_deck(DECK, seed=0)}
    res, wrs = {}, []
    with torch.inference_mode():
        for name, mk in opps.items():
            t0 = time.perf_counter()
            st = run_gauntlet(make_bc_agent(DECK, model), mk(), n_games=n, swap_sides=True)
            dt = time.perf_counter() - t0
            res[name] = {"winrate": round(st.winrate0, 3), "rec": f"{st.wins0}-{st.wins1}",
                         "err": st.errors0, "spg": round(dt/n, 2)}
            if name != "random":
                wrs.append(st.winrate0)
            print(f"vs {name:11s} winrate={st.winrate0:.3f} ({st.wins0}-{st.wins1}) err={st.errors0} {dt/n:.2f}s/g")
    print(f"\navg vs rule-based = {sum(wrs)/len(wrs):.3f}  (v003 ref: crustle~0.55, pool圧勝)")
    json.dump({"model": os.path.basename(path), "n": n, "results": res}, open(os.path.join(HERE, "results", "eval_phase1.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
