#Requires -Version 5.0
<#
    install-notebooklm-skill.ps1
    ----------------------------
    (Windows PowerShell 버전) notebooklm-manager 서브에이전트가 사용하는 upstream
    `notebooklm` 스킬을 이 저장소의 .claude\skills\notebooklm 에 설치(clone)한다.

    사용법 (저장소 폴더 안에서 실행):
      powershell -ExecutionPolicy Bypass -File scripts\install-notebooklm-skill.ps1
      # 전역(%USERPROFILE%\.claude\skills)에 설치하려면:
      $env:TARGET="global"; powershell -ExecutionPolicy Bypass -File scripts\install-notebooklm-skill.ps1
#>
$ErrorActionPreference = 'Stop'

$Upstream = 'https://github.com/PleasePrompto/notebooklm-skill'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoRoot  = Split-Path -Parent $ScriptDir

if ($env:TARGET -eq 'global') {
    $SkillsDir = Join-Path $HOME '.claude\skills'
} else {
    $SkillsDir = Join-Path $RepoRoot '.claude\skills'
}
$Dest = Join-Path $SkillsDir 'notebooklm'

Write-Host "▶ notebooklm 스킬 설치 대상: $Dest"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git 이 필요합니다. 'Git for Windows'(https://git-scm.com/download/win) 설치 후 다시 실행하세요."
    exit 1
}

New-Item -ItemType Directory -Force -Path $SkillsDir | Out-Null

if (Test-Path (Join-Path $Dest '.git')) {
    Write-Host "▶ 이미 설치됨 — upstream 변경 사항을 pull 합니다."
    try { git -C $Dest pull --ff-only }
    catch { Write-Warning "pull 실패(로컬 변경 등). 수동 확인이 필요합니다: $Dest" }
}
elseif (Test-Path $Dest) {
    Write-Error "$Dest 가 이미 존재하지만 git 저장소가 아닙니다. 확인 후 옮기거나 지우세요."
    exit 1
}
else {
    Write-Host "▶ clone: $Upstream"
    git clone --depth 1 $Upstream $Dest
}

Write-Host ""
Write-Host "✔ 설치 완료: $Dest"
Write-Host ""
Write-Host "다음 단계:"
Write-Host "  1) cd `"$Dest`""
Write-Host "  2) python scripts\run.py auth_manager.py status   # 인증 상태 확인(최초 1회 로그인)"
Write-Host "  3) 이후에는 notebooklm-manager 에이전트에게 자연어로 요청하세요."
Write-Host ""
Write-Host "참고: 이 스킬은 실제 Chrome 브라우저를 구동하므로 로컬 Claude Code 에서만 동작합니다."
