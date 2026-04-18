param(
    [int]$Port = 8080,
    [int]$RefreshMinutes = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:PublicRoot = Join-Path $script:ProjectRoot "public"
$script:LogPath = Join-Path $script:ProjectRoot "server.log"
$script:CacheRoot = Join-Path $script:ProjectRoot "cache"
$script:ImageCacheRoot = Join-Path $script:CacheRoot "images"
$script:QrCacheRoot = Join-Path $script:CacheRoot "qr"
$script:SourceUrl = "https://www.sunderlandculture.org.uk/arts-centre-washington/whats-on/"
$script:ClassCategories = @(
    "Adult Workshops and Activities",
    "Children and Young People's Activities"
)
$script:EventCache = @{
    GeneratedAt = [datetime]::MinValue
    Items = @()
    LastError = $null
}
$script:EventPageDetailCache = @{}

function Write-Log {
    param([string]$Message)

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[{0}] {1}" -f $timestamp, $Message
    Add-Content -LiteralPath $script:LogPath -Value $line
}

function Ensure-Directory {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        $null = New-Item -ItemType Directory -Path $Path -Force
    }
}

function Get-Sha1Hex {
    param([string]$Value)

    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
        $hash = $sha1.ComputeHash($bytes)
        return ([System.BitConverter]::ToString($hash)).Replace("-", "").ToLowerInvariant()
    } finally {
        $sha1.Dispose()
    }
}

function Get-ImageCacheFilePath {
    param([string]$Url)

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return $null
    }

    Ensure-Directory $script:ImageCacheRoot

    $uri = [uri]$Url
    $extension = [System.IO.Path]::GetExtension($uri.AbsolutePath)
    if ([string]::IsNullOrWhiteSpace($extension)) {
        $extension = ".img"
    }

    $fileName = "{0}{1}" -f (Get-Sha1Hex $Url), $extension.ToLowerInvariant()
    return Join-Path $script:ImageCacheRoot $fileName
}

function Save-ImageToCache {
    param([string]$Url)

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return $null
    }

    try {
        $targetPath = Get-ImageCacheFilePath $Url
        if (Test-Path -LiteralPath $targetPath -PathType Leaf) {
            return $targetPath
        }

        Write-Log ("Caching image {0}" -f $Url)
        Invoke-WebRequest -Uri $Url -OutFile $targetPath -UseBasicParsing -Headers @{
            "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            "Referer" = $script:SourceUrl
        }
        return $targetPath
    } catch {
        Write-Log ("Image cache failed for {0}: {1}" -f $Url, $_.Exception.Message)
        return $null
    }
}

function Get-LocalImageUrl {
    param([string]$Url)

    $cachedPath = Save-ImageToCache $Url
    if ([string]::IsNullOrWhiteSpace($cachedPath)) {
        return $null
    }

    return "/cache/images/{0}" -f [System.IO.Path]::GetFileName($cachedPath)
}

function Get-QrCacheFilePath {
    param([string]$Url)

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return $null
    }

    Ensure-Directory $script:QrCacheRoot

    $fileName = "{0}.png" -f (Get-Sha1Hex $Url)
    return Join-Path $script:QrCacheRoot $fileName
}

function Save-QrToCache {
    param([string]$Url)

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return $null
    }

    try {
        $targetPath = Get-QrCacheFilePath $Url
        if (Test-Path -LiteralPath $targetPath -PathType Leaf) {
            return $targetPath
        }

        $providers = @(
            ("https://api.qrserver.com/v1/create-qr-code/?size=220x220&margin=0&data={0}" -f [System.Uri]::EscapeDataString($Url)),
            ("https://quickchart.io/qr?size=220&margin=0&text={0}" -f [System.Uri]::EscapeDataString($Url))
        )

        foreach ($providerUrl in $providers) {
            try {
                Write-Log ("Caching QR {0} via {1}" -f $Url, $providerUrl)
                Invoke-WebRequest -Uri $providerUrl -OutFile $targetPath -UseBasicParsing -Headers @{
                    "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
                    "Referer" = $script:SourceUrl
                }
                if (Test-Path -LiteralPath $targetPath -PathType Leaf) {
                    return $targetPath
                }
            } catch {
                if (Test-Path -LiteralPath $targetPath -PathType Leaf) {
                    Remove-Item -LiteralPath $targetPath -Force -ErrorAction SilentlyContinue
                }
            }
        }

        return $null
    } catch {
        Write-Log ("QR cache failed for {0}: {1}" -f $Url, $_.Exception.Message)
        return $null
    }
}

function Get-LocalQrUrl {
    param([string]$Url)

    $cachedPath = Save-QrToCache $Url
    if ([string]::IsNullOrWhiteSpace($cachedPath)) {
        return $null
    }

    return "/cache/qr/{0}" -f [System.IO.Path]::GetFileName($cachedPath)
}

function Convert-HtmlEntities {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ""
    }

    return [System.Net.WebUtility]::HtmlDecode($Value)
}

function Convert-ToPlainText {
    param([string]$Html)

    if ([string]::IsNullOrWhiteSpace($Html)) {
        return ""
    }

    $text = $Html -replace "(?is)<script.*?</script>", " "
    $text = $text -replace "(?is)<style.*?</style>", " "
    $text = $text -replace "(?i)<br\s*/?>", "`n"
    $text = $text -replace "(?i)</(p|div|section|article|li|h1|h2|h3|h4|h5|h6)>", "`n"
    $text = $text -replace "(?is)<.*?>", " "
    $text = Convert-HtmlEntities $text
    $text = $text -replace "[\r\t]", " "
    $text = $text -replace "\u00A0", " "
    $text = $text -replace " +", " "
    $text = $text -replace " *`n *", "`n"
    return $text.Trim()
}

