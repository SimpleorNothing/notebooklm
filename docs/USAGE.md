# 사용법 & 명령 레퍼런스

`notebooklm-manager` 에이전트가 내부적으로 실행하는 명령들을 정리한다. 모든 명령은
스킬 루트(`<SKILL_DIR>` = `.claude/skills/notebooklm` 또는 `~/.claude/skills/notebooklm`)에서
`python scripts/run.py [스크립트]` 래퍼로 실행한다. 래퍼가 `.venv/` 생성·의존성 설치·활성화를
자동 처리하므로 스크립트를 **직접** 호출하지 않는다.

```bash
cd <SKILL_DIR>
```

## 1. 인증 — `auth_manager.py`

```bash
# 인증 상태 확인
python scripts/run.py auth_manager.py status

# 로그인 설정(보이는 브라우저로 Google 로그인) — 최초 1회
python scripts/run.py auth_manager.py setup --show-browser
```

인증 정보는 `<SKILL_DIR>/data/`에 영속 저장된다.

## 2. 라이브러리 — `notebook_manager.py`

```bash
# 목록
python scripts/run.py notebook_manager.py list

# 추가 (스마트 추가: 내용을 모르면 먼저 질의해 파악 후 채워 넣는다)
python scripts/run.py notebook_manager.py add \
  --url "<노트북 URL>" \
  --name "<이름>" \
  --description "<한 줄 설명>" \
  --topics "주제1,주제2,주제3"

# 주제로 검색 / 활성 노트북 지정 / 삭제
python scripts/run.py notebook_manager.py search --topics "<주제>"
python scripts/run.py notebook_manager.py activate --notebook-id <ID>
python scripts/run.py notebook_manager.py remove --notebook-id <ID>
```

라이브러리는 `<SKILL_DIR>/data/library.json`에 저장된다.

## 3. 질의 — `ask_question.py`

```bash
python scripts/run.py ask_question.py \
  --question "<질문>" \
  [--notebook-id <ID> | --notebook-url <URL>] \
  [--show-browser]
```

- 라이브러리에 노트북이 여러 개면 질문 주제에 맞는 것을 골라 `--notebook-id`로 지정한다.
- 답변에는 NotebookLM의 인용(citation)이 포함된다 — 사용자에게 근거와 함께 전달한다.

## 4. 정리 — `cleanup_manager.py`

```bash
python scripts/run.py cleanup_manager.py --help
```

로컬 데이터·브라우저 상태를 정리한다.

## 에이전트 동작 패턴

1. **스킬 존재 확인** → 없으면 `bash scripts/install-notebooklm-skill.sh`로 설치.
2. **인증 확인**(`auth_manager.py status`) → 필요 시 로그인 안내.
3. **노트북 선택**: 라이브러리에서 질문에 맞는 노트북 선택(없으면 스마트 추가).
4. **질의** 후 **자기 검토**: 답이 요청을 완전히 충족했는지 확인, 부족하면 후속 질문
   (레이트 리밋 고려), 그다음 **종합 답변**을 출처와 함께 사용자에게 전달.

## 트러블슈팅

| 증상 | 원인/조치 |
| --- | --- |
| 브라우저가 안 뜨거나 네트워크 오류 | 샌드박스/웹 환경에서 실행 중일 가능성 — 로컬 Claude Code에서 실행. |
| 인증 만료/실패 | `auth_manager.py setup --show-browser`로 재로그인. |
| 질의가 갑자기 막힘 | 무료 계정 하루 ~50회 제한 도달 가능 — 다음 날 재시도. |
| 답이 빈약/맥락 유실 | 세션 비영속 특성 — 질문 문장에 필요한 맥락을 모두 포함. |
| `python`/의존성 오류 | 항상 `scripts/run.py` 래퍼로 실행(직접 호출 금지). |
