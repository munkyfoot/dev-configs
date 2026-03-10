# Guidelines

## 1) Prime Directive
Ship high-quality changes that are:
- Correct, maintainable, and readable
- Consistent with existing conventions
- Easy to review and understand (clear structure, sensible file organization, and helpful summaries)

Large changes are allowed and sometimes expected (e.g., greenfield apps, major refactors). In those cases:
- Prefer logical sequencing of changes and a clean final state over forced micro-commits.
- Provide a clear summary of what changed and how to verify it.

If clarification is needed before beginning a task, ask questions first. Once the task is well-defined (whether one change or many), complete it fully before prompting the user again.

---

## 2) Engineering Standards
### Language and Tooling Choices
- Use versions, package managers, and build tools that fit the repo and task constraints.
- If the repository already pins a language version or dependency workflow, follow it.
- If no version is specified, prefer a modern, stable release that is broadly compatible with the libraries in use.
- Keep environment and dependency management consistent with the repo.
- Pin or constrain dependencies appropriately for reproducible installs.
- Keep dev dependencies separate from runtime dependencies where practical.
- If introducing a new language or toolchain to a repo that did not previously use it, keep the setup simple and document it in the README.

### Code Structure and Maintainability
- Prefer explicit types or contracts at module boundaries where the language supports them.
- Keep components, modules, and functions focused; extract helpers or subcomponents when complexity grows.
- Avoid unsafe assertions, implicit coupling, and excessive prop or state threading when a clearer structure is available.
- Reuse existing project primitives and patterns before introducing new abstractions.

### Dependencies and Configuration
- Do not commit secrets. Use environment variables or existing secret-management patterns for configuration.

### Documentation and Comments
- Write code that reads cleanly without needing many comments.
- Add comments where they *increase understanding*, especially around:
  - Non-obvious logic, edge cases, or constraints
  - Performance considerations
  - “Why” something is done a certain way
- Keep comments proportional to complexity: simple code should not be narrated.

---

## 3) Repository Hygiene
### README Maintenance
Update `README.md` whenever you:
- Add or remove features
- Change usage, scripts, or configuration
- Introduce new setup steps (env vars, services, migrations, etc.)
- Modify how the app is built, run, or deployed

If unsure whether a change merits a README update, default to updating it.

### Configuration and Structure
- Follow existing repo patterns (folder structure, naming, lint rules).
- Don’t add new frameworks or major dependencies without a strong reason.
- Prefer incremental improvements over sweeping rewrites unless explicitly requested.

---

## 4) Workflow Expectations
### Before You Start
- If the task is ambiguous, ask concise questions up front.
- If the task is clear, proceed without extra chatter.

### While You Work
- Make changes in a logical sequence:
  1. Understand current behavior
  2. Implement the change
  3. Update tests (if present) or add coverage where practical
  4. Update documentation (README) as needed
  5. Ensure formatting/lint/typecheck passes

### Completion Standard
When the task is well-defined, finish it end-to-end before asking the user for the next step. That includes:
- Code changes
- Necessary refactors
- Documentation updates
- Basic validation (build/typecheck/tests if configured)

---

## 5) Testing and Verification
- Run the most relevant checks available in the repo (in priority order):
  - `npm test` (if present)
  - `npm run typecheck` (if present)
  - `npm run lint` (if present)
  - `npm run build`
- For Python projects, run what’s relevant if configured:
  - Unit tests (e.g., `pytest`)
  - Type checks (e.g., `mypy`, `pyright`)
  - Linters/formatters (e.g., `ruff`, `black`)
- If automated checks aren’t configured, do a basic “smoke review” of key flows.
- When you cannot run commands in the environment, still reason about correctness and note what should be run.

---

## 6) Error Handling and UX
- Handle errors gracefully with user-friendly messages in the UI.
- Avoid silent failures.
- Prefer clear loading, empty, and error states for async workflows.
- Keep accessibility in mind:
  - Proper labels
  - Focus management for dialogs/menus
  - Keyboard navigation where applicable

---

## 7) Security and Safety Basics
- Never commit secrets or tokens.
- Prefer environment variables for config.
- Validate and sanitize user input where relevant.
- Avoid insecure patterns (e.g., dangerouslySetInnerHTML) unless unavoidable and justified.

---

## 8) PR / Review Notes (If Applicable)
- Prefer reviewable changes, but do not avoid necessary large changes.
- Provide a short summary of:
  - What changed
  - Why it changed
  - How to verify it
  - Any follow-ups or known limitations

---

## 9) “If You’re Unsure” Rule
When uncertain between:
- **Doing nothing** vs **making a possibly risky change**: choose doing nothing and ask.
- **A simple approach** vs **a complex architecture**: choose simple unless requirements demand complexity.
- **Consistency with the repo** vs **personal preference**: choose repo consistency.