# The journey — why it got built this way

The code is the *what*. This is the *why* — the decisions and the dead ends. It's
the most useful doc for learning, because the pivots are where the real lessons
are. (It's also the raw material for the write-up / thread.)

---

### Start: a sandbox-escape game, with some baggage

The original idea: build a sandbox, let an AI attacker try to break out and grab
fake flags, let an AI defender patch the holes, repeat — plus fine-tuning a local
model on winning attacks.

**First cut: drop the fine-tuning.** It was the most work for the least certain
payoff. What makes the box better is: escapes become permanent tests, and the
defender patches holes. None of that needs fine-tuning. The "memory" of what was
learned is better as a Markdown notebook + tests you can read than as opaque
weights. → *Cut it. Scope got sharper immediately.*

---

### Decision: model outside, harness relays commands in

The safety-critical call. If the attacker model ran *inside* the VM, it would
need real credentials and a way out. Instead: the model runs on the Mac with no
tools; a referee takes each proposed command and runs it *inside* the jail.

This isn't a compromise — it's how real agent-sandbox escape actually works (the
LLM is hosted; its shell tool runs in a sandbox). → *The referee became the center
of the whole system.*

---

### Reality check: OrbStack isn't isolated by default

A background research pass (and a live test) found OrbStack mounts your Mac files
and lets the VM run Mac commands *by default*. The fix: `--isolated
--isolate-network`. We then wrote an isolation check that must pass before any
attack runs. → *Lesson: verify your boundary, don't assume it.*

A smaller gotcha that cost real time: our first isolation check reported FAIL on a
box that was actually fine — a `set -o pipefail` + `grep` interaction made every
check invert. The box was sound; the *test* was wrong. → *Trust, then verify your
verifier.*

---

### The wall: Claude won't be the attacker

Running the attacker as a Claude model, the API refused — `cyber` safety
classifier. Three times across the session, the "AI generates escape commands"
framing got flagged. The defender side never did.

The tempting move — "use a smaller/older Claude model, its classifier is weaker" —
is exactly safeguard-evasion, and we *didn't* do it. The legitimate path: make the
attacker either a fixed, human-written **playbook** or a **local open model**
(Qwen) you run yourself. → *Lesson: when a model refuses dual-use generation,
that's a signal, not an obstacle to route around. Redesign instead.*

---

### Reframe: deliberate faults make it a real measurement

Against a *good* box, every attacker scores 0 — and you can't tell if that's a
smart box or a dumb attacker. So we flipped it: **plant known holes** (a fault
deck) and measure which attacker catches which. Now "caught 3/5" means something.
This is how real sandbox-escape benchmarks are built. → *Lesson: to measure a
capability, build known-answer tests; don't infer it from an uncontrolled game.*

---

### The surprise: prompting beat model size

First attacker-ladder run was flat and noisy (2–3 / 5 across 1.5B→7B) and nobody
cracked the hard recon box. Easy to blame model size. But the real culprit was the
*prompt* — bare, no methodology. Adding a skill file ("recon at most twice, then
you MUST read something; `ls` never prints a token") + a few-shot example + a bit
more budget took 3B and 7B to **5/5**, and both cracked the hard box.

→ *The headline lesson: fix the scaffolding before you reach for a bigger model.*

---

### A subtle bug that taught the point twice

The Qwen-vs-Qwen duel ran the *identical* 8 attacker commands every round. Cause:
generation was deterministic (greedy). Adding temperature gave varied
trajectories. → *Lesson: determinism is invisible until your agent does the exact
same thing forever. Sampling is a capability knob, not just a vibe.*

---

### The ending: a 7B built a sound box; scaffolding has a ceiling

Final capstone flipped the earlier prediction. A Qwen-7B *defender* wrote a
genuinely tight-but-usable policy (its own JSON), and a *scaffolded* Qwen-7B
attacker — now actually `cat`-ing files and probing hidden paths — still couldn't
break it, because the box has no hole.

→ *Two lessons in one: (1) small models can defend better than you'd guess when
the task is structured JSON; (2) scaffolding makes an attacker competent at known
moves but not creative at new ones — against a sound box, trying hard correctly
yields nothing.*

---

## The through-line

Every pivot was the same shape: **the model wasn't the interesting part — the
system around it was.** Isolation, the referee/gate, structured policies, the
eval with a counter-metric, the scaffolding. That's agent infrastructure, and
it's where almost all the leverage lived.