function Normalize-Whitespace {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ""
    }

    $text = Convert-HtmlEntities $Value
    $text = $text.Replace([string][char]0x2019, "'")
    $text = $text.Replace([string][char]0x2018, "'")
    $text = $text.Replace("Â£", [string][char]0x00A3)
    return ($text -replace "\s+", " ").Trim()
}

function Normalize-CategoryName {
    param([string]$Value)

    $normalized = Normalize-Whitespace $Value
    $normalized = $normalized.Replace("&", "and")
    $normalized = $normalized -replace "\s+", " "
    return $normalized.Trim()
}

function Get-AbsoluteUrl {
    param([string]$Url)

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return $null
    }

    if ($Url.StartsWith("http://") -or $Url.StartsWith("https://")) {
        return $Url
    }

    return ([uri]::new([uri]$script:SourceUrl, $Url)).AbsoluteUri
}

function Parse-QueryString {
    param([string]$Query)

    $result = @{}
    if ([string]::IsNullOrWhiteSpace($Query)) {
        return $result
    }

    $trimmed = $Query.TrimStart("?")
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        return $result
    }

    foreach ($pair in $trimmed.Split("&", [System.StringSplitOptions]::RemoveEmptyEntries)) {
        $parts = $pair.Split("=", 2)
        $key = [System.Uri]::UnescapeDataString($parts[0])
        $value = if ($parts.Count -gt 1) { [System.Uri]::UnescapeDataString($parts[1]) } else { "" }
        $result[$key] = $value
    }

    return $result
}

