param(
    [string]$ProjectRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$outputRoot = Join-Path $ProjectRoot 'output'
$baseDir = Join-Path $outputRoot 'generated-pages'
$pageDir = Join-Path $outputRoot 'images-v3'
$copyPath = Join-Path $outputRoot 'copy\typography-v2.json'
New-Item -ItemType Directory -Force -Path $pageDir | Out-Null
$pages = (Get-Content -LiteralPath $copyPath -Raw -Encoding UTF8 | ConvertFrom-Json).pages

$cropTop = @{
    1 = 300
    2 = 220
    3 = 120
    4 = 300
    5 = 220
    6 = 0
    7 = 260
    8 = 0
    9 = 220
    10 = 260
}

$fontCollection = New-Object System.Drawing.Text.PrivateFontCollection
$fontCollection.AddFontFile('C:\Windows\Fonts\NotoSansKR-VF.ttf')
$titleFamily = $fontCollection.Families | Where-Object Name -eq 'Noto Sans KR Black' | Select-Object -First 1
$mediumFamily = $fontCollection.Families | Where-Object Name -eq 'Noto Sans KR Medium' | Select-Object -First 1
$bodyFamily = $fontCollection.Families | Where-Object Name -eq 'Noto Sans KR' | Select-Object -First 1
if (-not $titleFamily -or -not $mediumFamily -or -not $bodyFamily) {
    throw 'Noto Sans KR font families were not loaded.'
}

$warmWhite = [System.Drawing.Color]::FromArgb(255, 250, 249, 246)
$visualBack = [System.Drawing.Color]::FromArgb(255, 243, 247, 250)
$navy = [System.Drawing.Color]::FromArgb(255, 12, 47, 96)
$gray = [System.Drawing.Color]::FromArgb(255, 83, 89, 96)
$blue = [System.Drawing.Color]::FromArgb(255, 94, 170, 220)
$paleBlue = [System.Drawing.Color]::FromArgb(255, 223, 241, 251)
$frame = [System.Drawing.Color]::FromArgb(255, 218, 229, 237)

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

function New-FittingFont(
    [System.Drawing.Graphics]$graphics,
    [System.Drawing.FontFamily]$family,
    [string]$text,
    [float]$startSize,
    [float]$maxWidth
) {
    $size = $startSize
    while ($size -ge 17) {
        $font = [System.Drawing.Font]::new($family, $size, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
        $measure = $graphics.MeasureString($text, $font, 4096, [System.Drawing.StringFormat]::GenericTypographic)
        if ($measure.Width -le $maxWidth) { return $font }
        $font.Dispose()
        $size -= 2
    }
    return [System.Drawing.Font]::new($family, 17, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
}

function Draw-CenteredLine(
    [System.Drawing.Graphics]$graphics,
    [System.Drawing.FontFamily]$family,
    [string]$text,
    [float]$y,
    [float]$size,
    [float]$maxWidth,
    [System.Drawing.Brush]$brush
) {
    $font = New-FittingFont $graphics $family $text $size $maxWidth
    $format = New-Object System.Drawing.StringFormat
    try {
        $format.Alignment = [System.Drawing.StringAlignment]::Center
        $format.LineAlignment = [System.Drawing.StringAlignment]::Near
        $format.FormatFlags = [System.Drawing.StringFormatFlags]::NoClip
        $rect = [System.Drawing.RectangleF]::new(40, $y, 700, ($font.Size + 20))
        $graphics.DrawString($text, $font, $brush, $rect, $format)
    }
    finally {
        $format.Dispose()
        $font.Dispose()
    }
}

function Draw-Badge([System.Drawing.Graphics]$graphics, [string]$text) {
    $font = New-FittingFont $graphics $mediumFamily $text 19 270
    $measure = $graphics.MeasureString($text, $font, 4096, [System.Drawing.StringFormat]::GenericTypographic)
    $width = [Math]::Max(150, [Math]::Ceiling($measure.Width + 44))
    $height = 40
    $x = (780 - $width) / 2
    $path = New-RoundedPath $x 23 $width $height 20
    $fill = New-Object System.Drawing.SolidBrush($paleBlue)
    $textBrush = New-Object System.Drawing.SolidBrush($blue)
    $format = New-Object System.Drawing.StringFormat
    try {
        $graphics.FillPath($fill, $path)
        $format.Alignment = [System.Drawing.StringAlignment]::Center
        $format.LineAlignment = [System.Drawing.StringAlignment]::Center
        $rect = [System.Drawing.RectangleF]::new($x, 23, $width, $height)
        $graphics.DrawString($text, $font, $textBrush, $rect, $format)
    }
    finally {
        $path.Dispose()
        $fill.Dispose()
        $textBrush.Dispose()
        $format.Dispose()
        $font.Dispose()
    }
}

$headerHeight = 320
$visualX = 24
$visualWidth = 732
$visualGap = 12
$bottomPad = 24
$titleBrush = New-Object System.Drawing.SolidBrush($navy)
$subBrush = New-Object System.Drawing.SolidBrush($gray)
$framePen = New-Object System.Drawing.Pen($frame, 2)
$accentBrush = New-Object System.Drawing.SolidBrush($blue)
$warmBrush = New-Object System.Drawing.SolidBrush($warmWhite)
$visualBrush = New-Object System.Drawing.SolidBrush($visualBack)
$rendered = @()

try {
    foreach ($page in $pages) {
        $number = [int]$page.page
        $top = [int]$cropTop[$number]
        $sourcePath = Join-Path $baseDir ('PG-{0:D2}.png' -f $number)
        $source = [System.Drawing.Image]::FromFile($sourcePath)
        try {
            $sourceHeight = $source.Height - $top
            $visualHeight = [Math]::Ceiling($sourceHeight * ($visualWidth / [double]$source.Width))
            $pageHeight = $headerHeight + $visualGap + $visualHeight + $bottomPad
            $canvas = [System.Drawing.Bitmap]::new(780, $pageHeight, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
            $graphics = [System.Drawing.Graphics]::FromImage($canvas)
            try {
                $graphics.Clear($warmWhite)
                $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
                $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
                $graphics.FillRectangle($accentBrush, 0, 0, 780, 7)
                Draw-Badge $graphics ([string]$page.badge)

                $headLines = @($page.head)
                $subLines = @($page.sub)
                if ($headLines.Count -eq 1) {
                    $titleY = 91
                    $titleSize = 52
                    $subY = 183
                }
                else {
                    $titleY = 72
                    $titleSize = 55
                    $subY = 216
                }
                if ($subLines.Count -gt 1) { $subY = 208 }

                for ($index = 0; $index -lt $headLines.Count; $index++) {
                    Draw-CenteredLine $graphics $titleFamily ([string]$headLines[$index]) ($titleY + ($index * 62)) $titleSize 700 $titleBrush
                }
                for ($index = 0; $index -lt $subLines.Count; $index++) {
                    Draw-CenteredLine $graphics $bodyFamily ([string]$subLines[$index]) ($subY + ($index * 34)) 24 700 $subBrush
                }

                $graphics.DrawLine($framePen, 42, ($headerHeight - 1), 738, ($headerHeight - 1))
                $imageY = $headerHeight + $visualGap
                $graphics.FillRectangle($visualBrush, 0, $headerHeight, 780, ($pageHeight - $headerHeight))
                $sourceRect = [System.Drawing.Rectangle]::new(0, $top, $source.Width, $sourceHeight)
                $destinationRect = [System.Drawing.Rectangle]::new($visualX, $imageY, $visualWidth, $visualHeight)
                $graphics.DrawImage($source, $destinationRect, $sourceRect, [System.Drawing.GraphicsUnit]::Pixel)
                $graphics.DrawRectangle($framePen, $visualX, $imageY, ($visualWidth - 1), ($visualHeight - 1))
            }
            finally { $graphics.Dispose() }

            $pagePath = Join-Path $pageDir ('{0:D2}-v3.png' -f $number)
            $canvas.Save($pagePath, [System.Drawing.Imaging.ImageFormat]::Png)
            $canvas.Dispose()
            $rendered += [pscustomobject]@{ Number = $number; Path = $pagePath; Height = $pageHeight }
        }
        finally { $source.Dispose() }
    }
}
finally {
    $titleBrush.Dispose()
    $subBrush.Dispose()
    $framePen.Dispose()
    $accentBrush.Dispose()
    $warmBrush.Dispose()
    $visualBrush.Dispose()
    $fontCollection.Dispose()
}

$totalHeight = ($rendered | Measure-Object -Property Height -Sum).Sum
$stitched = [System.Drawing.Bitmap]::new(780, $totalHeight, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$stitchedGraphics = [System.Drawing.Graphics]::FromImage($stitched)
try {
    $stitchedGraphics.Clear($warmWhite)
    $offsetY = 0
    foreach ($item in ($rendered | Sort-Object Number)) {
        $image = [System.Drawing.Image]::FromFile($item.Path)
        try { $stitchedGraphics.DrawImageUnscaled($image, 0, $offsetY) }
        finally { $image.Dispose() }
        $offsetY += $item.Height
    }
}
finally { $stitchedGraphics.Dispose() }

$codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object MimeType -eq 'image/jpeg'
$encoderParameters = New-Object System.Drawing.Imaging.EncoderParameters 1
$encoderParameters.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]93)
$stitchedPath = Join-Path $outputRoot 'project6-detail-page-complete-v3.jpg'
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
    foreach ($item in ($rendered | Sort-Object Number)) {
        $index = $item.Number - 1
        $image = [System.Drawing.Image]::FromFile($item.Path)
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
            $y = $cellY + 15
            $contactGraphics.DrawImage($image, $x, $y, $targetWidth, $targetHeight)
        }
        finally { $image.Dispose() }
    }
}
finally { $contactGraphics.Dispose() }
$contactPath = Join-Path $outputRoot 'contact-sheet-v3.png'
$contact.Save($contactPath, [System.Drawing.Imaging.ImageFormat]::Png)
$contact.Dispose()

$manifest = [ordered]@{
    version = '3.0'
    layout = 'separate_header_and_contained_visual'
    source = 'output/generated-pages/PG-01..PG-10.png'
    width = 780
    total_height = $totalHeight
    pages = @($rendered | Sort-Object Number | ForEach-Object {
        [ordered]@{
            page = ('{0:D2}' -f $_.Number)
            file = ('output/images-v3/{0:D2}-v3.png' -f $_.Number)
            width = 780
            height = $_.Height
            source_crop = [ordered]@{ left = 0; top = $cropTop[$_.Number]; right = 0; bottom = 0 }
            visual_padding = 24
            typography_overlap = $false
        }
    })
}
$manifestPath = Join-Path $pageDir 'manifest.json'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

Write-Host "[OK] safe-layout v3 pages: $pageDir"
Write-Host "[OK] contact sheet: $contactPath"
Write-Host "[OK] stitched detail page: $stitchedPath"
Write-Host "[OK] total height: $totalHeight"
