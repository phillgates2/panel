@echo off
REM Android Build Script for Panel App
REM This script builds the Android application

echo ========================================
echo Panel Android Build Script
echo ========================================
echo.

cd /d "%~dp0android"

echo [1/4] Cleaning previous build...
call gradlew.bat clean
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Clean failed
    pause
    exit /b 1
)

echo [2/4] Running tests...
call gradlew.bat test
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Tests failed but continuing...
)

echo [3/4] Building debug APK...
call gradlew.bat assembleDebug
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Debug build failed
    pause
    exit /b 1
)

echo [4/4] Building release AAB...
call gradlew.bat bundleRelease
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Release build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Debug APK: app\build\outputs\apk\debug\app-debug.apk
echo Release AAB: app\build\outputs\bundle\release\app-release.aab
echo.
echo To install on device: gradlew.bat installDebug
echo.

pause