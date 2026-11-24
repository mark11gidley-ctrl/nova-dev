---
name: nova-dev-pr
description: Write a pull request description: what changed, why, how it was checked, and what was skipped or risky. Mirrors the repo's PR template when one exists. Use for "nova dev pr" or before opening a pull request.
---

# Nova Dev PR

1. Look for a PR template (`.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE/`, `docs/`). If one exists, use its headings and fill them in. Skip any section asking for credentials, environment variables or internal hostnames.
2. Otherwise use these headings:
   - **What changed:** the behavior change in 2 to 4 lines.
   - **Why:** the problem it solves.
   - **How it was checked:** the exact test or command and its result. Say if none was run.
   - **Skipped and risk:** what you did not do and what the reviewer should look at first.
3. Keep it under 250 words. Reference files as `path:line`.
4. Do not open the pull request unless the user asks.