function Get-DateSortKey {
    param([string]$DateText)

    if ([string]::IsNullOrWhiteSpace($DateText)) {
        return [datetime]::MaxValue
    }

    $formats = @(
        "dd MMM yyyy",
        "d MMM yyyy",
        "dd MMMM yyyy",
        "d MMMM yyyy"
    )

    $parts = @()

    if ($DateText -match "\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}") {
        $parts += $Matches[0]
    }

    if ($DateText -match "^\d{1,2}\s*(?:-|\u2013)\s*\d{1,2}\s+([A-Za-z]{3,9})\s+(\d{4})") {
        $parts += ("{0} {1} {2}" -f (($DateText -replace "^(\d{1,2}).*", '$1')), $Matches[1], $Matches[2])
    }

    if ($DateText -match "^\d{1,2}\s+[A-Za-z]{3,9}\s*(?:-|\u2013)\s*\d{1,2}\s+[A-Za-z]{3,9}\s+(\d{4})") {
        $parts += ($DateText -replace "^(\d{1,2}\s+[A-Za-z]{3,9}).*(\d{4})$", '$1 $2')
    }

    foreach ($part in $parts | Select-Object -Unique) {
        foreach ($format in $formats) {
            $parsed = [datetime]::MinValue
            if ([datetime]::TryParseExact($part, $format, [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::AssumeLocal, [ref]$parsed)) {
                return $parsed
            }
        }
    }

    return [datetime]::MaxValue
}

function Get-DateTextFromLines {
    param([string[]]$Lines)

    if ($null -eq $Lines -or $Lines.Count -eq 0) {
        return $null
    }

    $currentYear = (Get-Date).Year
    $patterns = @(
        "\b\d{1,2}\s*(?:-|\u2013)\s*\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
        "\b\d{1,2}\s+[A-Za-z]{3,9}\s*(?:-|\u2013)\s*\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
        "\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
        "\b\d{1,2}\s*(?:-|\u2013)\s*\d{1,2}\s+[A-Za-z]{3,9}\b",
        "\b\d{1,2}\s+[A-Za-z]{3,9}\s*(?:-|\u2013)\s*\d{1,2}\s+[A-Za-z]{3,9}\b",
        "\b\d{1,2}\s+[A-Za-z]{3,9}\b"
    )

    foreach ($line in $Lines) {
        foreach ($pattern in $patterns) {
            $match = [regex]::Match($line, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            if (-not $match.Success) {
                continue
            }

            $value = Normalize-Whitespace $match.Value
            if ($value -notmatch "\b\d{4}\b") {
                $value = "{0} {1}" -f $value, $currentYear
            }

            return $value.Trim()
        }
    }

    foreach ($line in $Lines) {
        if ($line -match "\b\d{1,2}(:\d{2})?\s*(am|pm)\b") {
            return Normalize-Whitespace $line
        }
    }

    return $null
}

function Get-DateTextFromEventPage {
    param([string]$Url)

    $details = Get-EventPageDetails $Url
    if ($null -eq $details) {
        return $null
    }

    return $details.dateText
}

function Get-StartTimeFromLines {
    param([string[]]$Lines)

    foreach ($line in $Lines) {
        $match = [regex]::Match($line, '\b\d{1,2}(?::|\.)?\d{0,2}\s*(am|pm)\b', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if ($match.Success) {
            $value = Normalize-Whitespace $match.Value.ToLowerInvariant()
            return $value.Replace(".", ":")
        }
    }

    return $null
}

function Get-CostFromLines {
    param(
        [string[]]$Lines,
        [string[]]$Badges
    )

    if ($Badges -contains "Free") {
        return "Free"
    }

    foreach ($line in $Lines) {
        $moneyMatch = [regex]::Match($line, '(Tickets?\s*)?£\s*\d+(?:\.\d{2})?')
        if ($moneyMatch.Success) {
            $value = Normalize-Whitespace $moneyMatch.Value
            $value = $value -replace '^(Tickets?\s*)', ''
            return $value.Trim()
        }
    }

    return $null
}

<#
function Normalize-CurrencyText {
    param([string]$Value)

    $text = Normalize-Whitespace $Value
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $null
    }

    $text = $text -replace '^(Tickets?\s*)', ''
    $text = $text -replace '^£\s*', ([string][char]0x00A3)
    return $text.Trim()
}

function Normalize-CompareText {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ""
    }

    $text = Normalize-Whitespace $Value
    $text = $text.ToLowerInvariant()
    $text = $text -replace "[^a-z0-9]+", ""
    return $text
}

function Get-EventPageDetails {
    param([string]$Url)

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return $null
    }

    if ($script:EventPageDetailCache.ContainsKey($Url)) {
        return $script:EventPageDetailCache[$Url]
    }

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -Headers @{
            "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            "Accept-Language" = "en-GB,en;q=0.9"
            "Referer" = $script:SourceUrl
        }

        $dateText = $null
        $startTime = $null
        $cost = $null

        if ($response.Content -match '(?is)Quick summary.*?Price.*?(Free|£\s*\d+(?:\.\d{2})?)') {
            $cost = Normalize-Whitespace $Matches[1]
        }

        if ($response.Content -match '(?is)Dates and times.*?(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})') {
            $dateText = Normalize-Whitespace $Matches[1]
        }

        if ($response.Content -match '(?is)Dates and times.*?(\d{1,2}(?::|\.)?\d{0,2}\s*(?:am|pm))') {
            $startTime = Normalize-Whitespace($Matches[1].ToLowerInvariant()).Replace(".", ":")
        }

        if ($response.Content -match '"startDate"\s*:\s*"([^"]+)"') {
            $iso = $Matches[1]
            $parsed = [datetime]::MinValue
            if ([datetime]::TryParse($iso, [ref]$parsed)) {
                $dateText = $parsed.ToString("dd MMM yyyy")
                $startTime = $parsed.ToString("h:mmtt").ToLowerInvariant().Replace(":00", "")
            }
        }

        if ($response.Content -match '"price"\s*:\s*"?(0|[0-9]+(?:\.[0-9]{2})?)"?' -or
            $response.Content -match '"lowPrice"\s*:\s*"?(0|[0-9]+(?:\.[0-9]{2})?)"?') {
            $priceValue = $Matches[1]
            if ($priceValue -eq "0") {
                $cost = "Free"
            } else {
                $cost = ("£{0}" -f $priceValue.TrimEnd("0").TrimEnd("."))
            }
        }

        $text = Convert-ToPlainText $response.Content
        $lines = @(
            $text -split "`n" |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ }
        )

        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ([string]::IsNullOrWhiteSpace($cost) -and $lines[$i] -eq "Price" -and $i + 1 -lt $lines.Count) {
                $possiblePrice = Normalize-Whitespace $lines[$i + 1]
                if ($possiblePrice -match '^(Free|£\s*\d+(?:\.\d{2})?)$') {
                    $cost = $possiblePrice
                }
            }

            if ($lines[$i] -eq "Dates and times") {
                for ($j = $i + 1; $j -lt [Math]::Min($i + 8, $lines.Count); $j++) {
                    if ([string]::IsNullOrWhiteSpace($dateText)) {
                        $dateCandidate = Get-DateTextFromLines @($lines[$j])
                        if (-not [string]::IsNullOrWhiteSpace($dateCandidate)) {
                            $dateText = $dateCandidate
                            continue
                        }
                    }

                    if ([string]::IsNullOrWhiteSpace($startTime)) {
                        $timeCandidate = Get-StartTimeFromLines @($lines[$j])
                        if (-not [string]::IsNullOrWhiteSpace($timeCandidate)) {
                            $startTime = $timeCandidate
                        }
                    }
                }
            }
        }

        foreach ($line in $lines) {
            $summaryMatch = [regex]::Match($line, '(?<date>(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}\s+[A-Za-z]{3,9})(?:,\s*(?<time>\d{1,2}(?::|\.)?\d{0,2}\s*(?:am|pm)))?(?:,\s*Tickets?\s*(?<price>£\s*\d+(?:\.\d{2})?|Free))?', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            if ($summaryMatch.Success) {
                if ([string]::IsNullOrWhiteSpace($dateText)) {
                    $dateValue = $summaryMatch.Groups["date"].Value
                    $dateParsed = [datetime]::MinValue
                    if ([datetime]::TryParse(("{0} {1}" -f $dateValue, (Get-Date).Year), [ref]$dateParsed)) {
                        $dateText = $dateParsed.ToString("dd MMM yyyy")
                    } else {
                        $dateText = Normalize-Whitespace $dateValue
                    }
                }

                if ([string]::IsNullOrWhiteSpace($startTime) -and $summaryMatch.Groups["time"].Success) {
                    $startTime = Normalize-Whitespace($summaryMatch.Groups["time"].Value.ToLowerInvariant()).Replace(".", ":")
                }

                if ([string]::IsNullOrWhiteSpace($cost) -and $summaryMatch.Groups["price"].Success) {
                    $cost = Normalize-Whitespace $summaryMatch.Groups["price"].Value
                }
            }
        }

        if ([string]::IsNullOrWhiteSpace($dateText)) {
            $dateText = Get-DateTextFromLines $lines
        }

        if ([string]::IsNullOrWhiteSpace($startTime)) {
            $startTime = Get-StartTimeFromLines $lines
        }

        if ([string]::IsNullOrWhiteSpace($cost)) {
            $cost = Get-CostFromLines -Lines $lines -Badges @()
        }

        $details = [pscustomobject]@{
            dateText = $dateText
            startTime = $startTime
            cost = $cost
        }

        $script:EventPageDetailCache[$Url] = $details
        return $details
    } catch {
        Write-Log ("Event page detail lookup failed for {0}: {1}" -f $Url, $_.Exception.Message)
        $script:EventPageDetailCache[$Url] = $null
        return $null
    }
}

