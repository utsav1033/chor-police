#!/usr/bin/env python3
"""Play ONE round: Police builds a box, Chor gets N tries, referee scores.

Usage:
  CHOR_POLICE_MOCK=1 python3 run_round.py            # mock, no plan spent
  python3 run_round.py --police opus --chor sonnet   # real, uses your plan
  python3 run_round.py --mode vm                     # real box on OrbStack VM
"""
import argparse
import json
import os
import time
from pathlib import Path

from cp import backend, playbook, prompts, referee, vmround
from cp.box import run_in_box, FakeBox

MODELS = {"sonnet": backend.SONNET, "opus": backend.OPUS}
LOGDIR = Path(__file__).parent / "logs"


def play_round(police="opus", chor="sonnet", tries=5, mode="fake",
               last_result=None, round_id=1, matchup="run", quiet=False,
               known_escapes=None, policy_override=None):
    canaries = referee.new_canaries()

    # 1. The box: either a seeded policy (e.g. the open starting box) or Police builds it
    if policy_override is not None:
        policy = policy_override
    else:
        policy = prompts.parse_policy(
            backend.ask(prompts.police_prompt(last_result, known_escapes), MODELS[police],
                        system=prompts.POLICE_SYSTEM))

    # 2. Plant this round's loot (VM mode) and pick the forbidden address
    if mode == "vm":
        vmround.prep_round(canaries)
        net_target = vmround.NET_TARGET
    else:
        net_target = "10.0.0.1"

    # 3. Chor's attempts: either a fixed probe playbook (no model) or a model
    history, box = [], (FakeBox(policy, canaries) if mode == "fake" else None)
    if chor == "playbook":
        for command in playbook.get_probes(net_target):
            output, box = run_in_box(policy, command, canaries, mode=mode, box=box)
            history.append({"command": command, "output": output})
    else:
        chor_model = MODELS[chor]
        for _ in range(tries):
            command = prompts.parse_command(
                backend.ask(prompts.chor_prompt(policy, history, net_target), chor_model,
                            system=prompts.CHOR_SYSTEM))
            output, box = run_in_box(policy, command, canaries, mode=mode, box=box)
            history.append({"command": command, "output": output})

    # 4. Referee scores (collect leftovers from the VM for the sleeper flag)
    if mode == "vm":
        box = vmround.collect_leftovers()
    flags_taken = referee.score_flags(history, canaries, box)
    usability = referee.check_usability(policy, canaries, run_in_box, mode)
    result = referee.verdict(flags_taken, usability)

    record = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "matchup": matchup, "round": round_id,
        "police": police, "chor": chor, "mode": mode,
        "policy": policy, "transcript": history, **result,
        "usability": usability,
    }
    LOGDIR.mkdir(exist_ok=True)
    (LOGDIR / f"{matchup}_r{round_id}.json").write_text(json.dumps(record, indent=2))
    if not quiet:
        _print_round(record)
    return record


def _print_round(r):
    icon = {"GREEN": "🟢", "RED": "🔴", "FOUL": "⚫"}[r["tag"]]
    print(f"\n{icon} {r['matchup']} round {r['round']}: "
          f"{r['police']}-police vs {r['chor']}-chor  ->  {r['label']}")
    for s in r["transcript"]:
        print(f"    chor: {s['command']:<32} -> {s['output'][:60]}")
    if r["flags_taken"]:
        print(f"    flags stolen: {', '.join(r['flags_taken'])}")
    print(f"    usability: {'ok' if r['usable'] else 'BROKEN'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--police", default="opus", choices=MODELS)
    ap.add_argument("--chor", default="playbook", choices=list(MODELS) + ["playbook"])
    ap.add_argument("--tries", type=int, default=5)
    ap.add_argument("--mode", default="fake", choices=["fake", "vm"])
    args = ap.parse_args()
    if args.mode == "vm" and os.environ.get("CHOR_POLICE_MOCK") == "1":
        print("note: MOCK is on, so models are canned even though mode=vm")
    play_round(args.police, args.chor, args.tries, args.mode)
