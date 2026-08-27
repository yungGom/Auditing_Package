# harden_webview2.ps1 — WebView2 런타임 업데이트/원격측정 체크 선택적 차단
#
# 기본 배포에 포함되지 않는다. 보안 요구가 강한 환경(IT팀이 사내 정책상 요구하는
# 경우)에서만 IT팀이 직접, 이해하고 적용한다. DSD_footing 자체는 이 스크립트 없이도
# 완전히 동작한다 — 이건 "우리 도구"가 아니라 "Windows/WebView2 시스템 컴포넌트"의
# 설정이다(CLAUDE.md "네트워크·오프라인 범위" 절 참고).
#
# 무엇을 바꾸는가:
#   HKLM\SOFTWARE\Policies\Microsoft\EdgeUpdate
#     UpdateDefault = 0                                    (전체 업데이트 체크 끔)
#     Update{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5} = 0      (WebView2 런타임 개별 지정)
#     AutoUpdateCheckPeriodMinutes = 0
#   HKLM\SOFTWARE\Policies\Microsoft\Edge
#     MetricsReportingEnabled = 0
#
# {F3017226-...}는 마이크로소프트가 공개한 WebView2 런타임의 EdgeUpdate 제품 GUID다
# (Microsoft Learn "Group Policy support for WebView2" 문서 기준, 2026-08 확인).
# Edge/WebView2 버전에 따라 정책 키가 바뀔 수 있으니, 적용 전 IT팀이 최신
# 마이크로소프트 공식 문서와 대조할 것 — 이 스크립트는 확인 시점 기준 최선이지
# 영구 보증이 아니다.
#
# 관리자 권한 PowerShell에서 실행해야 한다(HKLM 쓰기 필요).
#
# 사용:
#   .\harden_webview2.ps1 -Apply      적용
#   .\harden_webview2.ps1 -Revert     원복(값 삭제 — 정책 없음 상태로 되돌림)
#   .\harden_webview2.ps1 -Check      현재 상태만 출력(변경 없음)
#
# 적용 전후 확인 방법(회계사·IT팀이 직접 재현 가능해야 함):
#   1. 이 스크립트를 -Check로 실행해 정책값이 비어 있는지 확인
#   2. DSD_footing UI 셸을 실행: python ui/app.py <오버레이_PDF.pdf>
#   3. 별도 PowerShell 창에서: netstat -ano | findstr ":443"
#      → msedgewebview2.exe PID로 ESTABLISHED 줄이 있는지 확인(작업 관리자에서
#        PID→프로세스명 대조). 있으면 외부 접속이 발생한 것.
#   4. -Apply 실행 후 2~3을 반복해 접속이 사라졌는지 재확인

[CmdletBinding(DefaultParameterSetName = 'Check')]
param(
    [Parameter(ParameterSetName = 'Apply')]  [switch]$Apply,
    [Parameter(ParameterSetName = 'Revert')] [switch]$Revert,
    [Parameter(ParameterSetName = 'Check')]  [switch]$Check
)

$ErrorActionPreference = 'Stop'
$WV2_GUID = 'F3017226-FE2A-4295-8BDF-00C3A9A7E4C5'
$EdgeUpdateKey = 'HKLM:\SOFTWARE\Policies\Microsoft\EdgeUpdate'
$EdgeKey = 'HKLM:\SOFTWARE\Policies\Microsoft\Edge'

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Show-State {
    Write-Host "`n[현재 상태]" -ForegroundColor Cyan
    foreach ($item in @(
        @{ Path = $EdgeUpdateKey; Name = 'UpdateDefault' },
        @{ Path = $EdgeUpdateKey; Name = "Update{$WV2_GUID}" },
        @{ Path = $EdgeUpdateKey; Name = 'AutoUpdateCheckPeriodMinutes' },
        @{ Path = $EdgeKey;       Name = 'MetricsReportingEnabled' }
    )) {
        $v = Get-ItemProperty -Path $item.Path -Name $item.Name -ErrorAction SilentlyContinue
        $val = if ($v) { $v.($item.Name) } else { '(설정 없음 — 기본값)' }
        Write-Host ("  {0}\{1} = {2}" -f $item.Path, $item.Name, $val)
    }
}

if (-not (Test-Admin) -and ($Apply -or $Revert)) {
    Write-Host "[오류] 관리자 권한 PowerShell에서 실행하세요(HKLM 쓰기 필요)." -ForegroundColor Red
    exit 1
}

if ($Check -or (-not $Apply -and -not $Revert)) {
    Show-State
    Write-Host "`n변경 없음. 적용하려면 -Apply, 원복하려면 -Revert." -ForegroundColor Yellow
    exit 0
}

if ($Apply) {
    New-Item -Path $EdgeUpdateKey -Force | Out-Null
    New-Item -Path $EdgeKey -Force | Out-Null
    New-ItemProperty -Path $EdgeUpdateKey -Name 'UpdateDefault' -Value 0 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $EdgeUpdateKey -Name "Update{$WV2_GUID}" -Value 0 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $EdgeUpdateKey -Name 'AutoUpdateCheckPeriodMinutes' -Value 0 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $EdgeKey -Name 'MetricsReportingEnabled' -Value 0 -PropertyType DWord -Force | Out-Null
    Write-Host "[적용 완료]" -ForegroundColor Green
    Show-State
    Write-Host "`n확인: DSD_footing UI를 재실행하고 netstat -ano | findstr `":443`" 으로 WebView2 접속이 사라졌는지 확인하세요." -ForegroundColor Yellow
}

if ($Revert) {
    Remove-ItemProperty -Path $EdgeUpdateKey -Name 'UpdateDefault' -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path $EdgeUpdateKey -Name "Update{$WV2_GUID}" -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path $EdgeUpdateKey -Name 'AutoUpdateCheckPeriodMinutes' -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path $EdgeKey -Name 'MetricsReportingEnabled' -ErrorAction SilentlyContinue
    Write-Host "[원복 완료]" -ForegroundColor Green
    Show-State
}
