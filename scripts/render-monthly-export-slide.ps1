param(
    [Parameter(Mandatory = $true)][string]$SpecPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

function Get-FittedTitleLayout {
    param(
        [Parameter(Mandatory = $true)][System.Drawing.Graphics]$Graphics,
        [Parameter(Mandatory = $true)][System.Drawing.FontFamily]$FontFamily,
        [Parameter(Mandatory = $true)][string[]]$Words,
        [Parameter(Mandatory = $true)][float]$StartSize,
        [Parameter(Mandatory = $true)][float]$MinimumSize,
        [Parameter(Mandatory = $true)][float]$MaxWidth,
        [Parameter(Mandatory = $true)][float]$MaxHeight,
        [Parameter(Mandatory = $true)][int]$MaxLines,
        [Parameter(Mandatory = $true)][float]$LineHeightFactor
    )

    function Get-WrappedLines {
        param(
            [System.Drawing.Graphics]$Graphics,
            [System.Drawing.Font]$Font,
            [string[]]$Words,
            [float]$MaxWidth
        )

        $lines = New-Object System.Collections.Generic.List[string]
        $currentLine = ""
        foreach ($word in $Words) {
            if ([string]::IsNullOrWhiteSpace($word)) {
                continue
            }
            $candidate = if ([string]::IsNullOrWhiteSpace($currentLine)) { $word } else { "$currentLine $word" }
            $candidateWidth = $Graphics.MeasureString($candidate, $Font).Width
            if ($candidateWidth -le $MaxWidth -or [string]::IsNullOrWhiteSpace($currentLine)) {
                $currentLine = $candidate
                continue
            }
            $lines.Add($currentLine)
            $currentLine = $word
        }
        if ([string]::IsNullOrWhiteSpace($currentLine) -eq $false) {
            $lines.Add($currentLine)
        }
        return ,$lines.ToArray()
    }

    $size = [Math]::Max($StartSize, $MinimumSize)
    while ($size -ge $MinimumSize) {
        $font = New-Object System.Drawing.Font($FontFamily, $size, [System.Drawing.FontStyle]::Regular)
        $lines = Get-WrappedLines -Graphics $Graphics -Font $font -Words $Words -MaxWidth $MaxWidth
        if ($lines.Count -gt $MaxLines) {
            $font.Dispose()
            $size -= 1
            continue
        }
        $lineHeight = [Math]::Ceiling($size * $LineHeightFactor)
        $totalHeight = ($lineHeight * $lines.Count) + 12
        $widestLine = 0.0
        foreach ($line in $lines) {
            $measured = $Graphics.MeasureString([string]$line, $font)
            if ($measured.Width -gt $widestLine) {
                $widestLine = $measured.Width
            }
        }
        if ($widestLine -le $MaxWidth -and $totalHeight -le $MaxHeight) {
            return @{
                Font = $font
                LineHeight = $lineHeight
                Lines = $lines
            }
        }
        $font.Dispose()
        $size -= 1
    }

    $fallbackFont = New-Object System.Drawing.Font($FontFamily, $MinimumSize, [System.Drawing.FontStyle]::Regular)
    $fallbackLines = Get-WrappedLines -Graphics $Graphics -Font $fallbackFont -Words $Words -MaxWidth $MaxWidth
    return @{
        Font = $fallbackFont
        LineHeight = [Math]::Ceiling($MinimumSize * $LineHeightFactor)
        Lines = $fallbackLines
    }
}

$spec = Get-Content -LiteralPath $SpecPath -Raw | ConvertFrom-Json

$bitmap = New-Object System.Drawing.Bitmap([int]$spec.width, [int]$spec.height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

try {
    $background = [System.Drawing.ColorTranslator]::FromHtml("#f4eee6")
    $panelFill = [System.Drawing.ColorTranslator]::FromHtml([string]$spec.panelColor)
    $ink = [System.Drawing.ColorTranslator]::FromHtml([string]$spec.inkColor)
    $brand = [System.Drawing.ColorTranslator]::FromHtml([string]$spec.brandColor)
    $white = [System.Drawing.Color]::White

    $graphics.Clear($background)

    $outerBrush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml("#fffaf5"))
    $graphics.FillRectangle($outerBrush, 28, 28, ([int]$spec.width - 56), ([int]$spec.height - 56))
    $outerBrush.Dispose()

    $imagePath = [string]$spec.imagePath
    if ($imagePath -and (Test-Path -LiteralPath $imagePath)) {
        $eventImage = [System.Drawing.Image]::FromFile($imagePath)
        try {
            $destRect = New-Object System.Drawing.Rectangle(56, 56, [int]$spec.imageWidth, [int]$spec.imageHeight)
            $srcRatio = $eventImage.Width / $eventImage.Height
            $destRatio = $destRect.Width / $destRect.Height
            if ($srcRatio -gt $destRatio) {
                $srcHeight = $eventImage.Height
                $srcWidth = [int]($srcHeight * $destRatio)
                $srcX = [int](($eventImage.Width - $srcWidth) / 2)
                $srcY = 0
            } else {
                $srcWidth = $eventImage.Width
                $srcHeight = [int]($srcWidth / $destRatio)
                $srcX = 0
                $srcY = [int](($eventImage.Height - $srcHeight) / 2)
            }
            $srcRect = New-Object System.Drawing.Rectangle($srcX, $srcY, $srcWidth, $srcHeight)
            $graphics.DrawImage($eventImage, $destRect, $srcRect, [System.Drawing.GraphicsUnit]::Pixel)
        } finally {
            $eventImage.Dispose()
        }
    }

    $panelBrush = New-Object System.Drawing.SolidBrush($panelFill)
    $graphics.FillRectangle($panelBrush, [int]$spec.panelX, 56, [int]$spec.panelWidth, ([int]$spec.height - 112))
    $panelBrush.Dispose()

    $categoryFontCollection = New-Object System.Drawing.Text.PrivateFontCollection
    $categoryFontCollection.AddFontFile([string]$spec.categoryFontFile)
    $titleFontCollection = New-Object System.Drawing.Text.PrivateFontCollection
    $titleFontCollection.AddFontFile([string]$spec.titleFontFile)

    $categoryFamily = $categoryFontCollection.Families | Select-Object -First 1
    $titleFamily = $titleFontCollection.Families | Select-Object -First 1

    $categoryFont = New-Object System.Drawing.Font($categoryFamily, [float]$spec.categoryFontSize, [System.Drawing.FontStyle]::Regular)
    $titleWords = ([string]$spec.titleRaw) -split "\s+"
    $titleLayout = Get-FittedTitleLayout `
        -Graphics $graphics `
        -FontFamily $titleFamily `
        -Words $titleWords `
        -StartSize ([float]$spec.titleFontSize) `
        -MinimumSize ([float]$spec.titleMinFontSize) `
        -MaxWidth ([float]$spec.titleWidth) `
        -MaxHeight ([float]$spec.titleBoxHeight) `
        -MaxLines ([int]$spec.titleMaxLines) `
        -LineHeightFactor ([float]$spec.titleLineHeightFactor)
    $titleFont = $titleLayout.Font
    $metaFont = New-Object System.Drawing.Font([string]$spec.metaFontFamily, [float]$spec.metaFontSize, [System.Drawing.FontStyle]::Bold)
    $noteFont = New-Object System.Drawing.Font([string]$spec.noteFontFamily, [float]$spec.noteFontSize, [System.Drawing.FontStyle]::Regular)
    $qrPromptFont = New-Object System.Drawing.Font([string]$spec.metaFontFamily, [float]$spec.qrPromptFontSize, [System.Drawing.FontStyle]::Bold)

    $brandBrush = New-Object System.Drawing.SolidBrush($brand)
    $inkBrush = New-Object System.Drawing.SolidBrush($ink)
    $graphics.DrawString([string]$spec.category, $categoryFont, $brandBrush, [float]$spec.categoryX, [float]$spec.categoryY)

    $titleY = [float]$spec.titleY
    foreach ($titleLine in $titleLayout.Lines) {
        $graphics.DrawString([string]$titleLine, $titleFont, $inkBrush, [float]$spec.titleX, $titleY)
        $titleY += [float]$titleLayout.LineHeight
    }

    $graphics.DrawString([string]$spec.metaLine, $metaFont, $inkBrush, [float]$spec.metaX, [float]$spec.metaY)
    if ([string]::IsNullOrWhiteSpace([string]$spec.noteLine) -eq $false) {
        $noteBrush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml([string]$spec.noteColor))
        $graphics.DrawString([string]$spec.noteLine, $noteFont, $noteBrush, [float]$spec.noteX, [float]$spec.noteY)
        $noteBrush.Dispose()
    }

    $qrPromptBrush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml("#6b4d3c"))
    $graphics.DrawString([string]$spec.qrPrompt, $qrPromptFont, $qrPromptBrush, [float]$spec.qrX, [float]$spec.qrPromptY)
    $qrPromptBrush.Dispose()

    $qrContainerBrush = New-Object System.Drawing.SolidBrush($white)
    $graphics.FillRectangle(
        $qrContainerBrush,
        ([int]$spec.qrX - [int]$spec.qrContainerPadding),
        ([int]$spec.qrY - [int]$spec.qrContainerPadding),
        ([int]$spec.qrSize + ([int]$spec.qrContainerPadding * 2)),
        ([int]$spec.qrSize + ([int]$spec.qrContainerPadding * 2))
    )
    $qrContainerBrush.Dispose()

    $qrPath = [string]$spec.qrPath
    if ($qrPath -and (Test-Path -LiteralPath $qrPath)) {
        $qrImage = [System.Drawing.Image]::FromFile($qrPath)
        try {
            $graphics.DrawImage($qrImage, [int]$spec.qrX, [int]$spec.qrY, [int]$spec.qrSize, [int]$spec.qrSize)
        } finally {
            $qrImage.Dispose()
        }
    }

    $jpegCodec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq "image/jpeg" } | Select-Object -First 1
    $encoder = [System.Drawing.Imaging.Encoder]::Quality
    $encoderParams = New-Object System.Drawing.Imaging.EncoderParameters(1)
    $encoderParams.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter($encoder, [long]95)
    $bitmap.Save([string]$spec.outputPath, $jpegCodec, $encoderParams)
    $encoderParams.Dispose()

    $categoryFont.Dispose()
    $titleFont.Dispose()
    $metaFont.Dispose()
    $noteFont.Dispose()
    $qrPromptFont.Dispose()
    $categoryFontCollection.Dispose()
    $titleFontCollection.Dispose()
    $brandBrush.Dispose()
    $inkBrush.Dispose()
} finally {
    $graphics.Dispose()
    $bitmap.Dispose()
}
