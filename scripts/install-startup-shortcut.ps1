param(
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$shortcutName = "Jarvis for Omair.lnk"
$startupFolder = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupFolder $shortcutName

if ($Remove) {
    if (Test-Path $shortcutPath) {
        Remove-Item -LiteralPath $shortcutPath -Force
        Write-Output "Startup shortcut removed from $shortcutPath"
    }
    else {
        Write-Output "No startup shortcut was found."
    }
    exit 0
}

$targetPath = (Resolve-Path (Join-Path $PSScriptRoot "start-jarvis.bat")).Path
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,44"
$shortcut.Save()

Write-Output "Startup shortcut created at $shortcutPath"
