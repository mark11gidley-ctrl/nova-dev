---
name: nova-dev-audit
description: Audit the whole repo, not just a diff. Maps entry points and data flow, then ranks the most important problems and what to fix first. Use for "audit", "nova dev audit", or "what should I fix first".
---

# Nova Dev Audit

1. **Map the code first.** Find entry points (main, routes, CLI commands, jobs), how data moves between them, and the load the project expects (users, rows, requests). Use Glob and Grep; read only what you need.
2. **Check the same risks as the review:** broken callers, trust-boundary validation, data-loss handling, security, untested risky logic, slow paths at realistic size, and dead or duplicated code.
3. **Rank.** Number each finding: 1 = fix first. Label it **Must fix**, **Should fix** or **Nice to have**.
4. For each: file:line, what goes wrong with a concrete input, the smallest fix, and what happens if skipped.
5. End with one verdict line: what to fix first and why.

Do not list every style issue. Cap the report at the 10 most important findings and say how many were left out. If the repo is clean, say so and name what you could not check (for example, no runtime test was run).

End with the **Skipped / Risk** line.
