# CLAUDE.md — Project-level instructions for Claude Code

## Code Style: norminette-inspired (42 School)

Keep code short, readable, and easy to scan — inspired by 42's norminette rules.

- **Max 7 functions per file.** If a file grows beyond this, split into modules.
- **Max 30 lines per function** (excluding docstrings and blank lines).
- **One responsibility per function.** If you need a comment to explain a block, extract it.
- **Prefer flat over nested.** Early returns instead of deep if/else.
- **File splits over long files.** When a file exceeds ~150 lines, consider splitting.

## Git Conventions

### Branch naming: `type/short-description`
- `feature/persistent-alert` — new feature
- `fix/dockerfile-env-syntax` — bug fix
- `hotfix/security-patch` — urgent production fix
- `chore/update-dependencies` — maintenance
- `docs/api-reference` — documentation only
- `refactor/simplify-gauge` — code cleanup, no behavior change

Do NOT put phase numbers in branch names. Use tags for milestones.

### Tags: Semantic Versioning for milestones
- `v0.0.x` — v0.0 (minimal volume gauge)
- `v0.1.x` — v0.1 (VAD + emotion)
- `v0.2.x` — v0.2, etc.

### Commits: Conventional Commits
- `feat: add persistent 10s alert banner`
- `fix: dockerfile inline comment syntax`
- `docs: add infrastructure status report`
- `chore: remove unused v0.1 files`
- `refactor: simplify gauge HTML`

## Development Workflow — Balanced with Claude Code

This project is built step-by-step as a learning portfolio. Claude Code is a
co-pilot, not an autopilot. The workflow balances speed with understanding.

### Per-issue cycle

1. **Goal** — I state what I want to build (one sentence)
2. **Scaffold** — Claude generates working code or a starting point
3. **Understand** — I read every line. If something is unclear, I ask "why?"
4. **Modify** — I adjust to my style, rename variables, add my own touches
5. **Test** — `python app.py` (or pytest) after every change
6. **Commit** — only code I can explain. `git add <specific files>`, never `git add .`
7. **PR + review** — Claude runs the review skill, I read findings, fix if needed
8. **Merge + close** — squash merge, pull main, close issue with learning summary

### Principles

- **Don't commit code I can't explain.** Claude can write it, but I must understand it before it enters main.
- **Ask "why?" freely.** No question is too basic. Understanding > speed.
- **Print-first debugging.** When unsure what data looks like, `print()` it before writing logic.
- **Spike → implement.** For unfamiliar APIs, explore first (30 min), then plan. Don't write detailed checklists for things you haven't tried.
- **Small PRs, single purpose.** One issue = one branch = one PR. Each PR should be reviewable in under 5 minutes.
- **Learning notes in every PR.** The "Learning notes" section in PR body is mandatory — it's the portfolio's voice.

### What Claude should do

- Generate code scaffolds when asked
- Explain concepts using C analogies (user has 2+ years of C background)
- Fix bugs directly (edit the file) rather than just describing what to change
- Keep explanations concise — teach the concept, not the textbook
- Flag security/performance issues proactively in reviews

### What Claude should NOT do

- Write full solutions without being asked — offer scaffolds and let user fill gaps
- Give 30-minute reading assignments (`help()`, docs deep-dives) as the first step
- Over-explain when user says "했다" (done) — move to next step quickly
- Add features beyond what the current issue asks for

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
