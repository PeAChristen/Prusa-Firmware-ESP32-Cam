@echo off
setlocal enabledelayedexpansion

rem ================= SETTINGS =================
rem Camera address. Use the IP address if the .local name does not resolve.
set "CAM=http://prusa-esp32-s3-cam.local"
rem Folder for downloaded photos (created next to this script)
set "DIR=%~dp0photos"
rem 1 = delete the file from the SD card after a successful download
set "DELETE=1"
rem Seconds between runs. 0 = run once and exit.
set "INTERVAL=0"
rem Basic Auth, if enabled on the camera. Example: set "AUTH=-u user:password"
set "AUTH="
rem ============================================

if not exist "%DIR%" mkdir "%DIR%"
set "LIST=%TEMP%\cam_files.txt"

:run
echo [%date% %time%] Getting file list from %CAM%
curl -sf --connect-timeout 10 --max-time 60 %AUTH% -o "%LIST%" "%CAM%/sd_files"
if errorlevel 1 (
  echo Could not get file list. Camera unreachable or busy.
  goto next
)

set /a NEW=0, SKIP=0, FAIL=0
for /f "usebackq delims=" %%f in ("%LIST%") do call :process "%%f"
echo Done: !NEW! new, !SKIP! already local, !FAIL! failed

:next
if %INTERVAL% GTR 0 (
  timeout /t %INTERVAL% /nobreak >nul
  goto run
)
goto :eof

:process
set "NAME=%~1"
set "FILE=%DIR%\%NAME%"

if exist "%FILE%" (
  set /a SKIP+=1
  exit /b
)

curl -sf --connect-timeout 10 --max-time 60 %AUTH% -o "%FILE%.part" "%CAM%/sd_download?file=%NAME%"
if errorlevel 1 (
  del "%FILE%.part" 2>nul
  echo FAILED: %NAME%
  set /a FAIL+=1
  exit /b
)

for %%A in ("%FILE%.part") do set "SIZE=%%~zA"
if "!SIZE!"=="0" (
  del "%FILE%.part" 2>nul
  echo EMPTY FILE: %NAME%
  set /a FAIL+=1
  exit /b
)

move /y "%FILE%.part" "%FILE%" >nul
echo Downloaded: %NAME% (!SIZE! bytes)
set /a NEW+=1

if "%DELETE%"=="1" curl -sf %AUTH% -X DELETE "%CAM%/sd_delete?file=%NAME%" >nul
exit /b