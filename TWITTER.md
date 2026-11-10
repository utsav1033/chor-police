# Twitter / X draft

Two thread angles + a one-liner. All claims are true to the runs (see
docs/FINDINGS.md). Pick one, tweak the voice to yours. Attach `docs/diagram.svg`
(export to PNG) to the first tweet.

---

## Angle A — "the build + 3 surprises" (recommended)

**1/**
I spent one evening building a game: one AI builds a Linux sandbox, another AI
tries to escape it, a script referees.

Three things genuinely surprised me about how agents work. 🧵

**2/**
Setup: the attacker model never gets a shell. It only *proposes* commands — a
referee script runs them inside a bubblewrap jail (in a throwaway VM) and feeds
back the output.

That's not a toy choice. It's literally how real AI agents touch anything.

**3/** Surprise #1: I tried to make Claude the *attacker*.

It refused. The safety classifier flags "generate sandbox-escape commands" as
cyber-misuse — even on a fake, disposable box.

The *defender* side never trips. Building a sandbox is fine; breaking one isn't.

**4/**
The tempting move is "use a weaker model that won't refuse." That's just
safeguard-evasion. So instead: the attacker is a fixed command playbook, or a
*local* open model (Qwen) you run yourself. Redesign > route around.

**5/** Surprise #2: prompting beat model size.

My first attacker ladder (Qwen 1.5B→7B) was flat and bad — nobody cracked the
hard box.

Adding a one-page "methodology" to the prompt took 3B and 7B from ~2/5 to 5/5.
Same models.

**6/** Surprise #3: a 7B built a genuinely *sound* sandbox.

Qwen-7B as the defender wrote a tight-but-usable policy (its own JSON). A
scaffolded 7B attacker then tried hard — cat, curl, probing hidden files — and
got zero.

You can't read a file that was never mounted.

**7/**
The through-line: the model was never the interesting part. The *system* was —
the isolation, the referee/gate, structured policies, an eval with a
counter-metric ("0 escapes AND still usable"), the scaffolding.

That's agent infrastructure.

**8/**
Everything's a small from-scratch repo: bubblewrap jail, policy→sandbox compiler,
canary scoring, a local-Qwen backend, a fault-deck benchmark.

Honest about limits (tiny N, noisy small models). Writeup + code 👇
https://github.com/utsav1033/chor-police

---

## Angle B — "the refusal hook" (punchier, riskier)

**1/**
I tried to get Claude to break out of a sandbox.

It said no.

So I accidentally learned how agent infrastructure actually works instead. 🧵

**2/**
The plan: one AI designs a Linux jail, another AI attacks it, a script keeps
score — all in a throwaway VM with fake secrets.

The catch: Claude's safety classifier refuses to *be* the attacker (cyber
category). The defender side is totally fine.

**3/**
Lesson 1: when a model refuses dual-use generation, that's a signal, not a bug to
route around. I did NOT model-shop for a weaker classifier. The attacker became a
local open model (Qwen) + a fixed playbook.

**4/**
Lesson 2: prompting > model size. A one-page methodology in the prompt took my
local attacker from 2/5 to 5/5 on a set of planted holes. Same weights.

**5/**
Lesson 3: a 7B designed a sandbox that a (scaffolded) 7B attacker couldn't crack —
correctly, because a sound jail has no command-level escape.

The leverage was never the model. It was the harness around it.
Code + writeup 👇 https://github.com/utsav1033/chor-police

---

## One-liner (standalone)

Spent an evening building an AI-vs-AI sandbox escape game. Found: (1) Claude
refuses to be the attacker, (2) prompting beat model size, (3) a local 7B built a
sandbox a 7B attacker couldn't crack. The model was never the interesting part —
the harness was. https://github.com/utsav1033/chor-police

---

### Notes
- Swap `https://github.com/utsav1033/chor-police` for the repo/writeup URL.
- First tweet gets the diagram image (`docs/diagram.svg` → PNG).
- Keep the honesty — the "illustrative, not rigorous" framing is part of why it
  reads as credible rather than hype.
