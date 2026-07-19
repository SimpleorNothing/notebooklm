# notebooklm-agent

Google NotebookLM을 관리·질의하는 Claude Code 서브에이전트(스킬).

NotebookLM에는 공개 API가 없으므로, 이 스킬은 **저장된 Google 로그인 세션으로
실제 웹 UI를 Playwright로 자동 조작**해서 노트북 목록 조회·질의를 수행한다.

## 설치

리포 루트에서 스킬을 프로젝트의 `.claude/skills/notebooklm` 로 설치한다:

```bash
bash scripts/install-notebooklm-skill.sh
cd .claude/skills/notebooklm
python scripts/run.py auth_manager.py status   # 최초 1회: 의존성 부트스트랩 + 로그인 확인
python scripts/run.py auth_manager.py login     # 최초 1회 Google 로그인
# 이후 "내 NotebookLM에 물어봐줘 …" 식으로 에이전트에게 요청
```

`scripts/run.py` 가 첫 실행 때 `.venv` 를 만들고 Playwright(드라이버)를 설치한다.
Chromium 브라우저는 환경에 이미 있으면 그대로 쓰고, 없으면
`NBLM_CHROMIUM_PATH` 로 지정할 수 있다.

## 사용법

```bash
# 노트북 목록
python scripts/run.py notebooklm.py list
python scripts/run.py notebooklm.py list --json

# 노트북에 질문 (제목 일부 또는 노트북 id)
python scripts/run.py notebooklm.py ask --notebook "Research" "핵심 결론 3가지 요약해줘"
python scripts/run.py notebooklm.py ask --notebook <id> "질문" --json --timeout 120
```

에이전트에게는 그냥 자연어로 요청하면 된다:
- "내 NotebookLM에 물어봐줘: X 노트북에서 최신 실적 요약"
- "list my notebooks"

## 인증

세션은 Playwright `storage_state` 로 `.auth/state.json` 에 저장된다(gitignore).

| 명령 | 설명 |
| --- | --- |
| `auth_manager.py status` | 유효 세션 여부 확인 |
| `auth_manager.py login` | 헤디드 브라우저로 Google 로그인 후 세션 저장 |
| `auth_manager.py import <file>` | 다른 곳에서 export 한 storage_state 가져오기 |
| `auth_manager.py logout` | 저장된 세션 삭제 |

### 헤드리스/클라우드 환경 (디스플레이 없음)

컨테이너에는 보통 화면이 없어 `login` 이 브라우저를 띄울 수 없다. 이때는 **내 PC의
일반 Chrome/Chromium 으로 NotebookLM 에 로그인**한 뒤 세션을 내보내 `import` 한다.

내 PC에서 Playwright 로 한 번 로그인하고 상태를 저장하는 예:

```python
# export_state.py  (로컬 PC에서 실행, 화면 있는 곳)
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=False)
    ctx = b.new_context()
    pg = ctx.new_page()
    pg.goto("https://notebooklm.google.com/")
    input("로그인 완료 후 Enter…")   # 브라우저에서 직접 로그인
    ctx.storage_state(path="state.json")
    b.close()
```

생성된 `state.json` 을 서버로 복사한 뒤:

```bash
python scripts/run.py auth_manager.py import /path/to/state.json
python scripts/run.py auth_manager.py status
```

## 리포 구조

```
notebooklm/
├── README.md
├── scripts/
│   └── install-notebooklm-skill.sh   # skill/ → .claude/skills/notebooklm 설치
└── skill/                            # 설치되는 스킬 소스
    ├── SKILL.md                      # 스킬 정의(트리거/워크플로)
    ├── requirements.txt
    ├── config/selectors.json         # 튜닝 가능한 DOM 셀렉터
    └── scripts/
        ├── run.py                    # venv 부트스트랩 + 실행 런처
        ├── _browser.py               # 공용 브라우저/세션 헬퍼
        ├── auth_manager.py           # 로그인 세션 관리
        └── notebooklm.py             # list / ask / open
```

## 문제 해결

NotebookLM UI 는 예고 없이 바뀐다. `list`/`ask` 가 요소를 못 찾으면
`skill/config/selectors.json` 을 수정한다(각 키의 배열에서 먼저 보이는 것이 우선).
`--debug` 를 붙이면 실패 시 `.auth/debug-*.png|html` 를 남긴다.

드라이버/Chromium 버전 불일치로 실행이 안 되면
`NBLM_PLAYWRIGHT_VERSION=<x.y.z>` 로 드라이버 버전을 맞춘다.

## 주의

- 사적인 Google API 가 아니라 사람이 쓰는 것과 동일한 웹 UI 를 자동화한다. 사용자
  본인 계정과 Google 약관의 적용을 받는다.
- `.venv/`, `.auth/` 는 로컬 런타임 상태이므로 절대 커밋하지 않는다.
