[CmdletBinding()]
param(
    [ValidateSet("local", "remote")]
    [string]$Backend = "local",
    [string]$RemoteUrl,
    [string]$RemoteToken,
    [string]$TorchIndexUrl,
    [string]$InstallRoot,
    [string]$OutputRoot,
    [string]$CodexConfigPath,
    [string]$WorkBuddyConfigPath,
    [string]$CodexSkillsRoot,
    [string]$WorkBuddySkillsRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-PrivateEndpoint([uri]$Endpoint) {
    if ($Endpoint.Scheme -notin @("http", "https") -or $Endpoint.UserInfo) {
        return $false
    }

    $hostName = $Endpoint.DnsSafeHost.TrimEnd(".").ToLowerInvariant()
    if ($hostName.EndsWith(".ts.net") -or $hostName -in @("localhost", "mineru-api")) {
        return $true
    }

    $address = $null
    if ([System.Net.IPAddress]::TryParse($hostName, [ref]$address)) {
        $bytes = $address.GetAddressBytes()
        if ($address.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork) {
            return (
                ($bytes[0] -eq 100 -and $bytes[1] -ge 64 -and $bytes[1] -le 127) -or
                $bytes[0] -eq 10 -or
                ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or
                ($bytes[0] -eq 192 -and $bytes[1] -eq 168)
            )
        }
        return $address.IsIPv6LinkLocal -or $address.IsIPv6SiteLocal -or $hostName.StartsWith("fd")
    }

    return $false
}

if ($Backend -eq "remote") {
    if (-not $RemoteUrl) {
        throw "remote 模式需要通过 -RemoteUrl 指定 MinerU API 地址。"
    }
    $endpoint = $null
    if (-not [uri]::TryCreate($RemoteUrl, [System.UriKind]::Absolute, [ref]$endpoint) -or -not (Test-PrivateEndpoint $endpoint)) {
        throw "远程 API 地址必须是 Tailscale 或其他私网地址（例如 http://100.x.y.z:8000 或 https://主机名.ts.net）。"
    }
}

$systemPython = Get-Command python -ErrorAction SilentlyContinue
if (-not $systemPython) {
    throw "未找到 Python。请先安装 Python 3.10 到 3.14，并确保 python 命令可用。"
}
$versionText = (& $systemPython.Source --version 2>&1 | Out-String).Trim()
if ($versionText -notmatch "^Python 3\.(10|11|12|13|14)\.") {
    throw "需要 Python 3.10 到 3.14（MinerU 4.0.7 的支持范围）；当前为：$versionText"
}

$cpuOnly = $false
if ($Backend -eq "local") {
    $nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    $gpuAvailable = $false
    if ($nvidiaSmi) {
        & $nvidiaSmi -L *> $null
        $gpuAvailable = ($LASTEXITCODE -eq 0)
    }
    if (-not $gpuAvailable) {
        $answer = Read-Host "未检测到可用的 NVIDIA GPU。MinerU 可使用 CPU（速度较慢），是否继续安装 CPU 版本？输入 y 继续"
        if ($answer -notmatch "^(y|yes)$") {
            throw "已取消本机模式安装。可改用 -Backend remote 连接自有云端 API。"
        }
        $cpuOnly = $true
    }
}

$profileRoot = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $HOME ".local\share" }
if (-not $InstallRoot) { $InstallRoot = Join-Path $profileRoot "DocumentParser\app" }
if (-not $OutputRoot) { $OutputRoot = Join-Path $profileRoot "DocumentParser\output" }
if (-not $CodexConfigPath) { $CodexConfigPath = Join-Path $HOME ".codex\config.toml" }
if (-not $WorkBuddyConfigPath) { $WorkBuddyConfigPath = Join-Path $HOME ".workbuddy\mcp.json" }
if (-not $CodexSkillsRoot) { $CodexSkillsRoot = Join-Path $HOME ".codex\skills" }
if (-not $WorkBuddySkillsRoot) { $WorkBuddySkillsRoot = Join-Path $HOME ".workbuddy\skills" }

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$venvRoot = Join-Path $InstallRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
Copy-Item (Join-Path $projectRoot "pyproject.toml") -Destination $InstallRoot -Force
Copy-Item (Join-Path $projectRoot "README.md") -Destination $InstallRoot -Force
Copy-Item (Join-Path $projectRoot "LICENSE") -Destination $InstallRoot -Force
$destinationPackage = Join-Path $InstallRoot "src\document_parser_mcp"
New-Item -ItemType Directory -Force -Path $destinationPackage | Out-Null
$sourcePackage = Join-Path $projectRoot "src\document_parser_mcp"
Get-ChildItem $sourcePackage -File -Filter "*.py" -Recurse | ForEach-Object {
    $relativePath = $_.FullName.Substring($sourcePackage.Length).TrimStart("\", "/")
    $destination = Join-Path $destinationPackage $relativePath
    New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
    Copy-Item $_.FullName -Destination $destination -Force
}

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not (Test-Path $venvPython)) {
    if ($uv) {
        & $uv.Source venv $venvRoot --python $systemPython.Source
    } else {
        & $systemPython.Source -m venv $venvRoot
    }
    if ($LASTEXITCODE -ne 0) { throw "创建隔离 Python 环境失败。" }
}

