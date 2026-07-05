# PowerShell script to silently install Google Cloud SDK on Windows
$installerPath = "$env:Temp\GoogleCloudSDKInstaller.exe"

Write-Host "Downloading Google Cloud SDK Installer..."
$webClient = New-Object Net.WebClient
$webClient.DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", $installerPath)

Write-Host "Installing silently (this may take a couple of minutes)..."
$process = Start-Process -FilePath $installerPath -ArgumentList "/S" -Wait -PassThru

if ($process.ExitCode -eq 0) {
    Write-Host "Installation completed successfully."
} else {
    Write-Warning "Installation finished with exit code $($process.ExitCode)."
}

# Scan common installation paths to find the binary path
$pathsToSearch = @(
    "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin",
    "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin",
    "C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin"
)

$foundPath = $null
foreach ($path in $pathsToSearch) {
    if (Test-Path "$path\gcloud.cmd") {
        $foundPath = $path
        break
    }
}

if ($foundPath) {
    Write-Host "Found gcloud binary at: $foundPath"
    # Output path update instruction
    Write-Host "To use, run: `$env:PATH = '$foundPath;' + `$env:PATH"
} else {
    Write-Warning "Could not find gcloud binary in standard locations. Please check your AppData or ProgramFiles directory."
}
