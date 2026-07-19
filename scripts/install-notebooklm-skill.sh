#!/usr/bin/env bash
#
# install-notebooklm-skill.sh
# ---------------------------
# notebooklm-manager 서브에이전트가 사용하는 upstream `notebooklm` 스킬을
# 이 저장소의 .claude/skills/notebooklm 에 설치(clone)한다.
#
# - upstream: https://github.com/PleasePrompto/notebooklm-skill
# - 스킬 자체는 이 저장소에 vendoring 하지 않고 clone 으로 가져온다(.gitignore 처리됨).
#   → upstream 업데이트를 `git -C .claude/skills/notebooklm pull` 로 손쉽게 반영.
#
# 사용법:
#   bash scripts/install-notebooklm-skill.sh          # 저장소 로컬(.claude/skills)에 설치
#   TARGET=global bash scripts/install-notebooklm-skill.sh   # ~/.claude/skills 에 설치
#
set -euo pipefail

UPSTREAM="https://github.com/PleasePrompto/notebooklm-skill"

# 이 스크립트가 있는 저장소 루트로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ "${TARGET:-repo}" = "global" ]; then
  SKILLS_DIR="${HOME}/.claude/skills"
else
  SKILLS_DIR="${REPO_ROOT}/.claude/skills"
fi

DEST="${SKILLS_DIR}/notebooklm"

echo "▶ notebooklm 스킬 설치 대상: ${DEST}"

if ! command -v git >/dev/null 2>&1; then
  echo "✖ git 이 필요합니다. 설치 후 다시 실행하세요." >&2
  exit 1
fi

mkdir -p "${SKILLS_DIR}"

if [ -d "${DEST}/.git" ]; then
  echo "▶ 이미 설치됨 — upstream 변경 사항을 pull 합니다."
  git -C "${DEST}" pull --ff-only || {
    echo "⚠ pull 실패(로컬 변경 등). 수동 확인이 필요합니다: ${DEST}" >&2
  }
elif [ -e "${DEST}" ]; then
  echo "✖ ${DEST} 가 이미 존재하지만 git 저장소가 아닙니다. 확인 후 옮기거나 지우세요." >&2
  exit 1
else
  echo "▶ clone: ${UPSTREAM}"
  git clone --depth 1 "${UPSTREAM}" "${DEST}"
fi

echo
echo "✔ 설치 완료: ${DEST}"
echo
echo "다음 단계:"
echo "  1) cd ${DEST}"
echo "  2) python scripts/run.py auth_manager.py status   # 인증 상태 확인(최초 1회 로그인)"
echo "  3) 이후에는 notebooklm-manager 에이전트에게 자연어로 요청하세요."
echo
echo "참고: 이 스킬은 실제 Chrome 브라우저를 구동하므로 로컬 Claude Code 에서만 동작합니다."
