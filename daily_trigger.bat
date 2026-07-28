@echo off
:: Only push between 18:00-18:59
set HOUR=%time:~0,2%
if %HOUR% NEQ 18 exit /b 0
cd /d "C:\Users\ming\Documents\Codex\2026-07-22\x\tweet-digest"
git pull
echo %date% %time% > trigger.txt
git add trigger.txt
git commit -m "Daily trigger %date%"
git push
echo Done - GitHub Actions will handle collection
