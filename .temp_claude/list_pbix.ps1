[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.IO.Compression.FileSystem

$pbixPath = Get-ChildItem -Path "D:\Project\Git管理\PBI-BgDesign" -Filter "*.pbix" | Select-Object -First 1 -ExpandProperty FullName
Write-Output "PBIX file: $pbixPath"
Write-Output "Size: $([math]::Round((Get-Item $pbixPath).Length / 1KB, 2)) KB"
Write-Output ""
Write-Output "=== ZIP Contents ==="

$zip = [System.IO.Compression.ZipFile]::OpenRead($pbixPath)
foreach ($entry in $zip.Entries) {
    Write-Output ("{0,-60} {1,12:N0}" -f $entry.FullName, $entry.Length)
}
$zip.Dispose()
