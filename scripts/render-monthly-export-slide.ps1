param(
    [Parameter(Mandatory = $true)][string]$SpecPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

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

    $categoryFont = New-Object System.Drawing.Font("Arial", 22, [System.Drawing.FontStyle]::Bold)
    $titleFont = New-Object System.Drawing.Font("Georgia", 32, [System.Drawing.FontStyle]::Bold)
    $metaFont = New-Object System.Drawing.Font("Arial", 34, [System.Drawing.FontStyle]::Bold)
    $noteFont = New-Object System.Drawing.Font("Arial", 22, [System.Drawing.FontStyle]::Regular)

    $brandBrush = New-Object System.Drawing.SolidBrush($brand)
    $inkBrush = New-Object System.Drawing.SolidBrush($ink)
    $graphics.DrawString([string]$spec.category, $categoryFont, $brandBrush, [float]$spec.categoryX, [float]$spec.categoryY)

    $titleRect = New-Object System.Drawing.RectangleF([float]$spec.titleX, [float]$spec.titleY, [float]$spec.titleWidth, 220.0)
    $titleFormat = New-Object System.Drawing.StringFormat
    $titleFormat.Trimming = [System.Drawing.StringTrimming]::EllipsisWord
    $graphics.DrawString([string]$spec.title, $titleFont, $inkBrush, $titleRect, $titleFormat)

    $graphics.DrawString([string]$spec.metaLine, $metaFont, $inkBrush, [float]$spec.metaX, [float]$spec.metaY)
    if ([string]::IsNullOrWhiteSpace([string]$spec.noteLine) -eq $false) {
        $noteBrush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml("#43514b"))
        $graphics.DrawString([string]$spec.noteLine, $noteFont, $noteBrush, [float]$spec.noteX, [float]$spec.noteY)
        $noteBrush.Dispose()
    }

    $qrContainerBrush = New-Object System.Drawing.SolidBrush($white)
    $graphics.FillRectangle($qrContainerBrush, ([int]$spec.qrX - 16), ([int]$spec.qrY - 16), ([int]$spec.qrSize + 32), ([int]$spec.qrSize + 32))
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
    $brandBrush.Dispose()
    $inkBrush.Dispose()
    $titleFormat.Dispose()
} finally {
    $graphics.Dispose()
    $bitmap.Dispose()
}
