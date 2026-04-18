param(
    [string]$OutputRoot = (Join-Path $PSScriptRoot "..\public")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$sourceUrl = "https://www.sunderlandculture.org.uk/arts-centre-washington/whats-on/"
$outputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
$imageRoot = Join-Path $outputRoot "cache\images"
$qrRoot = Join-Path $outputRoot "cache\qr"
$detailCache = @{}
$fetchHelperPath = Join-Path $PSScriptRoot "fetch-url.mjs"
$classCategories = @(
    "Adult Workshops and Activities",
    "Children and Young People's Activities"
)
$allowedSections = @(
    "Theatre and Performance",
    "Music",
    "Comedy",
    "Films",
    "Talks",
    "Adult Workshops and Activities",
    "Children and Young People's Activities",
    "Exhibitions",
    "Special Events"
)

function Ensure-Directory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        $null = New-Item -ItemType Directory -Path $Path -Force
    }
}

function Invoke-NodeFetch([string]$Url, [string]$OutFile) {
    $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
    if ($null -eq $nodeCommand) {
        throw "Node.js is required for the HTTP fallback, but 'node' was not found."
    }
    if (-not (Test-Path -LiteralPath $fetchHelperPath -PathType Leaf)) {
        throw "Fetch helper not found at $fetchHelperPath"
    }

    $arguments = @($fetchHelperPath, $Url)
    if (-not [string]::IsNullOrWhiteSpace($OutFile)) {
        $arguments += @("--out", $OutFile)
    }

    $previousProxyValues = @{
        HTTP_PROXY = $env:HTTP_PROXY
        HTTPS_PROXY = $env:HTTPS_PROXY
        ALL_PROXY = $env:ALL_PROXY
        GIT_HTTP_PROXY = $env:GIT_HTTP_PROXY
        GIT_HTTPS_PROXY = $env:GIT_HTTPS_PROXY
    }

    try {
        $env:HTTP_PROXY = ""
        $env:HTTPS_PROXY = ""
        $env:ALL_PROXY = ""
        $env:GIT_HTTP_PROXY = ""
        $env:GIT_HTTPS_PROXY = ""
        & $nodeCommand.Source @arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Node fetch failed for $Url"
        }
    } finally {
        foreach ($key in $previousProxyValues.Keys) {
            $value = $previousProxyValues[$key]
            if ($null -eq $value) {
                Remove-Item ("Env:{0}" -f $key) -ErrorAction SilentlyContinue
            } else {
                Set-Item ("Env:{0}" -f $key) -Value $value
            }
        }
    }
}

function Get-WebContent([string]$Url) {
    $headers = @{
        "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        "Accept-Language" = "en-GB,en;q=0.9"
        "Referer" = $sourceUrl
    }

    $previousProxyValues = @{
        HTTP_PROXY = $env:HTTP_PROXY
        HTTPS_PROXY = $env:HTTPS_PROXY
        ALL_PROXY = $env:ALL_PROXY
        GIT_HTTP_PROXY = $env:GIT_HTTP_PROXY
        GIT_HTTPS_PROXY = $env:GIT_HTTPS_PROXY
    }

    try {
        $env:HTTP_PROXY = ""
        $env:HTTPS_PROXY = ""
        $env:ALL_PROXY = ""
        $env:GIT_HTTP_PROXY = ""
        $env:GIT_HTTPS_PROXY = ""

        try {
            return (Invoke-WebRequest -Uri $Url -UseBasicParsing -Headers $headers).Content
        } catch {
            $tempPath = [System.IO.Path]::GetTempFileName()
            try {
                Invoke-NodeFetch -Url $Url -OutFile $tempPath
                return [System.IO.File]::ReadAllText($tempPath)
            } finally {
                if (Test-Path -LiteralPath $tempPath -PathType Leaf) {
                    Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
                }
            }
        }
    } finally {
        foreach ($key in $previousProxyValues.Keys) {
            $value = $previousProxyValues[$key]
            if ($null -eq $value) {
                Remove-Item ("Env:{0}" -f $key) -ErrorAction SilentlyContinue
            } else {
                Set-Item ("Env:{0}" -f $key) -Value $value
            }
        }
    }
}

