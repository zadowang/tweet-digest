cd /d "C:\Users\ming\Documents\Codex\2026-07-22\x\tweet-digest"
git pull
echo %date% %time% > trigger.txt
git add trigger.txt
git commit -m "Daily trigger %date%"
git push
