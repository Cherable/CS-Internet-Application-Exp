$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$remoteUrl = 'https://github.com/Cherable/CS-Internet-Application-Exp.git'
$expectedHead = '11a4c5aa696202eedd425ede6cc3fc231ec8b571'

function Invoke-GitChecked {
    param([string[]]$GitArguments)
    & git @GitArguments
    if ($LASTEXITCODE -ne 0) { throw "Git failed: $($GitArguments -join ' ')" }
}

# Work in a new checkout; preserve both the original workspace and remote history.
$checkout = Join-Path $projectRoot ('.runtime\publish-' + [guid]::NewGuid().ToString('N'))
Invoke-GitChecked -GitArguments @('clone', '--branch', 'main', '--single-branch', $remoteUrl, $checkout)
$actualHead = (& git -C $checkout rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $actualHead -ne $expectedHead) {
    throw 'Remote main has changed. Stop and compare remote edits before uploading; nothing was pushed.'
}

$topFiles = @('README.md', 'LICENSE', 'requirements.txt', 'manage.py', '.env.example', '.gitignore')
foreach ($name in $topFiles) {
    Copy-Item -LiteralPath (Join-Path $projectRoot $name) -Destination (Join-Path $checkout $name)
}
foreach ($folder in @('config', 'shop', 'templates', 'static', 'scripts', 'docs', '.github')) {
    $sourceFolder = Join-Path $projectRoot $folder
    foreach ($file in Get-ChildItem -LiteralPath $sourceFolder -File -Recurse) {
        $relative = $file.FullName.Substring($projectRoot.Length + 1)
        if ($relative -match '(^|\\)__pycache__(\\|$)' -or $file.Extension -in @('.pyc', '.sqlite3') -or $file.Name -eq '.env') { continue }
        $destination = Join-Path $checkout $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $destination
    }
}
Invoke-GitChecked -GitArguments @('-C', $checkout, 'add', '--all')
& git -C $checkout diff --cached --quiet
if ($LASTEXITCODE -eq 0) { Write-Host 'No changes to upload.'; exit 0 }
if ($LASTEXITCODE -ne 1) { throw 'Cannot inspect staged changes.' }
Invoke-GitChecked -GitArguments @('-C', $checkout, 'diff', '--cached', '--stat')
Invoke-GitChecked -GitArguments @('-C', $checkout, 'commit', '-m', 'feat: rebrand storefront to orangible with orange theme and evidence')
Invoke-GitChecked -GitArguments @('-C', $checkout, 'push', 'origin', 'main')
$newHead = (& git -C $checkout rev-parse HEAD).Trim()
$remoteLine = & git -C $checkout ls-remote origin refs/heads/main
if ($LASTEXITCODE -ne 0 -or ($remoteLine -split '\s+')[0] -ne $newHead) { throw 'Push verification failed.' }
$commitUrl = 'https://github.com/Cherable/CS-Internet-Application-Exp/commit/' + $newHead
$agentsFile = Join-Path $projectRoot 'AGENTS.md'
$agentsText = Get-Content -LiteralPath $agentsFile -Raw -Encoding utf8
$agentsText = $agentsText.Replace('状态：PENDING', '状态：DONE')
Set-Content -LiteralPath $agentsFile -Value ($agentsText + "`nVerified upload: $commitUrl`n") -Encoding utf8
Add-Content -LiteralPath (Join-Path $projectRoot 'docs\GITHUB_UPLOAD.md') -Value "`nVerified upload: $commitUrl`n" -Encoding utf8
Write-Host "Upload verified: $commitUrl"