function Download-WebFile([string]$Url, [string]$Destination) {
    $headers = @{
        "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        "Referer" = $sourceUrl
    }

    $previousProxyValues = @{
        HTTP_PROXY = $env:HTTP_PROXY
        HTTPS_PROXY = $env:HTTPS_PROXY
        ALL_PROXY = $env:ALL_PROXY
        GIT_HTTP_PROXY = $env:GIT_HTTP_PROXY
        GIT_HTTPS_PROXY = $env:GIT_HTTPS_PROXY
    }

    try {
        $env:HTTP_PROXY = ""
        $env:HTTPS_PROXY = ""
        $env:ALL_PROXY = ""
        $env:GIT_HTTP_PROXY = ""
        $env:GIT_HTTPS_PROXY = ""

        try {
            Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing -Headers $headers
        } catch {
            Invoke-NodeFetch -Url $Url -OutFile $Destination
        }
    } finally {
        foreach ($key in $previousProxyValues.Keys) {
            $value = $previousProxyValues[$key]
            if ($null -eq $value) {
                Remove-Item ("Env:{0}" -f $key) -ErrorAction SilentlyContinue
            } else {
                Set-Item ("Env:{0}" -f $key) -Value $value
            }
        }
    }
}

function Reset-Directory([string]$Path) {
    if (Test-Path -LiteralPath $Path -PathType Container) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
    $null = New-Item -ItemType Directory -Path $Path -Force
}

function Normalize-Whitespace([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value)) { return "" }
    $text = [System.Net.WebUtility]::HtmlDecode($Value)
    $text = $text.Replace([string][char]0x2019, "'").Replace([string][char]0x2018, "'").Replace([string][char]0x2013, "-").Replace("Â£", [string][char]0x00A3)
    return ($text -replace '\s+', ' ').Trim()
}

function Normalize-CompareText([string]$Value) {
    return ((Normalize-Whitespace $Value).ToLowerInvariant() -replace '[^a-z0-9]+', '')
}

function Normalize-CurrencyText([string]$Value) {
    $text = Normalize-Whitespace $Value
    if ([string]::IsNullOrWhiteSpace($text)) { return $null }
    $text = $text -replace '^(Tickets?\s*)', ''
    if ($text -match '(?i)\bfree\b') { return "Free" }
    $match = [regex]::Match($text, [regex]::Escape([string][char]0x00A3) + '\s*\d+(?:\.\d{2})?')
    if ($match.Success) {
        $amount = $match.Value -replace ('^' + [regex]::Escape([string][char]0x00A3) + '\s*'), ''
        return ("{0}{1}" -f [char]0x00A3, $amount)
    }
    return $text
}

function Convert-ToPlainText([string]$Html) {
    if ([string]::IsNullOrWhiteSpace($Html)) { return "" }
    $text = $Html -replace '(?is)<script.*?</script>', ' '
    $text = $text -replace '(?is)<style.*?</style>', ' '
    $text = $text -replace '(?i)<br\s*/?>', "`n"
    $text = $text -replace '(?i)</(p|div|section|article|li|h1|h2|h3|h4|h5|h6)>', "`n"
    $text = $text -replace '(?is)<.*?>', ' '
    $text = [System.Net.WebUtility]::HtmlDecode($text)
    $text = $text -replace '[\r\t]', ' '
    $text = $text -replace '\u00A0', ' '
    $text = $text -replace ' +', ' '
    $text = $text -replace ' *`n *', "`n"
    return $text.Trim()
}

