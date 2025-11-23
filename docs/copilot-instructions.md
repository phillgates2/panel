<!-- .github/copilot-instructions.md - Project-specific guidance for AI coding agents -->

# Copilot instructions for `panel`

This repository is small and currently contains a minimal surface (see `README.md`). These instructions explain how an AI coding agent can be immediately productive and what project-specific patterns to follow.

**Quick context**
- **Repo purpose**: `panel` — labeled in `README.md` as "oz panel". There are currently no `src/`, `pkg/`, or test directories checked in.
- **Branching**: Default branch is `main`. Work by creating feature branches and open a PR to `main`.

**Primary workflow for the agent**
- **Start by listing files**: run `git ls-files` or search the workspace for likely entry points (`src`, `app`, `cmd`, `package.json`, `pyproject.toml`). If nothing exists, confirm with the user before scaffolding.
- **Read `README.md`**: it may contain short project notes; treat it as authoritative until the user provides more context.
- **Avoid large refactors**: this repo appears minimal — prefer small, easily-reviewable changes.

**When adding code or scaffolding**
- **Ask first**: If you need to add a framework (Node/React/Django/etc.), propose choices to the user and wait for confirmation.
- **Create minimal runnable changes**: include a small README update and a simple run/test command in `package.json`/`pyproject.toml` when applicable.
- **Follow commit style**: small commits with clear messages (e.g., `feat: add X`, `fix: correct Y`).

**Project-specific checks and examples**
- There are no tests or build scripts present. If you add code, include a lightweight test and a one-line command to run it.
- Example search patterns to locate code or conventions in this repo:
  - `rg "module|package|src|index" -S` — look for common entry points
  - `git ls-files | rg "README|readme|cli|setup|package.json"` — find build or config files

**Merging / updating existing instructions**
- If a `.github/copilot-instructions.md` already exists, merge by preserving any project-specific notes and updating only inaccurate or stale lines. Do not delete historical rationale.

**What not to assume**
- Do not assume language, framework, or CI configuration — this repo currently lacks detectable language-specific files.
- Do not run or install large dependencies without approval.

**If uncertain / missing info**
- Ask the repo owner: request preferred language/framework, testing approach, and CI expectations.
- Provide a short proposal with options (2–3) and a recommended minimal implementation.

-- End of file
