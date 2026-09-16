param(
    [string]$ModelPath = 'F:\ShrimpCounterSystem\models\weights_color\best.pt',
    [string]$DataYamlPath = 'F:\ShrimpCounterSystem\config\data.yaml',
    [string]$PythonPath = 'F:\ShrimpCounterSystem\.venv\Scripts\python.exe',
    [string]$DisplayName = 'Custom YOLO26'
)

$ErrorActionPreference = 'Stop'

$FunctionName = 'pth-ultralytics-custom-yolo26'
$ContainerName = "nuclio-nuclio-$FunctionName"
$HelperName = 'cvat-custom-yolo-deployer'
$SamContainerName = 'nuclio-nuclio-pth-facebookresearch-sam-vit-b'
$NuclioVersion = '1.16.3'
$ScriptRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot '..\..\..\..')).Path
$StagePath = Join-Path $ScriptRoot '.deployment'

if (-not $StagePath.StartsWith($ScriptRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Unsafe deployment staging path: $StagePath"
}

foreach ($Path in @($ModelPath, $DataYamlPath, $PythonPath)) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required file was not found: $Path"
    }
}

if ([System.IO.Path]::GetExtension($ModelPath) -ne '.pt') {
    throw "ModelPath must point to an Ultralytics .pt model: $ModelPath"
}

$RestartSam = (docker inspect $SamContainerName --format '{{.State.Running}}' 2>$null) -eq 'true'

try {
    if ($RestartSam) {
        Write-Host 'Temporarily stopping SAM to reserve memory for the model build...'
        docker stop $SamContainerName | Out-Null
    }

    if (Test-Path -LiteralPath $StagePath) {
        Remove-Item -LiteralPath $StagePath -Recurse -Force
    }

    Copy-Item -LiteralPath (Join-Path $ScriptRoot 'nuclio') -Destination $StagePath -Recurse
    Copy-Item -LiteralPath $ModelPath -Destination (Join-Path $StagePath 'model.pt')
    Copy-Item -LiteralPath $DataYamlPath -Destination (Join-Path $StagePath 'data.yaml')

    $Labels = & $PythonPath (Join-Path $ScriptRoot 'prepare_deployment.py') `
        --function-yaml (Join-Path $StagePath 'function.yaml') `
        --data-yaml (Join-Path $StagePath 'data.yaml') `
        --display-name $DisplayName
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not prepare the model class configuration'
    }
    Write-Host "Classes: $Labels"

    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Desktop is not ready'
    }

    docker rm -f $HelperName 2>$null | Out-Null
    docker run -d --name $HelperName `
        -e DOCKER_BUILDKIT=1 `
        -v /var/run/docker.sock:/var/run/docker.sock `
        -v "${RepoRoot}:/workspace" `
        -w /workspace `
        alpine:3.22 tail -f /dev/null | Out-Null

    docker exec $HelperName apk add --no-cache ca-certificates docker-cli docker-cli-buildx wget
    docker exec $HelperName wget -q -O /tmp/nuctl `
        "https://github.com/nuclio/nuclio/releases/download/$NuclioVersion/nuctl-$NuclioVersion-linux-amd64"
    docker exec $HelperName chmod +x /tmp/nuctl

    $RelativeStage = $StagePath.Substring($RepoRoot.Length).TrimStart('\').Replace('\', '/')
    docker exec $HelperName /tmp/nuctl deploy `
        --project-name cvat `
        --namespace nuclio `
        --path $RelativeStage `
        --file "$RelativeStage/function.yaml" `
        --platform local
    if ($LASTEXITCODE -ne 0) {
        throw 'Nuclio deployment failed'
    }

    docker network connect cvat_cvat $ContainerName 2>$null
    if ($LASTEXITCODE -ne 0) {
        $Networks = docker inspect $ContainerName --format '{{json .NetworkSettings.Networks}}'
        if ($Networks -notmatch 'cvat_cvat') {
            throw 'Could not connect the detector to the CVAT network'
        }
    }

    $Ready = $false
    for ($Attempt = 0; $Attempt -lt 60; $Attempt++) {
        docker exec cvat_server python -c `
            "import requests, sys; response = requests.get('http://${ContainerName}:8082/ready', timeout=2); sys.exit(0 if response.status_code == 200 else 1)" `
            2>$null
        if ($LASTEXITCODE -eq 0) {
            $Ready = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $Ready) {
        throw 'The detector did not become healthy within 120 seconds'
    }

    Write-Host "Deployed '$DisplayName' as $FunctionName"
    Write-Host 'Refresh the CVAT annotation page to use the new detector.'
}
finally {
    docker rm -f $HelperName 2>$null | Out-Null
    if (Test-Path -LiteralPath $StagePath) {
        Remove-Item -LiteralPath $StagePath -Recurse -Force
    }
    if ($RestartSam) {
        docker start $SamContainerName 2>$null | Out-Null
    }
}
