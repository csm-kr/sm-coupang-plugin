param(
    [string]$ProjectRoot = (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$outputRoot = Join-Path $ProjectRoot 'output'
$baseDir = Join-Path $outputRoot 'generated-pages'
$typeDir = Join-Path $outputRoot 'typography-pages-v2'
$imageDir = Join-Path $outputRoot 'images-v2'
$copyPath = Join-Path $outputRoot 'copy\typography-v2.json'
New-Item -ItemType Directory -Force -Path $typeDir, $imageDir | Out-Null
$pages = (Get-Content -LiteralPath $copyPath -Raw -Encoding UTF8 | ConvertFrom-Json).pages

$fontCollection = New-Object System.Drawing.Text.PrivateFontCollection
$fontCollection.AddFontFile('C:\Windows\Fonts\malgun.ttf')
$fontCollection.AddFontFile('C:\Windows\Fonts\malgunbd.ttf')
$fontFamily = $fontCollection.Families | Where-Object Name -eq 'Malgun Gothic' | Select-Object -First 1
if (-not $fontFamily) { throw 'Malgun Gothic was not loaded.' }

$navy = [System.Drawing.Color]::FromArgb(255, 11, 50, 107)
$gray = [System.Drawing.Color]::FromArgb(255, 78, 78, 78)
$blue = [System.Drawing.Color]::FromArgb(255, 78, 146, 203)
$badgeFill = [System.Drawing.Color]::FromArgb(235, 218, 240, 252)
$cardFill = [System.Drawing.Color]::FromArgb(226, 255, 252, 246)
$cardBorder = [System.Drawing.Color]::FromArgb(110, 255, 255, 255)

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

function New-FittingFont([System.Drawing.Graphics]$graphics, [string]$text, [float]$startSize, [float]$maxWidth, [System.Drawing.FontStyle]$style) {
    $size = $startSize
    while ($size -ge 18) {
        $font = New-Object System.Drawing.Font($fontFamily, $size, $style, [System.Drawing.GraphicsUnit]::Pixel)
        $measure = $graphics.MeasureString($text, $font, 4096, [System.Drawing.StringFormat]::GenericTypographic)
        if ($measure.Width -le $maxWidth) { return $font }
        $font.Dispose()
        $size -= 2
    }
    return New-Object System.Drawing.Font($fontFamily, 18, $style, [System.Drawing.GraphicsUnit]::Pixel)
}

function Draw-CenteredLine([System.Drawing.Graphics]$graphics, [string]$text, [float]$y, [float]$size, [float]$maxWidth, [System.Drawing.Brush]$brush, [System.Drawing.FontStyle]$style) {
    $font = New-FittingFont $graphics $text $size $maxWidth $style
    $format = New-Object System.Drawing.StringFormat
    try {
        $format.Alignment = [System.Drawing.StringAlignment]::Center
        $format.LineAlignment = [System.Drawing.StringAlignment]::Near
        $format.FormatFlags = [System.Drawing.StringFormatFlags]::NoClip
        $format.Trimming = [System.Drawing.StringTrimming]::None
        $rect = New-Object System.Drawing.RectangleF 52, $y, 920, ($font.Size + 28)
        $graphics.DrawString($text, $font, $brush, $rect, $format)
    }
    finally {
        $format.Dispose()
        $font.Dispose()
    }
}

function Draw-CenteredLines([System.Drawing.Graphics]$graphics, [object[]]$lines, [float]$y, [float]$size, [float]$lineHeight, [float]$maxWidth, [System.Drawing.Brush]$brush, [System.Drawing.FontStyle]$style) {
    for ($index = 0; $index -lt $lines.Count; $index++) {
        Draw-CenteredLine $graphics ([string]$lines[$index]) ($y + ($index * $lineHeight)) $size $maxWidth $brush $style
    }
}

function Draw-Badge([System.Drawing.Graphics]$graphics, [string]$text, [float]$y, [bool]$outline) {
    $font = New-FittingFont $graphics $text 27 380 ([System.Drawing.FontStyle]::Bold)
    $measure = $graphics.MeasureString($text, $font, 4096, [System.Drawing.StringFormat]::GenericTypographic)
    $width = [Math]::Max(190, [Math]::Ceiling($measure.Width + 70))
    $height = 56
    $x = (1024 - $width) / 2
    $path = New-RoundedPath $x $y $width $height 28
    try {
        if ($outline) {
            $fill = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(190, 255, 255, 255))
            $pen = New-Object System.Drawing.Pen($blue, 3)
            try { $graphics.FillPath($fill, $path); $graphics.DrawPath($pen, $path) }
            finally { $fill.Dispose(); $pen.Dispose() }
        }
        else {
            $fill = New-Object System.Drawing.SolidBrush($badgeFill)
            try { $graphics.FillPath($fill, $path) } finally { $fill.Dispose() }
        }
        $format = New-Object System.Drawing.StringFormat
        $brush = New-Object System.Drawing.SolidBrush($blue)
        try {
            $format.Alignment = [System.Drawing.StringAlignment]::Center
            $format.LineAlignment = [System.Drawing.StringAlignment]::Center
            $rect = New-Object System.Drawing.RectangleF $x, $y, $width, $height
            $graphics.DrawString($text, $font, $brush, $rect, $format)
        }
        finally { $format.Dispose(); $brush.Dispose() }
    }
    finally { $path.Dispose(); $font.Dispose() }
}

$titleBrush = New-Object System.Drawing.SolidBrush($navy)
$subBrush = New-Object System.Drawing.SolidBrush($gray)
try {
    foreach ($page in $pages) {
        $basePath = Join-Path $baseDir ('PG-{0:D2}.png' -f $page.page)
        $source = [System.Drawing.Image]::FromFile($basePath)
        try {
            $canvas = [System.Drawing.Bitmap]::new(1024, 1536, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
            $graphics = [System.Drawing.Graphics]::FromImage($canvas)
            try {
                $graphics.Clear([System.Drawing.Color]::White)
                $graphics.DrawImageUnscaled($source, 0, 0)
                $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
                $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

                if ($page.card) {
                    $card = New-RoundedPath $page.card[0] $page.card[1] $page.card[2] $page.card[3] 34
                    $cardBrush = New-Object System.Drawing.SolidBrush($cardFill)
                    $cardPen = New-Object System.Drawing.Pen($cardBorder, 2)
                    try { $graphics.FillPath($cardBrush, $card); $graphics.DrawPath($cardPen, $card) }
                    finally { $cardBrush.Dispose(); $cardPen.Dispose(); $card.Dispose() }
                }

                Draw-CenteredLines $graphics $page.head $page.head_y $page.head_size $page.line_height 900 $titleBrush ([System.Drawing.FontStyle]::Bold)
                $subLineHeight = if ($page.sub_line_height) { $page.sub_line_height } else { $page.sub_size + 10 }
                Draw-CenteredLines $graphics $page.sub $page.sub_y $page.sub_size $subLineHeight 890 $subBrush ([System.Drawing.FontStyle]::Regular)
                Draw-Badge $graphics $page.badge $page.badge_y ([bool]$page.outline)
            }
            finally { $graphics.Dispose() }
            $typePath = Join-Path $typeDir ('TY-{0:D2}-v2.png' -f $page.page)
            $canvas.Save($typePath, [System.Drawing.Imaging.ImageFormat]::Png)
            $canvas.Dispose()
        }
        finally { $source.Dispose() }
    }
}
finally { $titleBrush.Dispose(); $subBrush.Dispose(); $fontCollection.Dispose() }

for ($page = 1; $page -le 10; $page++) {
    $sourcePath = Join-Path $typeDir ('TY-{0:D2}-v2.png' -f $page)
    $source = [System.Drawing.Image]::FromFile($sourcePath)
    try {
        $resized = New-Object System.Drawing.Bitmap 780, 1170
        $graphics = [System.Drawing.Graphics]::FromImage($resized)
        try {
            $graphics.Clear([System.Drawing.Color]::White)
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
            $graphics.DrawImage($source, 0, 0, 780, 1170)
        }
        finally { $graphics.Dispose() }
        $resized.Save((Join-Path $imageDir ('{0:D2}-v2.png' -f $page)), [System.Drawing.Imaging.ImageFormat]::Png)
        $resized.Dispose()
    }
    finally { $source.Dispose() }
}

$contact = New-Object System.Drawing.Bitmap 780, 2925
$contactGraphics = [System.Drawing.Graphics]::FromImage($contact)
try {
    $contactGraphics.Clear([System.Drawing.Color]::White)
    $contactGraphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    for ($index = 0; $index -lt 10; $index++) {
        $page = $index + 1
        $image = [System.Drawing.Image]::FromFile((Join-Path $imageDir ('{0:D2}-v2.png' -f $page)))
        try {
            $x = ($index % 2) * 390
            $y = [Math]::Floor($index / 2) * 585
            $contactGraphics.DrawImage($image, $x, $y, 390, 585)
        }
        finally { $image.Dispose() }
    }
}
finally { $contactGraphics.Dispose() }
$contactPath = Join-Path $outputRoot 'contact-sheet-v2.png'
$contact.Save($contactPath, [System.Drawing.Imaging.ImageFormat]::Png)
$contact.Dispose()

$stitched = New-Object System.Drawing.Bitmap 780, 11700
$stitchedGraphics = [System.Drawing.Graphics]::FromImage($stitched)
try {
    $stitchedGraphics.Clear([System.Drawing.Color]::White)
    for ($page = 1; $page -le 10; $page++) {
        $image = [System.Drawing.Image]::FromFile((Join-Path $imageDir ('{0:D2}-v2.png' -f $page)))
        try { $stitchedGraphics.DrawImageUnscaled($image, 0, (($page - 1) * 1170)) }
        finally { $image.Dispose() }
    }
}
finally { $stitchedGraphics.Dispose() }
$codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object MimeType -eq 'image/jpeg'
$encoderParameters = New-Object System.Drawing.Imaging.EncoderParameters 1
$encoderParameters.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]92)
$stitchedPath = Join-Path $outputRoot 'project6-detail-page-complete-v2.jpg'
$stitched.Save($stitchedPath, $codec, $encoderParameters)
$encoderParameters.Dispose()
$stitched.Dispose()

Write-Host "[OK] rendered deterministic typography v2: $typeDir"
Write-Host "[OK] contact sheet: $contactPath"
Write-Host "[OK] stitched detail page: $stitchedPath"
