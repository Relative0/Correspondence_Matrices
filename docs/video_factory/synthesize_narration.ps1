param(
    [Parameter(Mandatory = $true)]
    [string]$InputJson
)

$ErrorActionPreference = 'Stop'
$contract = Get-Content -Raw -LiteralPath $InputJson | ConvertFrom-Json

Add-Type -AssemblyName System.Speech
$synth = [System.Speech.Synthesis.SpeechSynthesizer]::new()
try {
    $synth.SelectVoice([string]$contract.voice)
    $synth.Rate = [int]$contract.rate
    $synth.Volume = [int]$contract.volume
    $format = [System.Speech.AudioFormat.SpeechAudioFormatInfo]::new(
        [int]$contract.sample_rate,
        [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,
        [System.Speech.AudioFormat.AudioChannel]::Mono
    )
    foreach ($cue in $contract.cues) {
        if ($null -ne $cue.rate) {
            $synth.Rate = [int]$cue.rate
        }
        else {
            $synth.Rate = [int]$contract.rate
        }
        $target = [System.IO.Path]::GetFullPath([string]$cue.output)
        $parent = [System.IO.Path]::GetDirectoryName($target)
        [System.IO.Directory]::CreateDirectory($parent) | Out-Null
        $synth.SetOutputToWaveFile($target, $format)
        $synth.Speak([string]$cue.text)
        $synth.SetOutputToNull()
        $item = Get-Item -LiteralPath $target
        Write-Output ("synthesized {0} {1}" -f $cue.cue_id, $item.Length)
    }
}
finally {
    $synth.Dispose()
}
