# notebooklm-agent

**Google NotebookLM을 관리·질의하는 Claude Code 서브에이전트.**

NotebookLM(Gemini)은 업로드된 문서만 근거로 답하므로 환각이 크게 줄어든다. 이 저장소는
그 NotebookLM을 Claude Code에서 자연어로 다룰 수 있게 해주는 **`notebooklm-manager`
서브에이전트**와, 그 에이전트가 구동하는 **`notebooklm` 스킬 설치 스크립트**로 구성된다.

> 동작 원리: `Claude가 NotebookLM에 질문 → Gemini가 출처 기반으로 답변 → Claude가 그
> 답을 근거로 작업`. 앱 사이를 복붙할 필요가 없다.

## 구성

```
.claude/agents/notebooklm-manager.md   서브에이전트 정의(시스템 프롬프트·툴)
scripts/install-notebooklm-skill.sh    upstream notebooklm 스킬 설치(clone) 부트스트랩
docs/USAGE.md                          명령 레퍼런스·상세 사용법
.gitignore                             clone된 스킬·로컬 데이터 제외
```

스킬 본체는 이 저장소에 vendoring하지 않고, 설치 스크립트가
[PleasePrompto/notebooklm-skill](https://github.com/PleasePrompto/notebooklm-skill)을
`.claude/skills/notebooklm`에 clone한다(→ upstream 업데이트 반영이 쉽다).

## ⚠️ 로컬 전용

이 스킬은 **실제 Chrome 브라우저**를 띄워 NotebookLM을 조작한다(Patchright 기반). 따라서
샌드박스 웹 환경(claude.ai/code 등)에서는 동작하지 않고, **사용자의 로컬 Claude Code
설치에서만** 실행된다.

## 설치

> **사전 준비**: Git, Python 3.10+, 그리고 로컬 [Claude Code](https://claude.com/claude-code).
> Windows는 [Git for Windows](https://git-scm.com/download/win)가 필요하다.

0) 먼저 이 저장소를 로컬에 clone한다(시스템 폴더가 아닌 작업 폴더에서):

```bash
# macOS / Linux
cd ~/projects
git clone https://github.com/SimpleorNothing/notebooklm.git
cd notebooklm
```
```powershell
# Windows PowerShell — C:\WINDOWS\system32 같은 곳이 아니라 개인 작업 폴더에서
cd $HOME\Documents
git clone https://github.com/SimpleorNothing/notebooklm.git
cd notebooklm
```

1) 스킬을 설치한다:

```bash
# macOS / Linux
bash scripts/install-notebooklm-skill.sh
# 전역(~/.claude/skills)에 설치하려면:  TARGET=global bash scripts/install-notebooklm-skill.sh
```
```powershell
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts\install-notebooklm-skill.ps1
# 전역(%USERPROFILE%\.claude\skills)에 설치하려면:
#   $env:TARGET="global"; powershell -ExecutionPolicy Bypass -File scripts\install-notebooklm-skill.ps1
```

2) 에이전트를 사용할 프로젝트의 `.claude/agents/`에 `notebooklm-manager.md`가 인식되도록
   둔다. 이 저장소를 그대로 쓰면 이미 `.claude/agents/`에 있으므로 별도 작업이 없다.

3) 최초 1회 인증:

```bash
# macOS / Linux
cd .claude/skills/notebooklm   # 또는 ~/.claude/skills/notebooklm
python scripts/run.py auth_manager.py status
```
```powershell
# Windows PowerShell
cd .claude\skills\notebooklm
python scripts\run.py auth_manager.py status
```

4) 이 `notebooklm` 폴더에서 로컬 Claude Code를 실행하면 `.claude/agents/`의
   `notebooklm-manager` 에이전트가 자동 인식된다. 이후 자연어로 요청하면 된다.

## 사용 예 (자연어)

에이전트에게 자연어로 요청하면 된다:

- "NotebookLM 인증 상태 확인해줘 / 로그인 설정해줘"
- "이 링크를 내 NotebookLM 라이브러리에 추가해줘: `<노트북 URL>`"
- "내 React 문서 노트북에 라우팅 관련해서 뭐라고 돼 있는지 물어봐줘"
- "내 NotebookLM 노트북 목록 보여줘"

내부적으로는 `notebooklm` 스킬을 `python scripts/run.py <스크립트>`로 구동한다. 자세한
명령·전략은 [`docs/USAGE.md`](docs/USAGE.md) 참고.

## 알아둘 제약

- **레이트 리밋**: 무료 계정 하루 약 50회 질의.
- **세션 비영속**: 질문마다 새 브라우저 — 맥락이 이어지지 않으므로 후속 질문에 이전
  맥락을 다시 담아야 한다(에이전트가 자동으로 종합 처리).
- **문서 업로드 수동**: 소스 문서 업로드는 NotebookLM 웹에서 사용자가 직접 한다.

## 크레딧

스킬 본체: [PleasePrompto/notebooklm-skill](https://github.com/PleasePrompto/notebooklm-skill) (MIT).
이 저장소는 그 스킬을 감싸 **관리 에이전트** 형태로 사용하기 쉽게 만든 래퍼다.