function Normalize-CurrencyText {
    param([string]$Value)

    $text = Normalize-Whitespace $Value
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $null
    }

    $text = $text -replace '^(Tickets?\s*)', ''
    if ($text -match 'Free') {
        return "Free"
    }

    $moneyMatch = [regex]::Match($text, '(?:£|Â£)\s*\d+(?:\.\d{2})?')
    if ($moneyMatch.Success) {
        $amount = $moneyMatch.Value -replace '^(?:£|Â£)\s*', ''
        return ("{0}{1}" -f [char]0x00A3, $amount)
    }

    return $text.Trim()
}

function Get-CostFromLines {
    param(
        [string[]]$Lines,
        [string[]]$Badges
    )

    if ($Badges -contains "Free") {
        return "Free"
    }

    foreach ($line in $Lines) {
        $moneyMatch = [regex]::Match($line, '(Tickets?\s*)?(?:£|Â£)\s*\d+(?:\.\d{2})?|Free')
        if ($moneyMatch.Success) {
            return Normalize-CurrencyText $moneyMatch.Value
        }
    }

    return $null
}

function Get-EventPageDetails {
    param([string]$Url)

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return $null
    }

    if ($script:EventPageDetailCache.ContainsKey($Url)) {
        return $script:EventPageDetailCache[$Url]
    }

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -Headers @{
            "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            "Accept-Language" = "en-GB,en;q=0.9"
            "Referer" = $script:SourceUrl
        }

        $dateText = $null
        $startTime = $null
        $cost = $null

        $text = Convert-ToPlainText $response.Content
        $lines = @(
            $text -split "`n" |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ }
        )

        foreach ($line in $lines) {
            $summaryMatch = [regex]::Match($line, '(?<date>(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}\s+[A-Za-z]{3,9})(?:,\s*(?<time>\d{1,2}(?::|\.)?\d{0,2}\s*(?:am|pm)))?(?:,\s*Tickets?\s*(?<price>(?:£|Â£)\s*\d+(?:\.\d{2})?|Free))?', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            if (-not $summaryMatch.Success) {
                continue
            }

            if ([string]::IsNullOrWhiteSpace($dateText)) {
                $dateValue = $summaryMatch.Groups["date"].Value
                $dateParsed = [datetime]::MinValue
                if ([datetime]::TryParse(("{0} {1}" -f $dateValue, (Get-Date).Year), [ref]$dateParsed)) {
                    $dateText = $dateParsed.ToString("dd MMM yyyy")
                } else {
                    $dateText = Normalize-Whitespace $dateValue
                }
            }

            if ([string]::IsNullOrWhiteSpace($startTime) -and $summaryMatch.Groups["time"].Success) {
                $startTime = Normalize-Whitespace($summaryMatch.Groups["time"].Value.ToLowerInvariant()).Replace(".", ":")
            }

            if ([string]::IsNullOrWhiteSpace($cost) -and $summaryMatch.Groups["price"].Success) {
                $cost = Normalize-CurrencyText $summaryMatch.Groups["price"].Value
            }
        }

        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -eq "Price") {
                for ($j = $i + 1; $j -lt [Math]::Min($i + 4, $lines.Count); $j++) {
                    if ([string]::IsNullOrWhiteSpace($cost)) {
                        $cost = Get-CostFromLines -Lines @($lines[$j]) -Badges @()
                    }
                }
            }

            if ($lines[$i] -eq "Dates and times") {
                for ($j = $i + 1; $j -lt [Math]::Min($i + 8, $lines.Count); $j++) {
                    if ([string]::IsNullOrWhiteSpace($dateText)) {
                        $dateCandidate = Get-DateTextFromLines @($lines[$j])
                        if (-not [string]::IsNullOrWhiteSpace($dateCandidate)) {
                            $dateText = $dateCandidate
                        }
                    }

                    if ([string]::IsNullOrWhiteSpace($startTime)) {
                        $timeCandidate = Get-StartTimeFromLines @($lines[$j])
                        if (-not [string]::IsNullOrWhiteSpace($timeCandidate)) {
                            $startTime = $timeCandidate
                        }
                    }
                }
            }
        }

        if ([string]::IsNullOrWhiteSpace($dateText)) {
            $dateText = Get-DateTextFromLines $lines
        }

        if ([string]::IsNullOrWhiteSpace($startTime)) {
            $startTime = Get-StartTimeFromLines $lines
        }

        if ([string]::IsNullOrWhiteSpace($cost)) {
            $cost = Get-CostFromLines -Lines $lines -Badges @()
        }

        if ([string]::IsNullOrWhiteSpace($dateText) -or [string]::IsNullOrWhiteSpace($startTime)) {
            if ($response.Content -match '"startDate"\s*:\s*"([^"]+)"') {
                $iso = $Matches[1]
                $parsed = [datetime]::MinValue
                if ([datetime]::TryParse($iso, [ref]$parsed)) {
                    if ([string]::IsNullOrWhiteSpace($dateText)) {
                        $dateText = $parsed.ToString("dd MMM yyyy")
                    }

                    $hasMeaningfulTime = $iso -match 'T(?!00:00)(?!00:00:00)\d{2}:\d{2}'
                    if ([string]::IsNullOrWhiteSpace($startTime) -and $hasMeaningfulTime) {
                        $startTime = $parsed.ToString("h:mmtt").ToLowerInvariant().Replace(":00", "")
                    }
                }
            }
        }

        if ([string]::IsNullOrWhiteSpace($cost) -and ($response.Content -match '"price"\s*:\s*"?(0|[0-9]+(?:\.[0-9]{2})?)"?' -or
            $response.Content -match '"lowPrice"\s*:\s*"?(0|[0-9]+(?:\.[0-9]{2})?)"?')) {
            $priceValue = $Matches[1]
            if ($priceValue -eq "0") {
                $cost = "Free"
            } else {
                $cost = ("{0}{1}" -f [char]0x00A3, $priceValue.TrimEnd("0").TrimEnd("."))
            }
        }

        $details = [pscustomobject]@{
            dateText = $dateText
            startTime = $startTime
            cost = $cost
        }

        $script:EventPageDetailCache[$Url] = $details
        return $details
    } catch {
        Write-Log ("Event page detail lookup failed for {0}: {1}" -f $Url, $_.Exception.Message)
        $script:EventPageDetailCache[$Url] = $null
        return $null
    }
}

