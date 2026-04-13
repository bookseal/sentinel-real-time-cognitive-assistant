---
name: fix-issue
description: Fetch a GitHub issue by number, diagnose it, implement a fix on a new branch, run the test suite, and commit when tests pass. Use when the user says "fix issue N", "이슈 N 고쳐줘", "fix-issue 42", or references a GitHub issue number to resolve.
---

# Fix Issue Skill

이슈 번호를 받아 자동으로 조사 · 수정 · 테스트 · 커밋까지 수행한다. 목표는 "사람이 개입할 가치가 있는 판단 지점"만 사용자에게 묻고, 기계적으로 가능한 단계는 스킬이 책임지는 것.

## 0. 전제 조건 확인

스킬 시작 시 다음을 **병렬로** 확인한다.

1. `gh auth status` — GitHub CLI 인증 상태
2. `git status` — 작업 트리가 깨끗한지 (untracked는 허용, modified가 있으면 경고)
3. `git rev-parse --abbrev-ref HEAD` — 현재 브랜치
4. 사용자가 이슈 번호를 제공했는지 확인. 없으면 `gh issue list --state open`을 출력하고 사용자에게 선택을 요청한 뒤 스킬 종료.

작업 트리에 modified/staged 변경이 있으면 **즉시 멈추고** 사용자에게 "stash할까요 / 커밋할까요 / 계속 진행할까요"를 묻는다. 남의 작업을 덮어쓰지 않는 것이 최우선.

## 1. 이슈 컨텍스트 수집

`gh issue view <번호> --comments` 하나로 본문 + 모든 코멘트를 가져온다. 그 다음 본문에서 다음을 추출한다.

- **재현 방법** — 에러 메시지, 스택 트레이스, 재현 명령어
- **기대 동작 vs 실제 동작**
- **관련 파일/라인** — 이슈가 언급한 경로가 있으면 우선순위로
- **라벨** — `bug` / `security` / `performance` / `enhancement` / `good first issue` 등
- **참조 링크** — 연관 PR, 커밋, 외부 문서
- **담당자(assignee)** — 다른 사람에게 이미 할당되어 있으면 **진행 전 사용자에게 확인**

추출 결과를 한눈에 볼 수 있게 요약 블록으로 출력한 뒤 다음 단계로.

## 2. 원인 분석

코드를 수정하기 **전에** 먼저 원인을 특정한다. 추측으로 코드를 만지지 않는다.

- 이슈가 특정 파일/함수를 지목했다면 `Read`로 해당 범위를 읽는다
- 에러 메시지/스택 트레이스의 심볼을 `Grep`으로 찾아 호출 지점을 파악한다
- 관련 테스트가 있는지 `Glob`으로 `tests/test_*.py` 등에서 찾는다
- 광범위 탐색이 필요하면 `Agent` 툴(`subagent_type=Explore`)로 위임해 메인 컨텍스트를 보호한다

원인이 **확실하지 않으면** 사용자에게 "다음 두 가설 중 어느 쪽이 맞는지 확인해 주세요"라고 물어본다. 애매한 채로 계속 진행하지 않는다.

## 3. 작업 브랜치 생성

[CLAUDE.md](../../../CLAUDE.md) 컨벤션에 맞춰 브랜치를 만든다.

- 라벨이 `bug` → `fix/<short-description>`
- 라벨이 `security` → `hotfix/<short-description>`
- 라벨이 `enhancement`/`feature` → `feature/<short-description>`
- 라벨이 `documentation` → `docs/<short-description>`
- 그 외 → `fix/issue-<번호>`

`<short-description>`은 이슈 제목에서 추출한 케밥케이스 3~5 단어. 이슈 번호는 브랜치명에 넣지 않는다(CLAUDE.md의 "Phase 번호 금지" 규칙 정신에 맞춰).

```bash
git checkout -b fix/resample-int-normalization
```

이미 관련 브랜치가 존재하면 새로 만들지 말고 사용자에게 "기존 브랜치를 이어 쓸까요, 새로 만들까요?"를 묻는다.

## 4. 수정 구현

[CLAUDE.md](../../../CLAUDE.md)의 norminette 규칙을 지키며 수정한다.

- **최소 변경 원칙** — 이슈가 요구한 범위만 건드린다. 주변 리팩토링 금지
- **파일당 함수 7개 / 함수당 30줄 / 평탄한 제어흐름** 유지
- 수정하면서 관련 없는 코드에 docstring/주석/타입힌트를 추가하지 않는다
- 기존 스타일과 일관되게 작성 — 주변 코드가 따르는 패턴을 먼저 읽고 모방

변경 전에 수정 대상 파일을 **반드시 `Read`로 먼저 읽는다**. diff만 보고 수정하면 컨텍스트를 놓친다.

## 5. 테스트 추가

