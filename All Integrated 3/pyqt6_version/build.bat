@echo off
REM Build script for GoLive Studio
setlocal enabledelayedexpansion

REM Configuration
set APP_NAME=GoLiveStudio
set VERSION=1.0.0
set PYTHON=python
set PYINSTALLER=pyinstaller

REM Create output directory
if not exist "dist" mkdir dist

REM Check if PyInstaller is installed
%PYTHON% -m pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing PyInstaller...
    %PYTHON% -m pip install --upgrade pyinstaller
)

REM Install required packages
echo Installing required packages...
%PYTHON% -m pip install -r requirements.txt

REM Download FFmpeg if not present
if not exist "third_party\ffmpeg\bin\ffmpeg.exe" (
    echo Downloading FFmpeg...
    if not exist "third_party\ffmpeg\bin" mkdir "third_party\ffmpeg\bin"
    
    powershell -Command "Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'ffmpeg.zip'"
    if exist "ffmpeg.zip" (
        powershell -Command "Expand-Archive -Path 'ffmpeg.zip' -DestinationPath 'ffmpeg_temp' -Force"
        xcopy /E /Y "ffmpeg_temp\ffmpeg-*-essentials_build\bin\*.*" "third_party\ffmpeg\bin\"
        rmdir /S /Q ffmpeg_temp
        del ffmpeg.zip
        echo FFmpeg downloaded and extracted to third_party\ffmpeg\bin
    ) else (
        echo Failed to download FFmpeg. Please download it manually and place in third_party\ffmpeg\bin
    )
)

REM Build the application
echo Building %APP_NAME%...
%PYINSTALLER% --clean --noconfirm golive.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build completed successfully!
    echo.
    echo The built application is in the 'dist' folder.
    echo.
    echo To run the application:
    echo   dist\%APP_NAME%\%APP_NAME%.exe
) else (
    echo.
    echo Build failed with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

endlocal
