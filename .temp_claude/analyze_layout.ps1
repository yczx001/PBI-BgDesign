[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$layoutPath = "D:\Project\Git管理\PBI-BgDesign\.temp_claude\extracted\Layout.json"

# Read as UTF-16 (the format PBI uses)
$content = [System.IO.File]::ReadAllText($layoutPath, [System.Text.Encoding]::Unicode)

# Parse JSON
$layout = $content | ConvertFrom-Json

Write-Output "=== Report Info ==="
Write-Output "Report ID: $($layout.reportId)"
Write-Output "Theme: $($layout.theme)"
Write-Output ""

# Sections (Pages)
Write-Output "=== Pages (Sections): $($layout.sections.Count) ==="
foreach ($section in $layout.sections) {
    Write-Output ""
    Write-Output "--- Page: $($section.displayName) ---"
    Write-Output "  Name: $($section.name)"
    Write-Output "  Ordinal: $($section.ordinal)"

    # Display option / canvas size
    if ($section.displayOption) { Write-Output "  DisplayOption: $($section.displayOption)" }
    if ($section.width) { Write-Output "  Width: $($section.width)" }
    if ($section.height) { Write-Output "  Height: $($section.height)" }

    # Visual containers
    $vcCount = 0
    if ($section.visualContainers) { $vcCount = $section.visualContainers.Count }
    Write-Output "  Visual Containers: $vcCount"

    # Analyze each visual container
    $vcIndex = 0
    foreach ($vc in $section.visualContainers) {
        $vcIndex++
        $configStr = $vc.config
        try {
            $config = $configStr | ConvertFrom-Json
            $visualType = ""
            if ($config.singleVisual -and $config.singleVisual.visualType) {
                $visualType = $config.singleVisual.visualType
            }
            Write-Output "  [$vcIndex] Type=$visualType | x=$($vc.x) y=$($vc.y) w=$($vc.width) h=$($vc.height)"
        } catch {
            Write-Output "  [$vcIndex] (config parse error) x=$($vc.x) y=$($vc.y) w=$($vc.width) h=$($vc.height)"
        }
    }
}
