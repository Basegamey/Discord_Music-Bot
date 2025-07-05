@echo off
setlocal enabledelayedexpansion
set "FFMPEG_DIR=%~dp0ffmpeg"
set "FFMPEG_BIN=%FFMPEG_DIR%\bin"
if exist "%FFMPEG_BIN%\ffmpeg.exe" (
    goto set_env
)
echo Please do not close, the process may take a while.
set "URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
set "TMP_ZIP=%~dp0ffmpeg.zip"
powershell -Command "Invoke-WebRequest -Uri '%URL%' -OutFile '%TMP_ZIP%'"

if not exist "%TMP_ZIP%" (
    echo Error
    pause
    exit /b 1
)
echo loading...   Do not close.
powershell -Command "Expand-Archive -Path '%TMP_ZIP%' -DestinationPath '%~dp0' -Force"
for /d %%i in ("%~dp0ffmpeg-release-essentials*") do (
    move /Y "%%i" "%FFMPEG_DIR%"
)
del "%TMP_ZIP%"
:set_env
echo FFMPEG_PATH=%FFMPEG_BIN%\ffmpeg.exe > "%~dp0.env"
echo Done. Press a key to exit.
pause
