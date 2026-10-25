$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$videoDir = Join-Path $repoRoot "docs\video"
$sceneDir = Join-Path $videoDir "scenes"
$silentVideo = Join-Path $videoDir "call-screen-lab-demo-silent.mp4"
$finalVideo = Join-Path $videoDir "call-screen-lab-demo.mp4"
$publicVideo = Join-Path $repoRoot "web\public\call-screen-lab-demo.mp4"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $publicVideo) | Out-Null

$scenes = @(
    @{ File = "03-evaluation-top.png"; Duration = 7 },
    @{ File = "01-intro.png"; Duration = 10 },
    @{ File = "02-decision.png"; Duration = 11 },
    @{ File = "03-evaluation-top.png"; Duration = 10 },
    @{ File = "04-metrics.png"; Duration = 12 },
    @{ File = "05-errors.png"; Duration = 9 },
    @{ File = "06-rollout.png"; Duration = 9 }
)

$inputArgs = @("-y")
foreach ($scene in $scenes) {
    $inputArgs += @(
        "-loop", "1",
        "-framerate", "30",
        "-t", $scene.Duration.ToString(),
        "-i", (Join-Path $sceneDir $scene.File)
    )
}

$filters = @()
for ($index = 0; $index -lt $scenes.Count; $index++) {
    $filters += "[$index`:v]zoompan=z='min(zoom+0.00012,1.02)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1440x900:fps=30,format=yuv420p,setsar=1,setpts=PTS-STARTPTS[v$index]"
}
$videoInputs = (0..($scenes.Count - 1) | ForEach-Object { "[v$_]" }) -join ""
$filters += "${videoInputs}concat=n=$($scenes.Count):v=1:a=0[video]"
$filterGraph = $filters -join ";"

& ffmpeg @inputArgs `
    -f lavfi -t 68 -i "anullsrc=channel_layout=stereo:sample_rate=48000" `
    -filter_complex $filterGraph `
    -map "[video]" -map "$($scenes.Count):a" `
    -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p `
    -c:a aac -b:a 128k -shortest $silentVideo

if ($LASTEXITCODE -ne 0) {
    throw "FFmpeg could not assemble the scene video."
}

Push-Location $videoDir
try {
    $subtitleStyle = "FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H8008203F,BackColour=&H8008203F,BorderStyle=3,Outline=1,Shadow=0,MarginV=28,Alignment=2"
    & ffmpeg -y -i (Split-Path -Leaf $silentVideo) `
        -vf "subtitles=captions.srt:force_style='$subtitleStyle'" `
        -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p `
        -c:a copy (Split-Path -Leaf $finalVideo)
    if ($LASTEXITCODE -ne 0) {
        throw "FFmpeg could not burn the captions into the video."
    }
} finally {
    Pop-Location
}

Remove-Item -LiteralPath $silentVideo
Copy-Item -LiteralPath $finalVideo -Destination $publicVideo -Force
Get-Item -LiteralPath $finalVideo, $publicVideo | Select-Object FullName, Length
