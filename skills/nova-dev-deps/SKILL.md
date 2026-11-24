---
name: nova-dev-deps
description: Dependency review: find packages used for only a few lines, duplicates, unused packages, and risky additions, and propose the smallest replacement. Use for "nova dev deps" or before adding a package.
---

# Nova Dev Deps

1. List the declared dependencies (package.json, requirements files, pyproject, Cargo.toml, go.mod).
2. For each, grep how much of it the code uses (`callers.py <package-name>`).
3. Flag:
   - **Used for a few lines:** propose the standard-library or platform replacement, with the lines.
   - **Unused:** propose removal after confirming no config or script refers to it.
   - **Duplicates:** two packages doing the same job.
   - **Risky additions:** new in the diff, few maintainers, or an unpinned version.
4. Do not remove anything yourself. Report the list with the replacement or removal for each, and the risk of each change.

End with Skipped / Risk. If the project has no dependency file, say so.
