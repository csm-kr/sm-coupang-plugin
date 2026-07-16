param(
    [string]$ProjectRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$outputRoot = Join-Path $ProjectRoot 'output'
$sourceDir = Join-Path $outputRoot 'images-v3'
$targetDir = Join-Path $outputRoot 'images-v4'
$copyPath = Join-Path $outputRoot 'copy\page09-v4.json'
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
$cards = (Get-Content -LiteralPath $copyPath -Raw -Encoding UTF8 | ConvertFrom-Json).cards

$fontCollection = New-Object System.Drawing.Text.PrivateFontCollection
$fontCollection.AddFontFile('C:\Windows\Fonts\NotoSansKR-VF.ttf')
$titleFamily = $fontCollection.Families | Where-Object Name -eq 'Noto Sans KR Medium' | Select-Object -First 1
$bodyFamily = $fontCollection.Families | Where-Object Name -eq 'Noto Sans KR' | Select-Object -First 1
if (-not $titleFamily -or -not $bodyFamily) { throw 'Noto Sans KR was not loaded.' }

$navy = [System.Drawing.Color]::FromArgb(255, 12, 47, 96)
$gray = [System.Drawing.Color]::FromArgb(255, 84, 91, 99)
$blue = [System.Drawing.Color]::FromArgb(255, 94, 170, 220)
$paleBlue = [System.Drawing.Color]::FromArgb(255, 230, 244, 252)
$white = [System.Drawing.Color]::White

function New-RoundedPath([float]$x, [float]$y, [float]$width, [float]$height, [float]$radius) {
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $diameter = $radius * 2
    $path.AddArc($x, $y, $diameter, $diameter, 180, 90)
    $path.AddArc($x + $width - $diameter, $y, $diameter, $diameter, 270, 90)
    $path.AddArc($x + $width - $diameter, $y + $height - $diameter, $diameter, $diameter, 0, 90)
    $path.AddArc($x, $y + $height - $diameter, $diameter, $diameter, 90, 90)
    $path.CloseFigure()
    return $path
}

function New-FittingFont([System.Drawing.Graphics]$graphics, [System.Drawing.FontFamily]$family, [string]$text, [float]$startSize, [float]$maxWidth) {
    $size = $startSize
    while ($size -ge 15) {
        $font = [System.Drawing.Font]::new($family, $size, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
        $measure = $graphics.MeasureString($text, $font, 4096, [System.Drawing.StringFormat]::GenericTypographic)
        if ($measure.Width -le $maxWidth) { return $font }
        $font.Dispose()
        $size -= 1
    }
    return [System.Drawing.Font]::new($family, 15, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
}

function Draw-LeftText([System.Drawing.Graphics]$graphics, [System.Drawing.FontFamily]$family, [string]$text, [float]$x, [float]$y, [float]$size, [float]$maxWidth, [System.Drawing.Brush]$brush) {
    $font = New-FittingFont $graphics $family $text $size $maxWidth
    $format = New-Object System.Drawing.StringFormat
    try {
        $format.Alignment = [System.Drawing.StringAlignment]::Near
        $format.LineAlignment = [System.Drawing.StringAlignment]::Near
        $format.FormatFlags = [System.Drawing.StringFormatFlags]::NoClip
        $rect = [System.Drawing.RectangleF]::new($x, $y, $maxWidth, ($font.Size + 16))
        $graphics.DrawString($text, $font, $brush, $rect, $format)
    }
    finally { $format.Dispose(); $font.Dispose() }
}

for ($page = 1; $page -le 10; $page++) {
    if ($page -eq 9) { continue }
    $source = Join-Path $sourceDir ('{0:D2}-v3.png' -f $page)
    $target = Join-Path $targetDir ('{0:D2}-v4.png' -f $page)
    Copy-Item -LiteralPath $source -Destination $target -Force
}

$page09Source = Join-Path $sourceDir '09-v3.png'
$sourceImage = [System.Drawing.Image]::FromFile($page09Source)
try {
    $canvas = [System.Drawing.Bitmap]::new($sourceImage.Width, $sourceImage.Height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)
    $titleBrush = New-Object System.Drawing.SolidBrush($navy)
    $subBrush = New-Object System.Drawing.SolidBrush($gray)
    $labelFill = New-Object System.Drawing.SolidBrush($blue)
    $labelText = New-Object System.Drawing.SolidBrush($white)
    $accentFill = New-Object System.Drawing.SolidBrush($paleBlue)
    try {
        $graphics.DrawImageUnscaled($sourceImage, 0, 0)
        $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

        foreach ($card in $cards) {
            $top = [float]$card.top
            $bottom = [float]$card.bottom
            $height = $bottom - $top + 1
            $centerY = $top + ($height / 2)
            $labelWidth = 76
            $labelHeight = 42
            $labelX = 67
            $labelY = $centerY - ($labelHeight / 2)
            $labelPath = New-RoundedPath $labelX $labelY $labelWidth $labelHeight 21
            try { $graphics.FillPath($labelFill, $labelPath) }
            finally { $labelPath.Dispose() }

            $labelFont = New-FittingFont $graphics $titleFamily ([string]$card.label) 16 58
            $labelFormat = New-Object System.Drawing.StringFormat
            try {
                $labelFormat.Alignment = [System.Drawing.StringAlignment]::Center
                $labelFormat.LineAlignment = [System.Drawing.StringAlignment]::Center
                $labelRect = [System.Drawing.RectangleF]::new($labelX, $labelY, $labelWidth, $labelHeight)
                $graphics.DrawString([string]$card.label, $labelFont, $labelText, $labelRect, $labelFormat)
            }
            finally { $labelFormat.Dispose(); $labelFont.Dispose() }

            $graphics.FillRectangle($accentFill, 165, ($top + 31), 38, 5)
            Draw-LeftText $graphics $titleFamily ([string]$card.title) 165 ($top + 42) 30 520 $titleBrush
            Draw-LeftText $graphics $bodyFamily ([string]$card.subcopy) 165 ($top + 91) 21 520 $subBrush
        }
    }
    finally {
        $graphics.Dispose()
        $titleBrush.Dispose()
        $subBrush.Dispose()
        $labelFill.Dispose()
        $labelText.Dispose()
        $accentFill.Dispose()
    }
    $page09Target = Join-Path $targetDir '09-v4.png'
    $canvas.Save($page09Target, [System.Drawing.Imaging.ImageFormat]::Png)
    $canvas.Dispose()
}
finally { $sourceImage.Dispose(); $fontCollection.Dispose() }

$pageFiles = 1..10 | ForEach-Object { Join-Path $targetDir ('{0:D2}-v4.png' -f $_) }
$heights = @()
foreach ($file in $pageFiles) {
    $image = [System.Drawing.Image]::FromFile($file)
    try { $heights += $image.Height }
    finally { $image.Dispose() }
}
$totalHeight = ($heights | Measure-Object -Sum).Sum
$stitched = [System.Drawing.Bitmap]::new(780, $totalHeight, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$stitchedGraphics = [System.Drawing.Graphics]::FromImage($stitched)
try {
    $stitchedGraphics.Clear([System.Drawing.Color]::White)
    $offsetY = 0
    for ($index = 0; $index -lt $pageFiles.Count; $index++) {
        $image = [System.Drawing.Image]::FromFile($pageFiles[$index])
        try { $stitchedGraphics.DrawImageUnscaled($image, 0, $offsetY) }
        finally { $image.Dispose() }
        $offsetY += $heights[$index]
    }
}
finally { $stitchedGraphics.Dispose() }

$codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object MimeType -eq 'image/jpeg'
$encoderParameters = New-Object System.Drawing.Imaging.EncoderParameters 1
$encoderParameters.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]93)
$stitchedPath = Join-Path $outputRoot 'project6-detail-page-complete-v4.jpg'
$stitched.Save($stitchedPath, $codec, $encoderParameters)
$encoderParameters.Dispose()
$stitched.Dispose()

$cellWidth = 390
$cellHeight = 720
$contact = [System.Drawing.Bitmap]::new(780, ($cellHeight * 5), [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$contactGraphics = [System.Drawing.Graphics]::FromImage($contact)
try {
    $contactGraphics.Clear([System.Drawing.Color]::White)
    $contactGraphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    for ($index = 0; $index -lt $pageFiles.Count; $index++) {
        $image = [System.Drawing.Image]::FromFile($pageFiles[$index])
        try {
            $targetWidth = 360
            $targetHeight = [Math]::Round($image.Height * ($targetWidth / [double]$image.Width))
            if ($targetHeight -gt 690) {
                $targetHeight = 690
                $targetWidth = [Math]::Round($image.Width * ($targetHeight / [double]$image.Height))
            }
            $cellX = ($index % 2) * $cellWidth
            $cellY = [Math]::Floor($index / 2) * $cellHeight
            $x = $cellX + (($cellWidth - $targetWidth) / 2)
            $contactGraphics.DrawImage($image, $x, ($cellY + 15), $targetWidth, $targetHeight)
        }
        finally { $image.Dispose() }
    }
}
finally { $contactGraphics.Dispose() }
$contactPath = Join-Path $outputRoot 'contact-sheet-v4.png'
$contact.Save($contactPath, [System.Drawing.Imaging.ImageFormat]::Png)
$contact.Dispose()

Write-Host "[OK] completed page 09: $(Join-Path $targetDir '09-v4.png')"
Write-Host "[OK] rebuilt stitched detail page: $stitchedPath"
Write-Host "[OK] rebuilt contact sheet: $contactPath"