#>

function Normalize-CompareText {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ""
    }

    $text = Normalize-Whitespace $Value
    $text = $text.ToLowerInvariant()
    $text = $text -replace "[^a-z0-9]+", ""
    return $text
}

function Normalize-CurrencyText {
    param([string]$Value)

    $text = Normalize-Whitespace $Value
    if ([string]::IsNullOrWhiteSpace($text)) {
        return $null
    }

    $text = $text -replace '^(Tickets?\s*)', ''
    if ($text -match '(?i)\bfree\b') {
        return "Free"
    }

    $moneyMatch = [regex]::Match($text, '\d+(?:\.\d{2})?')
    if ($moneyMatch.Success) {
        return ("{0}{1}" -f [char]0x00A3, $moneyMatch.Value)
    }

    return $text.Trim()
}

function Get-CostFromLines {
    param(
        [string[]]$Lines,
        [string[]]$Badges
    )

    if ($Badges -contains "Free") {
        return "Free"
    }

    foreach ($line in $Lines) {
        $normalized = Normalize-Whitespace $line
        if ($normalized -match '(?i)\bfree\b') {
            return "Free"
        }

        if ($normalized -match '(?i)(tickets?|price)' -or $normalized.Contains([string][char]0x00A3)) {
            $value = Normalize-CurrencyText $normalized
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                return $value
            }
        }
    }

    return $null
}

function Get-EventPageDetails {
    param([string]$Url)

    if ([string]::IsNullOrWhiteSpace($Url)) {
        return $null
    }

    if ($script:EventPageDetailCache.ContainsKey($Url)) {
        return $script:EventPageDetailCache[$Url]
    }

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -Headers @{
            "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            "Accept-Language" = "en-GB,en;q=0.9"
            "Referer" = $script:SourceUrl
        }

        $dateText = $null
        $startTime = $null
        $cost = $null

        $text = Convert-ToPlainText $response.Content
        $lines = @(
            $text -split "`n" |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ }
        )

        foreach ($line in $lines) {
            $summaryMatch = [regex]::Match($line, '(?<date>(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}\s+[A-Za-z]{3,9})(?:,\s*(?<time>\d{1,2}(?::|\.)?\d{0,2}\s*(?:am|pm)))?(?:,\s*Tickets?\s*(?<price>[^,]+))?', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            if (-not $summaryMatch.Success) {
                continue
            }

            if ([string]::IsNullOrWhiteSpace($dateText)) {
                $dateValue = $summaryMatch.Groups["date"].Value
                $dateParsed = [datetime]::MinValue
                if ([datetime]::TryParse(("{0} {1}" -f $dateValue, (Get-Date).Year), [ref]$dateParsed)) {
                    $dateText = $dateParsed.ToString("dd MMM yyyy")
                } else {
                    $dateText = Normalize-Whitespace $dateValue
                }
            }

            if ([string]::IsNullOrWhiteSpace($startTime) -and $summaryMatch.Groups["time"].Success) {
                $startTime = Normalize-Whitespace($summaryMatch.Groups["time"].Value.ToLowerInvariant()).Replace(".", ":")
            }

            if ([string]::IsNullOrWhiteSpace($cost) -and $summaryMatch.Groups["price"].Success) {
                $cost = Normalize-CurrencyText $summaryMatch.Groups["price"].Value
            }
        }

        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -eq "Price") {
                for ($j = $i + 1; $j -lt [Math]::Min($i + 4, $lines.Count); $j++) {
                    if ([string]::IsNullOrWhiteSpace($cost)) {
                        $cost = Get-CostFromLines -Lines @($lines[$j]) -Badges @()
                    }
                }
            }

            if ($lines[$i] -eq "Dates and times") {
                for ($j = $i + 1; $j -lt [Math]::Min($i + 8, $lines.Count); $j++) {
                    if ([string]::IsNullOrWhiteSpace($dateText)) {
                        $dateCandidate = Get-DateTextFromLines @($lines[$j])
                        if (-not [string]::IsNullOrWhiteSpace($dateCandidate)) {
                            $dateText = $dateCandidate
                        }
                    }

                    if ([string]::IsNullOrWhiteSpace($startTime)) {
                        $timeCandidate = Get-StartTimeFromLines @($lines[$j])
                        if (-not [string]::IsNullOrWhiteSpace($timeCandidate)) {
                            $startTime = $timeCandidate
                        }
                    }
                }
            }
        }

        if ([string]::IsNullOrWhiteSpace($dateText)) {
            $dateText = Get-DateTextFromLines $lines
        }

        if ([string]::IsNullOrWhiteSpace($startTime)) {
            $startTime = Get-StartTimeFromLines $lines
        }

        if ([string]::IsNullOrWhiteSpace($cost)) {
            $cost = Get-CostFromLines -Lines $lines -Badges @()
        }

        if ([string]::IsNullOrWhiteSpace($dateText) -or [string]::IsNullOrWhiteSpace($startTime)) {
            if ($response.Content -match '"startDate"\s*:\s*"([^"]+)"') {
                $iso = $Matches[1]
                $parsed = [datetime]::MinValue
                if ([datetime]::TryParse($iso, [ref]$parsed)) {
                    if ([string]::IsNullOrWhiteSpace($dateText)) {
                        $dateText = $parsed.ToString("dd MMM yyyy")
                    }

                    $hasMeaningfulTime = $iso -match 'T(?!00:00)(?!00:00:00)\d{2}:\d{2}'
                    if ([string]::IsNullOrWhiteSpace($startTime) -and $hasMeaningfulTime) {
                        $startTime = $parsed.ToString("h:mmtt").ToLowerInvariant().Replace(":00", "")
                    }
                }
            }
        }

        if ([string]::IsNullOrWhiteSpace($cost) -and ($response.Content -match '"price"\s*:\s*"?(0|[0-9]+(?:\.[0-9]{2})?)"?' -or
            $response.Content -match '"lowPrice"\s*:\s*"?(0|[0-9]+(?:\.[0-9]{2})?)"?')) {
            $priceValue = $Matches[1]
            if ($priceValue -eq "0") {
                $cost = "Free"
            } else {
                $cost = ("{0}{1}" -f [char]0x00A3, $priceValue.TrimEnd("0").TrimEnd("."))
            }
        }

        $details = [pscustomobject]@{
            dateText = $dateText
            startTime = $startTime
            cost = $cost
        }

        $script:EventPageDetailCache[$Url] = $details
        return $details
    } catch {
        Write-Log ("Event page detail lookup failed for {0}: {1}" -f $Url, $_.Exception.Message)
        $script:EventPageDetailCache[$Url] = $null
        return $null
    }
}

