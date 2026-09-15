param(
    [Parameter(Mandatory = $true)][string]$TextPath,
    [Parameter(Mandatory = $true)][string]$WavePath,
    [string]$Voice = "Microsoft Zira Desktop",
    [ValidateRange(-10, 10)][int]$Rate = 0
)

$ErrorActionPreference = "Stop"
$text = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $TextPath))
$parent = Split-Path -Parent $WavePath
if (-not [System.IO.Directory]::Exists($parent)) {
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
}

# System.Speech can list the desktop voices in this environment but cannot select
# them. The underlying local Windows SAPI COM interface can, so use it directly.
$speaker = New-Object -ComObject SAPI.SpVoice
$selected = @($speaker.GetVoices() | Where-Object { $_.GetDescription() -like "$Voice*" }) | Select-Object -First 1
if ($null -eq $selected) {
    throw "The requested local voice '$Voice' is not available through Windows SAPI."
}
$stream = New-Object -ComObject SAPI.SpFileStream
try {
    $speaker.Voice = $selected
    $speaker.Rate = $Rate
    $speaker.Volume = 100
    $stream.Open($WavePath, 3, $false) # SSFMCreateForWrite
    $speaker.AudioOutputStream = $stream
    [void]$speaker.Speak($text)
}
finally {
    if ($null -ne $stream) {
        $stream.Close()
    }
}
