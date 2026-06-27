[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.IO.Compression.FileSystem

$pbixPath = Get-ChildItem -Path "D:\Project\Git管理\PBI-BgDesign" -Filter "*.pbix" | Select-Object -First 1 -ExpandProperty FullName
$extractDir = "D:\Project\Git管理\PBI-BgDesign\.temp_claude\extracted"

if (Test-Path $extractDir) { Remove-Item -Recurse -Force $extractDir }
New-Item -ItemType Directory -Path $extractDir -Force | Out-Null

$zip = [System.IO.Compression.ZipFile]::OpenRead($pbixPath)

# Extract Report/Layout
$layoutEntry = $zip.Entries | Where-Object { $_.FullName -eq "Report/Layout" }
if ($layoutEntry) {
    $destPath = Join-Path $extractDir "Layout.json"
    [System.IO.Compression.ZipFileExtensions]::ExtractToFile($layoutEntry, $destPath, $true)
    Write-Output "Extracted Report/Layout -> Layout.json"
    $fileSize = (Get-Item $destPath).Length
    Write-Output "Size: $fileSize bytes"
}

# Extract StaticResources
$staticEntries = $zip.Entries | Where-Object { $_.FullName -like "Report/StaticResources/*" }
foreach ($entry in $staticEntries) {
    $relativePath = $entry.FullName -replace "^Report/StaticResources/", ""
    $destPath = Join-Path $extractDir "StaticResources\$relativePath"
    $destDir = Split-Path $destPath -Parent
    if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destPath, $true)
    Write-Output "Extracted: $($entry.FullName)"
}

$zip.Dispose()

# Now read the first 5000 chars of Layout.json to understand structure
Write-Output ""
Write-Output "=== Layout.json First 5000 chars ==="
$content = Get-Content -Path (Join-Path $extractDir "Layout.json") -Raw -Encoding UTF8
Write-Output $content.Substring(0, [Math]::Min(5000, $content.Length))