function Get-BestImageUrlFromCard {
    param([string]$CardHtml)

    $attributePatterns = @(
        '(?is)\sdata-srcset="([^"]+)"',
        "(?is)\sdata-srcset='([^']+)'",
        '(?is)\ssrcset="([^"]+)"',
        "(?is)\ssrcset='([^']+)'",
        '(?is)\sdata-src="([^"]+)"',
        "(?is)\sdata-src='([^']+)'",
        '(?is)\ssrc="([^"]+)"',
        "(?is)\ssrc='([^']+)'"
    )

    foreach ($pattern in $attributePatterns) {
        $match = [regex]::Match($CardHtml, $pattern)
        if (-not $match.Success) {
            continue
        }

        $value = $match.Groups[1].Value.Trim()
        if ([string]::IsNullOrWhiteSpace($value)) {
            continue
        }

        if ($pattern -match 'srcset') {
            $candidates = @()
            foreach ($entry in $value.Split(",")) {
                $trimmed = $entry.Trim()
                if ([string]::IsNullOrWhiteSpace($trimmed)) {
                    continue
                }

                $parts = $trimmed -split "\s+"
                $url = $parts[0]
                $width = 0
                if ($parts.Count -gt 1 -and $parts[1] -match '^(\d+)w$') {
                    $width = [int]$Matches[1]
                }

                $candidates += [pscustomobject]@{
                    Url = $url
                    Width = $width
                }
            }

            $best = $candidates | Sort-Object Width -Descending | Select-Object -First 1
            if ($null -ne $best -and -not [string]::IsNullOrWhiteSpace($best.Url)) {
                return Get-AbsoluteUrl $best.Url
            }
        } else {
            return Get-AbsoluteUrl $value
        }
    }

    return $null
}

function Get-EventCardData {
    param(
        [string]$SectionTitle,
        [string]$CardHtml
    )

    $titleMatch = [regex]::Match($CardHtml, "(?is)<h3[^>]*>(.*?)</h3>")
    if (-not $titleMatch.Success) {
        return $null
    }

    $title = Normalize-Whitespace $titleMatch.Groups[1].Value
    if ([string]::IsNullOrWhiteSpace($title)) {
        return $null
    }

    $linkMatch = [regex]::Match($CardHtml, "(?is)<a[^>]+href=""([^""]+)""[^>]*>")
    $bestImageUrl = Get-BestImageUrlFromCard $CardHtml

    $text = Convert-ToPlainText $CardHtml
    $lines = @(
        $text -split "`n" |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ }
    )

    $badges = @()
    foreach ($badge in @("Free", "Sold Out", "Limited Availability")) {
        if ($lines -contains $badge) {
            $badges += $badge
        }
    }

    $eventLink = if ($linkMatch.Success) { Get-AbsoluteUrl $linkMatch.Groups[1].Value } else { $null }
    $dateLine = Get-DateTextFromLines $lines
    $startTime = Get-StartTimeFromLines $lines
    $cost = Get-CostFromLines -Lines $lines -Badges $badges

    if (-not [string]::IsNullOrWhiteSpace($eventLink)) {
        $eventPageDetails = Get-EventPageDetails $eventLink
        if ($null -ne $eventPageDetails) {
            if (-not [string]::IsNullOrWhiteSpace($eventPageDetails.dateText)) {
                $dateLine = $eventPageDetails.dateText
            }
            if (-not [string]::IsNullOrWhiteSpace($eventPageDetails.startTime)) {
                $startTime = $eventPageDetails.startTime
            }
            if (-not [string]::IsNullOrWhiteSpace($eventPageDetails.cost)) {
                $cost = $eventPageDetails.cost
            }
        }
    }

    $meta = @()
    $titleKey = Normalize-CompareText $title
    foreach ($line in $lines) {
        if ($line -eq $SectionTitle -or
            $line -eq $title -or
            $line -eq "More" -or
            $line -eq "Arts Centre Washington" -or
            $badges -contains $line -or
            $line -eq $dateLine -or
            $line -eq $startTime -or
            $line -eq $cost) {
            continue
        }

        $lineKey = Normalize-CompareText $line
        if (-not [string]::IsNullOrWhiteSpace($titleKey) -and -not [string]::IsNullOrWhiteSpace($lineKey) -and
            ($lineKey -eq $titleKey -or $lineKey.Contains($titleKey) -or $titleKey.Contains($lineKey))) {
            continue
        }

        if ($line -match '^(View all|Part of|Book now|Book tickets|Register your interest)\b') {
            continue
        }

        $meta += $line
    }

    [pscustomobject]@{
        title = $title
        category = $SectionTitle
        isClass = $script:ClassCategories -contains $SectionTitle
        dateText = $dateLine
        startTime = $startTime
        cost = $cost
        sortDate = (Get-DateSortKey $dateLine).ToString("o")
        status = ($badges -join " | ")
        meta = ($meta | Select-Object -First 3)
        link = $eventLink
        image = $bestImageUrl
        imageLocal = $null
        qrLocal = $null
    }
}