if ($uv) {
    & $uv.Source pip install --python $venvPython $InstallRoot
    if ($LASTEXITCODE -ne 0) { throw "安装文档解析 MCP 依赖失败。" }
    & $uv.Source pip install --python $venvPython --reinstall --no-deps $InstallRoot
} else {
    & $venvPython -m pip install $InstallRoot
    if ($LASTEXITCODE -ne 0) { throw "安装文档解析 MCP 依赖失败。" }
    & $venvPython -m pip install --force-reinstall --no-deps $InstallRoot
}
if ($LASTEXITCODE -ne 0) { throw "安装文档解析 MCP 失败。" }

if ($Backend -eq "local") {
    $vendorDirectory = Join-Path $InstallRoot 'vendor\mineru-4.0.7'
    New-Item -ItemType Directory -Force -Path $vendorDirectory | Out-Null
    $mineruWheelName = 'mineru-4.0.7-py3-none-any.whl'
    Copy-Item (Join-Path $projectRoot "vendor\mineru-4.0.7\$mineruWheelName") $vendorDirectory -Force
    $mineruWheel = Join-Path $vendorDirectory $mineruWheelName
    $mineruWheelUri = ([System.Uri]$mineruWheel).AbsoluteUri
    $mineruPackage = if ($cpuOnly) {
        "mineru @ $mineruWheelUri"
    } else {
        "mineru[full] @ $mineruWheelUri"
    }
    if ($uv) {
        & $uv.Source pip install --python $venvPython $mineruPackage
    } else {
        & $venvPython -m pip install $mineruPackage
    }
    if ($LASTEXITCODE -ne 0) { throw "安装随仓库提供的 MinerU 4.0.7 wheel 失败。" }

    if (-not $cpuOnly) {
        # MinerU's full extra can resolve the CPU wheel from PyPI and replace a
        # CUDA wheel. Install MinerU first, then reinstall the exact compatible
        # versions from one PyTorch index without dependency resolution.
        $torchVersion = (& $venvPython -c "import importlib.metadata as m; print(m.version('torch').split('+')[0])" 2>$null | Out-String).Trim()
        $torchvisionVersion = (& $venvPython -c "import importlib.metadata as m; print(m.version('torchvision').split('+')[0])" 2>$null | Out-String).Trim()
        if (-not $torchVersion -or -not $torchvisionVersion) {
            throw "MinerU 安装后未能读取 PyTorch 版本。"
        }

        $torchIndex = if ($TorchIndexUrl) { $TorchIndexUrl.TrimEnd("/") } else { "https://download.pytorch.org/whl/cu126" }
        if ($uv) {
            & $uv.Source pip install --python $venvPython --index-url $torchIndex --no-deps --reinstall "torch==$torchVersion" "torchvision==$torchvisionVersion"
        } else {
            & $venvPython -m pip install --index-url $torchIndex --no-deps --force-reinstall "torch==$torchVersion" "torchvision==$torchvisionVersion"
        }
        if ($LASTEXITCODE -ne 0) { throw "从 PyTorch 索引安装兼容版本失败：$torchIndex" }
    }
}

$envConfig = [ordered]@{
    DOCUMENT_PARSER_BACKEND = $Backend
    DOCUMENT_PARSER_OUTPUT_DIR = $OutputRoot
}
if ($Backend -eq "remote") {
    $envConfig["DOCUMENT_PARSER_REMOTE_URL"] = $RemoteUrl.TrimEnd("/")
    if ($RemoteToken) { $envConfig["DOCUMENT_PARSER_REMOTE_TOKEN"] = $RemoteToken }
}
$mcpArgsJson = ConvertTo-Json -InputObject ([string[]]@("-m", "document_parser_mcp.server")) -Compress
$mcpEnvJson = ConvertTo-Json -InputObject $envConfig -Compress
$configArgs = @(
    "-m", "document_parser_mcp.client_config",
    "--codex-config", $CodexConfigPath,
    "--workbuddy-config", $WorkBuddyConfigPath,
    "--server-name", "yushu-document-parser",
    "--command", $venvPython,
    "--args-json", $mcpArgsJson,
    "--env-json", $mcpEnvJson
)
& $venvPython @configArgs
if ($LASTEXITCODE -ne 0) { throw "合并 Codex 或 WorkBuddy MCP 配置失败。" }

foreach ($skillRoot in @($CodexSkillsRoot, $WorkBuddySkillsRoot)) {
    $skillDirectory = Join-Path $skillRoot "document-parser"
    New-Item -ItemType Directory -Force -Path $skillDirectory | Out-Null
    Copy-Item (Join-Path $projectRoot "SKILL.md") -Destination (Join-Path $skillDirectory "SKILL.md") -Force
}

Write-Host "安装完成。请重启 Codex 和 WorkBuddy 以加载 yushu-document-parser MCP 与 Skill。"
Write-Host "解析产物目录：$OutputRoot"
Write-Host "当前后端：$Backend"
if ($Backend -eq "local") {
    Write-Host "MinerU 4.0.7 已安装；模型会在首次解析时下载。"
} else {
    Write-Host "远程文件将发送到：$RemoteUrl"
}
