$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script:cpuPromptShown = $false
function global:nvidia-smi { $global:LASTEXITCODE = 1 }
function global:Read-Host {
    param([string]$Prompt)
    $script:cpuPromptShown = $true
    return "n"
}

try {
    . (Join-Path $repo "scripts\install.ps1") -Backend local -InstallRoot (Join-Path $env:TEMP "document-parser-gpu-prompt-must-not-create")
    throw "Installer should stop when CPU fallback is declined."
} catch {
    if ($_.Exception.Message -notmatch "已取消本机模式安装") { throw }
}

if (-not $script:cpuPromptShown) { throw "Installer did not ask before continuing without a GPU." }
Write-Output "GPU detection failure prompts before local runtime installation."
