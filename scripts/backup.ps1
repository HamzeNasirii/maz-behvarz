$date = Get-Date -Format "yyyy-MM-dd_HH-mm"
$backupDir = "D:\Backups\Behvarzan\$date"
New-Item -ItemType Directory -Path $backupDir -Force

# بک‌آپ دیتابیس
Copy-Item "D:\PycharmProjects\Behvarzan_site\db.sqlite3" "$backupDir\db.sqlite3"

# بک‌آپ فایل‌های آپلودی (مدارک، عکس‌ها)
Copy-Item -Recurse "D:\PycharmProjects\Behvarzan_site\media" "$backupDir\media"

Write-Host "بک‌آپ کامل شد در: $backupDir"