function Parse-EventsFromHtml {
    param([string]$Html)

    $results = New-Object System.Collections.Generic.List[object]
    $sectionMatches = [regex]::Matches($Html, "(?is)<h2[^>]*>(.*?)</h2>")

    for ($index = 0; $index -lt $sectionMatches.Count; $index++) {
        $sectionTitle = Normalize-CategoryName $sectionMatches[$index].Groups[1].Value

        if ([string]::IsNullOrWhiteSpace($sectionTitle)) {
            continue
        }

        if ($sectionTitle -notin @(
            "Theatre and Performance",
            "Music",
            "Comedy",
            "Films",
            "Talks",
            "Adult Workshops and Activities",
            "Children and Young People's Activities",
            "Exhibitions",
            "Special Events"
        )) {
            continue
        }

        $sectionStart = $sectionMatches[$index].Index + $sectionMatches[$index].Length
        $sectionEnd = if ($index + 1 -lt $sectionMatches.Count) { $sectionMatches[$index + 1].Index } else { $Html.Length }
        $sectionHtml = $Html.Substring($sectionStart, $sectionEnd - $sectionStart)

        $cardMatches = [regex]::Matches($sectionHtml, "(?is)<a\b[^>]*>.*?<h3[^>]*>.*?</h3>.*?</a>")

        foreach ($cardMatch in $cardMatches) {
            $item = Get-EventCardData -SectionTitle $sectionTitle -CardHtml $cardMatch.Value
            if ($null -ne $item) {
                $results.Add($item)
            }
        }
    }

    $unique = $results |
        Group-Object { "{0}|{1}|{2}" -f $_.title, $_.category, $_.dateText } |
        ForEach-Object { $_.Group[0] } |
        Sort-Object @{ Expression = {
            try {
                [datetime]$_.sortDate
            } catch {
                [datetime]::MaxValue
            }
        } }, @{ Expression = { $_.title } }

    return ,$unique
}

function Get-LiveEvents {
    $cacheAge = (Get-Date) - $script:EventCache.GeneratedAt
    if ($script:EventCache.Items.Count -gt 0 -and $cacheAge.TotalMinutes -lt $RefreshMinutes) {
        return $script:EventCache
    }

    try {
        Write-Log ("Fetching live events from {0}" -f $script:SourceUrl)
        $response = Invoke-WebRequest -Uri $script:SourceUrl -UseBasicParsing -Headers @{
            "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            "Accept-Language" = "en-GB,en;q=0.9"
        }
        $items = Parse-EventsFromHtml -Html $response.Content

        foreach ($item in $items) {
            if (-not [string]::IsNullOrWhiteSpace($item.image)) {
                $item.imageLocal = Get-LocalImageUrl $item.image
            }
            if (-not [string]::IsNullOrWhiteSpace($item.link)) {
                $item.qrLocal = Get-LocalQrUrl $item.link
            }
        }

        if (@($items).Count -eq 0) {
            throw "The live page was fetched, but no event cards were parsed."
        }

        Write-Log ("Fetched {0} live events." -f @($items).Count)

        $script:EventCache = @{
            GeneratedAt = Get-Date
            Items = $items
            LastError = $null
        }
    } catch {
        $script:EventCache.LastError = $_.Exception.Message
        Write-Log ("Live fetch failed: {0}" -f $_.Exception.Message)
        throw
    }

    return $script:EventCache
}

function Get-ContentType {
    param([string]$Path)

    switch ([System.IO.Path]::GetExtension($Path).ToLowerInvariant()) {
        ".html" { "text/html; charset=utf-8" }
        ".css" { "text/css; charset=utf-8" }
        ".js" { "application/javascript; charset=utf-8" }
        ".json" { "application/json; charset=utf-8" }
        ".png" { "image/png" }
        ".jpg" { "image/jpeg" }
        ".jpeg" { "image/jpeg" }
        ".svg" { "image/svg+xml" }
        ".ico" { "image/x-icon" }
        default { "application/octet-stream" }
    }
}

function Get-StatusText {
    param([int]$StatusCode)

    switch ($StatusCode) {
        200 { "OK" }
        400 { "Bad Request" }
        403 { "Forbidden" }
        404 { "Not Found" }
        405 { "Method Not Allowed" }
        500 { "Internal Server Error" }
        default { "OK" }
    }
}

function Send-HttpResponse {
    param(
        [System.Net.Sockets.TcpClient]$Client,
        [int]$StatusCode,
        [string]$ContentType,
        [byte[]]$Body
    )

    $stream = $Client.GetStream()
    $statusText = Get-StatusText $StatusCode
    $headers = @(
        "HTTP/1.1 $StatusCode $statusText",
        "Content-Type: $ContentType",
        "Content-Length: $($Body.Length)",
        "Connection: close",
        "Cache-Control: no-store",
        ""
    ) -join "`r`n"

    $headerBytes = [System.Text.Encoding]::ASCII.GetBytes($headers + "`r`n")
    $stream.Write($headerBytes, 0, $headerBytes.Length)
    $stream.Write($Body, 0, $Body.Length)
    $stream.Flush()
}

function Send-JsonResponse {
    param(
        [System.Net.Sockets.TcpClient]$Client,
        [object]$Payload,
        [int]$StatusCode = 200
    )

    $json = $Payload | ConvertTo-Json -Depth 6
    $body = [System.Text.Encoding]::UTF8.GetBytes($json)
    Send-HttpResponse -Client $Client -StatusCode $StatusCode -ContentType "application/json; charset=utf-8" -Body $body
}

