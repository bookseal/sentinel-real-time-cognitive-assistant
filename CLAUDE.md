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
