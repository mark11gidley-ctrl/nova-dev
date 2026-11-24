---
name: nova-dev-triage
description: Triage a bug report: reproduce it, find the failing code, rank severity, and name the smallest safe fix. Use for "nova dev triage" or when given an error or a bug description.
---

# Nova Dev Triage

1. **Reproduce:** get the exact steps, input, or command. If it cannot be reproduced, list what was tried and what info is missing. Stop there.
2. **Locate:** from the error text or steps, find the failing code (Grep for the message, then Read the range). Use `callers.py` to see who reaches it.
3. **Severity:** Critical (data loss, security, crash for everyone), High (a core flow broken), Medium (edge case, workaround exists), Low (cosmetic).
4. **Root cause:** one sentence on why it fails, with file:line.
5. **Smallest fix:** the change, and the callers it affects.
6. **Test:** the test that would have caught it.

Report in that order. End with Skipped / Risk.
