---
name: nova-dev-explain
description: Explain a piece of code in plain words: what it does, the inputs and outputs, and what could go wrong. Use for "nova dev explain <file or symbol>" or "what does this do".
---

# Nova Dev Explain

Read only the code you need (Grep for the symbol, then Read its range).

Answer in this order:
1. **What it does:** one sentence.
2. **Inputs and outputs:** types, and what happens on empty or invalid input.
3. **Where it is used:** the callers, from `callers.py`, when the user is deciding whether to change it.
4. **What could go wrong:** the one or two failure modes that matter.

Keep it under 12 lines unless the user asks for more. Reference file:line for every claim.
