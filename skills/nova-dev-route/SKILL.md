---
name: nova-dev-route
description: Model routing for delegated work, so subagents do not silently inherit the expensive main-loop model. Use when planning subagent or workflow calls, or for "nova dev route".
---

# Nova Dev Route

Every subagent call sets an explicit model. Subagents inherit the main model otherwise, so a fan-out from a top-tier session spends top-tier usage on routine work.

| Work | Model |
|------|-------|
| Run a command and report output; single-file lookups; counting; formatting | haiku (`nova-runner`, `nova-scout`) |
| Code search and exploration; reading and summarizing; boilerplate edits; running tests | sonnet (`nova-reader`) |
| Non-trivial implementation; debugging; refactors; code review; synthesis | opus |
| Architecture with lasting consequences; security-critical analysis; final verification where a wrong answer is expensive | top tier |

Rules:
- Escalate, do not start high: if a sonnet result is weak, rerun on opus; only then the top tier.
- Most subagent calls should be sonnet or opus. Top-tier calls should be rare (about 1 in 10 at most), and each one should be justifiable.
- Routing governs delegation only. Never downgrade the main conversation.
- In workflow scripts, set the model option on every agent call.
