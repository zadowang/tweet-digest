@echo off
cd /d %~dp0
echo ??????????...
echo.
echo ????: http://localhost:8080
echo ????: ???????
echo.
for /f "tokens=2 delims=:" %%i in ('python -c "import socket;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(('8.8.8.8',80));print(s.getsockname()[0]);s.close()"') do echo ???IP: %%i:8080
echo.
python server.py
pause
