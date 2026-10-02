
$root = "C:\FraudLab\fraud-lab-main"

if (Test-Path "$root\frontend\static\css\exhibition-tv.backup.css") {
    Copy-Item "$root\frontend\static\css\exhibition-tv.backup.css" `
              "$root\frontend\static\css\exhibition-tv.css" -Force
}

Write-Host "Rollback completed."
