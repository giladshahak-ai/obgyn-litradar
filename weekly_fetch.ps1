# משיכה שבועית אוטומטית מ-PubMed (מופעל ע"י Windows Task Scheduler).
# מושך רק מאמרי "ערך גבוה" (RCT/מטא/הנחיות) מ-10 הימים האחרונים, ושומר ל-litradar.db.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# בחר Python: עדיף venv אם קיים, אחרת ה-Python הגלובלי
$py = "C:\Users\gilad\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if (Test-Path ".\.venv\Scripts\python.exe") { $py = ".\.venv\Scripts\python.exe" }

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path ".\fetch_log.txt" -Value "===== $stamp — ריצה שבועית =====" -Encoding utf8
& $py -m app.ingest_pubmed *>> ".\fetch_log.txt"
# בנייה מחדש של אתר הדייג'סט השבועי (site/index.html)
& $py build_site.py *>> ".\fetch_log.txt"
Add-Content -Path ".\fetch_log.txt" -Value "" -Encoding utf8