버그 수정이면 **"수정 없이 실행하면 실패하고, 수정 후에 통과하는 테스트"**를 먼저 추가하는 것이 이상적이다. 기존 테스트 파일 구조를 따른다.

- `tests/test_<module>.py`가 있으면 거기에 추가
- 없으면 새 파일을 만들되 이슈 범위 밖의 테스트는 건드리지 않음
- 회귀 방지 테스트에는 이슈 번호를 주석으로 남긴다: `# Regression test for #42`

## 6. 테스트 실행

프로젝트 테스트 명령을 **자동 탐지**한다.

1. `pytest` 있으면 → `pytest -x --tb=short`
2. `package.json`에 `test` 스크립트 → `npm test`
3. `Makefile`에 `test` 타겟 → `make test`
4. `cargo` 프로젝트 → `cargo test`

실패가 나면:
- **수정 전에 이미 실패하던 테스트**인지 구분한다 (다른 이슈일 수 있음)
- 수정으로 **새로 깨뜨린** 테스트면 원인을 파악해 고치거나, 못 고치겠으면 사용자에게 보고하고 커밋은 **하지 않는다**
- 같은 실패를 반복해서 시도하지 않는다. 3회 이상 같은 패턴으로 실패하면 멈추고 사용자에게 상황 보고

테스트가 없는 프로젝트라면 최소한 변경된 모듈을 `python -c "import <module>"` 등으로 import 스모크 테스트라도 수행한다.

## 7. 린터/포매터

프로젝트에 린터가 설정되어 있으면 실행한다 (`ruff`, `black`, `eslint`, `prettier` 등). 설정이 없으면 건너뛴다. **스킬이 임의로 린터를 설치하지 않는다.**

## 8. 커밋

테스트가 모두 통과했을 때만 커밋한다. Conventional Commits 규칙([CLAUDE.md](../../../CLAUDE.md))을 따른다.

```
<type>: <짧은 설명> (#<이슈번호>)

<본문 — 왜 이 수정이 필요한지, 어떻게 고쳤는지>

Closes #<이슈번호>

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

- `type`은 라벨에서 유도: bug→`fix`, security→`fix`, enhancement→`feat`, docs→`docs`
- 제목은 50자 이내, 마침표 없음
- 본문은 "what"이 아니라 **"why"** — 코드를 보면 무엇이 바뀌었는지는 알 수 있음
- `Closes #N` 키워드로 이슈 자동 닫힘 연결

스테이징은 명시적으로 파일을 지정한다. `git add .` / `git add -A` **금지** (실수로 `.env` 등 포함 위험).

```bash
git add path/to/fixed_file.py tests/test_fixed_file.py
git commit -m "$(cat <<'EOF'
fix: normalize int16 audio before resampling (#42)

Gradio mic input returns int16 but resample_to_16k only cast to
float32 without rescaling to [-1, 1]. This fed unnormalized values
into Silero VAD and OpenAI WAV encoding, producing garbage output.

Closes #42

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

## 9. 완료 보고

사용자에게 다음 정보를 명확히 전달한다.

- ✅ 수정한 파일 목록 (클릭 가능한 마크다운 링크)
- ✅ 추가/수정한 테스트
- ✅ 테스트 실행 결과 요약
- ✅ 생성한 브랜치명과 커밋 해시
- ⏭️ **다음 단계 제안** — "PR 생성할까요?" (푸시는 사용자 확인 후)

## 10. 금지 사항

- 🚫 **푸시 금지** — `git push`는 사용자가 명시적으로 요청할 때만
- 🚫 **force push 금지** — 이 스킬은 force push를 절대 하지 않음
- 🚫 **이슈에 자동 코멘트/라벨 변경 금지** — `gh issue comment`, `gh issue edit` 등은 사용자가 명시적으로 요청할 때만
- 🚫 **pre-commit hook 우회 금지** — `--no-verify` 사용하지 않음. hook이 실패하면 원인을 고친 뒤 **새 커밋** (amend 아님)
- 🚫 **관련 없는 파일 수정 금지** — 이슈 범위 밖 파일은 건드리지 않음
- 🚫 **스코프 확장 금지** — "이 김에 저것도" 하지 않음. 별도 이슈로 제안만

## 11. 중단 조건

다음 경우에는 수정을 멈추고 사용자에게 상황을 설명한 뒤 판단을 요청한다.

- 원인이 코드 한 곳이 아니라 아키텍처 수준이라 단순 수정이 불가능
- 수정에 외부 서비스 변경/인프라 수정이 필요
- 기존 테스트가 깨지는데 의도된 breaking change인지 판단 필요
- 이슈 설명이 모호해 여러 해석이 가능
- 수정 범위가 +200줄을 넘어설 것 같음 (작은 수정이 아니라 기능 개발에 가까움)

이런 경우 스킬은 **분석 리포트까지만 내놓고 멈춘다**. 억지로 수정하지 않는다.
