#!/usr/bin/env python3
"""The one-day program: two short runs that give the two outcomes worth showing.

  Run A  Hardening: one matchup, N rounds -> the chart (escapes drop to zero).
  Run B  Bracket:   4 matchups, 1 round each -> the table (who holds, who breaks).

Usage:
  CHOR_POLICE_MOCK=1 python3 tussle.py --quick     # smoke test, no plan spent
  python3 tussle.py                                # real, uses your plan (fake box)
  python3 tussle.py --mode vm                      # real box on OrbStack VM
"""
import argparse
import json
from pathlib import Path

from run_round import play_round
from cp.box import OPEN_POLICY

LOGDIR = Path(__file__).parent / "logs"
BRACKET = [("sonnet", "sonnet"), ("opus", "sonnet"), ("sonnet", "opus"), ("opus", "opus")]


def run_hardening(rounds, tries, mode, chor="sonnet"):
    print(f"\n==================  RUN A: HARDENING (opus-police vs {chor}-chor)  ==================")
    last, series, known = None, [], {}
    for i in range(1, rounds + 1):
        # round 1 is the deliberately-open starting box; Police hardens from round 2
        override = OPEN_POLICY if i == 1 else None
        r = play_round("opus", chor, tries, mode, last, i, "hardening",
                       known_escapes=dict(known), policy_override=override)
        known.update(r["flags_taken"])  # defenses must stick across rounds
        last = r
        series.append((i, len(r["flags_taken"]), r["usable"]))
    print("\n  chart  (round: flags stolen | usability)")
    for i, flags, usable in series:
        bar = ("█" * flags) if flags else "·"
        print(f"    r{i}: {flags} {bar:<5} | {'green' if usable else 'FOUL'}")
    return series


def run_bracket(tries, mode, chor="sonnet"):
    print("\n==================  RUN B: BRACKET (1 round each)  ==================")
    rows = []
    if chor == "playbook":
        # compare Police models holding the same fixed playbook
        for police in ["opus", "sonnet"]:
            r = play_round(police, "playbook", tries, mode, None, 1, f"bracket_{police}_police")
            rows.append((police, "playbook", r["tag"], len(r["flags_taken"])))
    else:
        for police, c in BRACKET:
            r = play_round(police, c, tries, mode, None, 1, f"bracket_{police}_v_{c}")
            rows.append((police, c, r["tag"], len(r["flags_taken"])))
    print("\n  police     chor       result   flags")
    print("  " + "-" * 40)
    for police, c, tag, n in rows:
        print(f"  {police:<10} {c:<10} {tag:<8} {n}")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=3, help="hardening rounds (Run A)")
    ap.add_argument("--tries", type=int, default=5, help="chor tries per round")
    ap.add_argument("--mode", default="fake", choices=["fake", "vm"])
    ap.add_argument("--quick", action="store_true", help="2 rounds, 4 tries (fast)")
    ap.add_argument("--only", choices=["a", "b"], help="run only one of the two")
    ap.add_argument("--playbook", action="store_true",
                    help="use the fixed probe playbook as Chor (no attacker model)")
    args = ap.parse_args()
    if args.quick:
        args.rounds, args.tries = 2, 4
    chor = "playbook" if args.playbook else "sonnet"

    summary = {}
    if args.only != "b":
        summary["hardening"] = run_hardening(args.rounds, args.tries, args.mode, chor)
    if args.only != "a":
        summary["bracket"] = run_bracket(args.tries, args.mode, chor)

    LOGDIR.mkdir(exist_ok=True)
    (LOGDIR / "tussle_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nlogs + summary written to {LOGDIR}/")
