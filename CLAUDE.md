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
- `v0.0.x` — Phase 00 (minimal volume gauge)
- `v0.1.x` — Phase 01 (VAD + emotion)
- `v0.2.x` — Phase 02, etc.

### Commits: Conventional Commits
- `feat: add persistent 10s alert banner`
- `fix: dockerfile inline comment syntax`
- `docs: add infrastructure status report`
- `chore: remove unused Phase 01 files`
- `refactor: simplify gauge HTML`
