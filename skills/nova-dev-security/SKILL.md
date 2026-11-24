---
name: nova-dev-security
description: Security pass on a change: input validation at trust boundaries, injection, secrets in code, auth checks, unsafe file paths, and dependency risk. Use for "nova dev security" or before shipping anything that takes outside input.
---

# Nova Dev Security

Scan the change (`git diff HEAD`, or the files named) for:

- **Input at a trust boundary** (HTTP, CLI args, files, webhooks, env): validated before use?
- **Injection:** SQL, shell, template, path, and HTML built from input. Use parameters, argument lists, path joins with checks, escaping.
- **Path traversal:** user-supplied file names joined to a folder without normalizing and checking the prefix.
- **Secrets:** keys, tokens, passwords, or private URLs in code, tests, fixtures or logs. Grep for `key|token|secret|password|BEGIN .* PRIVATE`.
- **Auth:** every new route or command checks who may call it.
- **Unsafe defaults:** TLS off, debug on, wildcard CORS, world-readable files.
- **Dependencies:** a new package with few users or a recent ownership change.

For each finding: file:line, the attack in one sentence, the smallest fix, and severity. End with the Skipped / Risk line. Do not report theoretical issues with no path from outside input.