function Send-TextResponse {
    param(
        [System.Net.Sockets.TcpClient]$Client,
        [string]$Text,
        [int]$StatusCode = 200
    )

    $body = [System.Text.Encoding]::UTF8.GetBytes($Text)
    Send-HttpResponse -Client $Client -StatusCode $StatusCode -ContentType "text/plain; charset=utf-8" -Body $body
}

function Send-FileResponse {
    param(
        [System.Net.Sockets.TcpClient]$Client,
        [string]$FilePath
    )

    $body = [System.IO.File]::ReadAllBytes($FilePath)
    $contentType = Get-ContentType $FilePath
    Send-HttpResponse -Client $Client -StatusCode 200 -ContentType $contentType -Body $body
}

function Read-HttpRequest {
    param([System.Net.Sockets.TcpClient]$Client)

    $stream = $Client.GetStream()
    $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::ASCII, $false, 4096, $true)
    $requestLine = $reader.ReadLine()

    if ([string]::IsNullOrWhiteSpace($requestLine)) {
        return $null
    }

    $headerLines = New-Object System.Collections.Generic.List[string]
    while ($true) {
        $line = $reader.ReadLine()
        if ($null -eq $line -or $line -eq "") {
            break
        }

        $headerLines.Add($line)
    }

    $parts = $requestLine.Split(" ")
    if ($parts.Count -lt 2) {
        return $null
    }

    return [pscustomobject]@{
        Method = $parts[0]
        Target = $parts[1]
    }
}

$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
$listener.Start()

$prefix = "http://localhost:{0}/" -f $Port
Write-Host ("Arts Centre Washington display server running at {0}" -f $prefix)
Write-Host "Press Ctrl+C to stop."
Set-Content -LiteralPath $script:LogPath -Value ("[{0}] Server starting at {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $prefix)
Write-Log "Server started successfully."

try {
    while ($true) {
        $client = $listener.AcceptTcpClient()

        try {
            $request = Read-HttpRequest -Client $client
            if ($null -eq $request) {
                Send-TextResponse -Client $client -Text "Bad request" -StatusCode 400
                continue
            }

            if ($request.Method -ne "GET") {
                Send-TextResponse -Client $client -Text "Only GET is supported" -StatusCode 405
                continue
            }

            $url = [uri]("http://localhost:{0}{1}" -f $Port, $request.Target)
            $path = $url.AbsolutePath
            $query = Parse-QueryString $url.Query

            if ($path -eq "/api/events") {
                $includeClasses = $true
                if ($query["includeClasses"] -eq "false") {
                    $includeClasses = $false
                }

                $cache = Get-LiveEvents
                $items = if ($includeClasses) {
                    $cache.Items
                } else {
                    $cache.Items | Where-Object { -not $_.isClass }
                }

                Send-JsonResponse -Client $client -Payload @{
                    fetchedAt = $cache.GeneratedAt.ToString("o")
                    includeClasses = $includeClasses
                    sourceUrl = $script:SourceUrl
                    total = @($items).Count
                    items = @($items)
                    lastError = $cache.LastError
                }

                continue
            }

            if ($path -eq "/health") {
                Send-JsonResponse -Client $client -Payload @{
                    ok = $true
                    refreshedAt = $script:EventCache.GeneratedAt.ToString("o")
                    cachedItems = @($script:EventCache.Items).Count
                    lastError = $script:EventCache.LastError
                }
                continue
            }

            if ($path.StartsWith("/cache/images/", [System.StringComparison]::OrdinalIgnoreCase)) {
                $relativeCachedPath = $path.TrimStart("/")
                $fullCachedPath = [System.IO.Path]::GetFullPath((Join-Path $script:ProjectRoot $relativeCachedPath.Replace("/", "\")))

                if (-not $fullCachedPath.StartsWith($script:ImageCacheRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                    Send-TextResponse -Client $client -Text "Forbidden" -StatusCode 403
                    continue
                }

                if (-not (Test-Path -LiteralPath $fullCachedPath -PathType Leaf)) {
                    Send-TextResponse -Client $client -Text "Not found" -StatusCode 404
                    continue
                }

                Send-FileResponse -Client $client -FilePath $fullCachedPath
                continue
            }

            if ($path.StartsWith("/cache/qr/", [System.StringComparison]::OrdinalIgnoreCase)) {
                $relativeCachedPath = $path.TrimStart("/")
                $fullCachedPath = [System.IO.Path]::GetFullPath((Join-Path $script:ProjectRoot $relativeCachedPath.Replace("/", "\")))

                if (-not $fullCachedPath.StartsWith($script:QrCacheRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                    Send-TextResponse -Client $client -Text "Forbidden" -StatusCode 403
                    continue
                }

                if (-not (Test-Path -LiteralPath $fullCachedPath -PathType Leaf)) {
                    Send-TextResponse -Client $client -Text "Not found" -StatusCode 404
                    continue
                }

                Send-FileResponse -Client $client -FilePath $fullCachedPath
                continue
            }

            $relativePath = if ($path -eq "/") { "index.html" } else { $path.TrimStart("/") }
            $fullPath = [System.IO.Path]::GetFullPath((Join-Path $script:PublicRoot $relativePath))

            if (-not $fullPath.StartsWith($script:PublicRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                Send-TextResponse -Client $client -Text "Forbidden" -StatusCode 403
                continue
            }

            if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
                Send-TextResponse -Client $client -Text "Not found" -StatusCode 404
                continue
            }

            Send-FileResponse -Client $client -FilePath $fullPath
        } catch {
            Send-JsonResponse -Client $client -Payload @{
                error = $_.Exception.Message
            } -StatusCode 500
        } finally {
            $client.Close()
        }
    }
} finally {
    Write-Log "Server stopped."
    $listener.Stop()
}