function Split-Lines([string]$Text) {
    return @($Text -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

function Get-AbsoluteUrl([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) { return $null }
    if ($Url.StartsWith("http://") -or $Url.StartsWith("https://")) { return $Url }
    return ([uri]::new([uri]$sourceUrl, $Url)).AbsoluteUri
}

function Get-DateTextFromLines([string[]]$Lines) {
    $monthPattern = '(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    $currentYear = (Get-Date).Year
    $patterns = @(
        "\b\d{1,2}\s*-\s*\d{1,2}\s+$monthPattern\s+\d{4}\b",
        "\b\d{1,2}\s+$monthPattern\s*-\s*\d{1,2}\s+$monthPattern\s+\d{4}\b",
        "\b\d{1,2}\s+$monthPattern\s+\d{4}\b",
        "\b\d{1,2}\s*-\s*\d{1,2}\s+$monthPattern\b",
        "\b\d{1,2}\s+$monthPattern\s*-\s*\d{1,2}\s+$monthPattern\b",
        "\b\d{1,2}\s+$monthPattern\b"
    )
    foreach ($line in $Lines) {
        foreach ($pattern in $patterns) {
            $match = [regex]::Match($line, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            if ($match.Success) {
                $value = Normalize-Whitespace $match.Value
                if ($value -notmatch '\b\d{4}\b') { $value = "{0} {1}" -f $value, $currentYear }
                return $value
            }
        }
    }
    return $null
}

function Get-StartTimeFromLines([string[]]$Lines) {
    foreach ($line in $Lines) {
        $match = [regex]::Match($line, '\b\d{1,2}(?::|\.)?\d{0,2}\s*(am|pm)\b', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if ($match.Success) { return (Normalize-Whitespace ($match.Value.ToLowerInvariant())).Replace(".", ":") }
    }
    return $null
}

function Get-CostFromLines([string[]]$Lines, [string[]]$Badges) {
    if ($Badges -contains "Free") { return "Free" }
    foreach ($line in $Lines) {
        $match = [regex]::Match($line, '(Tickets?\s*)?(£\s*\d+(?:\.\d{2})?|Free)', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if ($match.Success) { return Normalize-CurrencyText $match.Value }
    }
    return $null
}

function Get-DateSortKey([string]$DateText) {
    if ([string]::IsNullOrWhiteSpace($DateText)) { return [datetime]::MaxValue }
    $match = [regex]::Match($DateText, '\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}')
    if (-not $match.Success) {
        $match = [regex]::Match($DateText, '^\d{1,2}\s*-\s*\d{1,2}\s+([A-Za-z]{3,9})\s+(\d{4})')
        if ($match.Success) {
            $dateText = "{0} {1} {2}" -f (($DateText -replace '^(\d{1,2}).*', '$1')), $match.Groups[1].Value, $match.Groups[2].Value
            $match = [regex]::Match($dateText, '.+')
        }
    }
    if ($match.Success) {
        $parsed = [datetime]::MinValue
        foreach ($format in @("dd MMM yyyy","d MMM yyyy","dd MMMM yyyy","d MMMM yyyy")) {
            if ([datetime]::TryParseExact($match.Value, $format, [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::AssumeLocal, [ref]$parsed)) {
                return $parsed
            }
        }
    }
    return [datetime]::MaxValue
}

function Get-Sha1Hex([string]$Value) {
    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
        return ([System.BitConverter]::ToString($sha1.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    } finally {
        $sha1.Dispose()
    }
}

function Save-Image([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) { return $null }
    $uri = [uri]$Url
    $ext = [System.IO.Path]::GetExtension($uri.AbsolutePath)
    if ([string]::IsNullOrWhiteSpace($ext)) { $ext = ".img" }
    $fileName = "{0}{1}" -f (Get-Sha1Hex $Url), $ext.ToLowerInvariant()
    $destination = Join-Path $imageRoot $fileName
    if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) {
        Download-WebFile -Url $Url -Destination $destination
    }
    return "cache/images/{0}" -f $fileName
}

function Save-QrCode([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) { return $null }

    $fileName = "{0}.png" -f (Get-Sha1Hex $Url)
    $destination = Join-Path $qrRoot $fileName
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        return "cache/qr/{0}" -f $fileName
    }

    $providers = @(
        ("https://api.qrserver.com/v1/create-qr-code/?size=220x220&margin=0&data={0}" -f [System.Uri]::EscapeDataString($Url)),
        ("https://quickchart.io/qr?size=220&margin=0&text={0}" -f [System.Uri]::EscapeDataString($Url))
    )

    foreach ($providerUrl in $providers) {
        try {
            Download-WebFile -Url $providerUrl -Destination $destination
            if (Test-Path -LiteralPath $destination -PathType Leaf) {
                return "cache/qr/{0}" -f $fileName
            }
        } catch {
            if (Test-Path -LiteralPath $destination -PathType Leaf) {
                Remove-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
            }
        }
    }

    return $null
}

function Get-BestImageUrl([string]$Html) {
    foreach ($pattern in @('(?is)\sdata-srcset="([^"]+)"','(?is)\ssrcset="([^"]+)"','(?is)\sdata-src="([^"]+)"','(?is)\ssrc="([^"]+)"')) {
        $match = [regex]::Match($Html, $pattern)
        if (-not $match.Success) { continue }
        $value = $match.Groups[1].Value.Trim()
        if ($pattern -match 'srcset') {
            $candidates = foreach ($entry in $value.Split(",")) {
                $parts = ($entry.Trim() -split '\s+')
                [pscustomobject]@{ Url = $parts[0]; Width = if ($parts.Count -gt 1 -and $parts[1] -match '^(\d+)w$') { [int]$Matches[1] } else { 0 } }
            }
            $best = $candidates | Sort-Object Width -Descending | Select-Object -First 1
            if ($best) { return Get-AbsoluteUrl $best.Url }
        } else {
            return Get-AbsoluteUrl $value
        }
    }
    return $null
}

function Get-CardLink([string]$Html) {
    $permalinkMatch = [regex]::Match($Html, '(?is)<a[^>]+class="[^"]*\bc-event-card__permalink\b[^"]*"[^>]+href="([^"]+)"')
    if ($permalinkMatch.Success) {
        return Get-AbsoluteUrl $permalinkMatch.Groups[1].Value
    }

    $matches = [regex]::Matches($Html, '(?is)<a[^>]+href="([^"]+)"[^>]*>')
    $urls = @()
    foreach ($match in $matches) {
        $url = Get-AbsoluteUrl $match.Groups[1].Value
        if (-not [string]::IsNullOrWhiteSpace($url)) {
            $urls += $url
        }
    }
    foreach ($url in $urls) {
        if ($url -notmatch '\?type=' -and $url -match '/whats-on/') {
            return $url
        }
    }
    return ($urls | Select-Object -First 1)
}

function Get-CardBlocks([string]$SectionHtml) {
    $containerMatches = [regex]::Matches($SectionHtml, '(?is)<div[^>]+class="[^"]*\bc-col-events-block__event-card-container\b[^"]*"[^>]*>')
    if ($containerMatches.Count -gt 0) {
        $blocks = New-Object System.Collections.Generic.List[string]
        for ($index = 0; $index -lt $containerMatches.Count; $index++) {
            $start = $containerMatches[$index].Index
            $end = if ($index + 1 -lt $containerMatches.Count) { $containerMatches[$index + 1].Index } else { $SectionHtml.Length }
            $blocks.Add($SectionHtml.Substring($start, $end - $start))
        }
        return @($blocks)
    }

    return @([regex]::Matches($SectionHtml, '(?is)<a\b[^>]*>.*?<h3[^>]*>.*?</h3>.*?</a>') | ForEach-Object { $_.Value })
}

function Get-EventDetails([string]$Url) {
    if ([string]::IsNullOrWhiteSpace($Url)) { return $null }
    if ($detailCache.ContainsKey($Url)) { return $detailCache[$Url] }
    try {
        $content = Get-WebContent -Url $Url
        $lines = Split-Lines (Convert-ToPlainText $content)
        $dateText = $null
        $startTime = $null
        $cost = $null
        foreach ($line in $lines) {
            $summary = [regex]::Match($line, '(?<date>(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}\s+[A-Za-z]{3,9})(?:,\s*(?<time>\d{1,2}(?::|\.)?\d{0,2}\s*(?:am|pm)))?(?:,\s*Tickets?\s*(?<price>[^,]+))?', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            if ($summary.Success) {
                if (-not $dateText) {
                    $parsed = [datetime]::MinValue
                    if ([datetime]::TryParse(("{0} {1}" -f $summary.Groups["date"].Value, (Get-Date).Year), [ref]$parsed)) { $dateText = $parsed.ToString("dd MMM yyyy") }
                }
                if (-not $startTime -and $summary.Groups["time"].Success) { $startTime = (Normalize-Whitespace ($summary.Groups["time"].Value.ToLowerInvariant())).Replace(".", ":") }
                if (-not $cost -and $summary.Groups["price"].Success) { $cost = Normalize-CurrencyText $summary.Groups["price"].Value }
                break
            }
        }
        if (-not $dateText) { $dateText = Get-DateTextFromLines $lines }
        if (-not $startTime) { $startTime = Get-StartTimeFromLines $lines }
        if (-not $cost) { $cost = Get-CostFromLines $lines @() }
        if (($content -match '"startDate"\s*:\s*"([^"]+)"') -and (-not $dateText -or -not $startTime)) {
            $parsed = [datetime]::MinValue
            if ([datetime]::TryParse($Matches[1], [ref]$parsed)) {
                if (-not $dateText) { $dateText = $parsed.ToString("dd MMM yyyy") }
                if (-not $startTime -and $Matches[1] -match 'T(?!00:00)(?!00:00:00)\d{2}:\d{2}') { $startTime = $parsed.ToString("h:mmtt").ToLowerInvariant().Replace(":00", "") }
            }
        }
        if (-not $cost -and (($content -match '"price"\s*:\s*"?(0|[0-9]+(?:\.[0-9]{2})?)"?' ) -or ($content -match '"lowPrice"\s*:\s*"?(0|[0-9]+(?:\.[0-9]{2})?)"?'))) {
            $cost = if ($Matches[1] -eq "0") { "Free" } else { ("{0}{1}" -f [char]0x00A3, $Matches[1].TrimEnd("0").TrimEnd(".")) }
        }
        $detailCache[$Url] = [pscustomobject]@{ dateText = $dateText; startTime = $startTime; cost = $cost }
    } catch {
        $detailCache[$Url] = $null
    }
    return $detailCache[$Url]
}

Ensure-Directory $outputRoot
Reset-Directory $imageRoot
Reset-Directory $qrRoot

$sourceContent = Get-WebContent -Url $sourceUrl

$results = New-Object System.Collections.Generic.List[object]
$sections = [regex]::Matches($sourceContent, '(?is)<h2[^>]*>(.*?)</h2>')
for ($i = 0; $i -lt $sections.Count; $i++) {
    $sectionTitle = Normalize-Whitespace $sections[$i].Groups[1].Value
    $sectionTitle = $sectionTitle.Replace("&", "and")
    if ($allowedSections -notcontains $sectionTitle) { continue }
    $start = $sections[$i].Index + $sections[$i].Length
    $end = if ($i + 1 -lt $sections.Count) { $sections[$i + 1].Index } else { $sourceContent.Length }
    $sectionHtml = $sourceContent.Substring($start, $end - $start)
    $cards = Get-CardBlocks -SectionHtml $sectionHtml
    foreach ($card in $cards) {
        $titleMatch = [regex]::Match($card, '(?is)<h3[^>]*>(.*?)</h3>')
        if (-not $titleMatch.Success) { continue }
        $title = Normalize-Whitespace $titleMatch.Groups[1].Value
        if (-not $title) { continue }
        $eventLink = Get-CardLink $card
        $imageUrl = Get-BestImageUrl $card
        $lines = Split-Lines (Convert-ToPlainText $card)
        $badges = @("Free","Sold Out","Limited Availability") | Where-Object { $lines -contains $_ }
        $listingDateText = Get-DateTextFromLines $lines
        $dateText = $listingDateText
        $startTime = Get-StartTimeFromLines $lines
        $cost = Get-CostFromLines $lines $badges
        if ($eventLink) {
            $details = Get-EventDetails $eventLink
            if ($details) {
                $detailFieldsAreTrusted = $true
                if (-not $dateText -and $details.dateText) {
                    $dateText = $details.dateText
                } elseif ($dateText -and $details.dateText) {
                    $listingDateKey = Get-DateSortKey $dateText
                    $detailDateKey = Get-DateSortKey $details.dateText
                    $datesConflict = $false

                    if ($listingDateKey -ne [datetime]::MaxValue -and $detailDateKey -ne [datetime]::MaxValue) {
                        $datesConflict = $listingDateKey -ne $detailDateKey
                    } else {
                        $datesConflict = (Normalize-Whitespace $dateText) -ne (Normalize-Whitespace $details.dateText)
                    }

                    if ($datesConflict) {
                        Write-Host ("Keeping listing date '{0}' for '{1}' instead of conflicting detail-page date '{2}' from {3}" -f $dateText, $title, $details.dateText, $eventLink)
                        $detailFieldsAreTrusted = $false
                    }
                }

                if ($detailFieldsAreTrusted) {
                    if ($details.startTime) { $startTime = $details.startTime }
                    if ($details.cost) { $cost = $details.cost }
                }
            }
        }
        $titleKey = Normalize-CompareText $title
        $meta = foreach ($line in $lines) {
            if ($line -in @($sectionTitle,$title,"More","Arts Centre Washington",$dateText,$startTime,$cost)) { continue }
            if ($badges -contains $line) { continue }
            $lineKey = Normalize-CompareText $line
            if ($line -match '^(View all|Part of|Book now|Book tickets|Register your interest)\b') { continue }
            if ($lineKey -and ($lineKey -eq $titleKey -or $lineKey.Contains($titleKey) -or $titleKey.Contains($lineKey))) { continue }
            $line
        }
        try { $imageLocal = if ($imageUrl) { Save-Image $imageUrl } else { $null } } catch { $imageLocal = $null }
        try { $qrLocal = if ($eventLink) { Save-QrCode $eventLink } else { $null } } catch { $qrLocal = $null }
        $results.Add([pscustomobject]@{
            title = $title
            category = $sectionTitle
            isClass = $classCategories -contains $sectionTitle
            dateText = $dateText
            startTime = $startTime
            cost = $cost
            sortDate = (Get-DateSortKey $dateText).ToString("o")
            status = ($badges -join " | ")
            meta = @($meta | Select-Object -First 3)
            link = $eventLink
            image = $imageUrl
            imageLocal = $imageLocal
            qrLocal = $qrLocal
        })
    }
}

$items = @(
    $results |
    Group-Object { "{0}|{1}|{2}" -f $_.title, $_.category, $_.dateText } |
    ForEach-Object { $_.Group[0] } |
    Sort-Object @{ Expression = {
        try { [datetime]$_.sortDate } catch { [datetime]::MaxValue }
    } }, @{ Expression = { $_.title } }
)

if (-not $items.Count) {
    throw "The live page was fetched, but no event cards were parsed."
}

$payload = [pscustomobject]@{
    fetchedAt = (Get-Date).ToString("o")
    includeClasses = $true
    sourceUrl = $sourceUrl
    total = $items.Count
    items = $items
    lastError = $null
}

$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $outputRoot "events.json") -Encoding UTF8
Write-Host ("Wrote {0} events to {1}" -f $items.Count, (Join-Path $outputRoot "events.json"))
