# הרצה מהירה ב-Windows PowerShell.
# שימוש:  .\run.ps1            → מפעיל את אפליקציית הניתוח (Streamlit)
#         .\run.ps1 -Setup    → התקנה ראשונית (סביבה + חבילות)
#         .\run.ps1 -Digest   → בונה ופותח את אתר הדייג'סט השבועי (site/index.html)

param([switch]$Setup, [switch]$Digest)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if ($Setup) {
    Write-Host "יוצר סביבה וירטואלית…" -ForegroundColor Cyan
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    Write-Host "התקנה הושלמה. ערוך את .env (העתק מ-.env.example) והרץ: .\run.ps1" -ForegroundColor Green
    exit
}

if ($Digest) {
    if (Test-Path ".\.venv\Scripts\Activate.ps1") { .\.venv\Scripts\Activate.ps1 }
    $env:PYTHONUTF8 = "1"
    python build_site.py
    Start-Process (Resolve-Path ".\site\index.html")
    Write-Host "אתר הדייג'סט נפתח בדפדפן." -ForegroundColor Green
    exit
}

if (Test-Path ".\.venv\Scripts\Activate.ps1") { .\.venv\Scripts\Activate.ps1 }
if (-not (Test-Path ".\.env")) {
    Write-Host "אזהרה: אין קובץ .env. העתק מ-.env.example ומלא ANTHROPIC_API_KEY." -ForegroundColor Yellow
}
streamlit run streamlit_app.py
