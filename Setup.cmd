@echo off
rem Build a playable Horizon offline folder from this repository, on this PC.
rem Everything it downloads is public: Horizon's release zip, Minecraft 26.3 from Mojang, and the
rem patched launcher attached to this repository's release. Reads: GUIDE.md
setlocal
cd /d "%~dp0"
set "ROOT=%~dp0"
set "REPO=https://github.com/hieudepzai14122007-ship-it/horizon-offline"

echo Horizon offline: setup
echo.

rem The patched launcher: small, and the one path that needs nothing else installed.
if exist "%ROOT%launcher\horizon-launcher.exe" goto have_launcher
echo [1/3] Downloading the patched launcher, 41 MB
if not exist "%ROOT%launcher" mkdir "%ROOT%launcher"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -Uri '%REPO%/releases/latest/download/horizon-launcher.exe' -OutFile '%ROOT%launcher\horizon-launcher.exe'"
if exist "%ROOT%launcher\horizon-launcher.exe" goto have_launcher
echo     Could not download it. Get it from %REPO%/releases/latest
exit /b 1

:have_launcher
rem From here on the folder is built directly, which needs Python and Java. Without them the
rem launcher does the same work itself, downloading Mojang's Java on its first Play.
where python >nul 2>nul
if errorlevel 1 goto launcher_only
if defined JAVA_HOME goto have_tools
where java >nul 2>nul
if errorlevel 1 goto launcher_only

:have_tools
if exist "%ROOT%horizon-windows-x64\horizon-client.exe" goto have_game
echo [2/3] Horizon nightly for Windows, 29 MB
python -c "import urllib.request;urllib.request.urlretrieve('https://github.com/horizon-rust/horizon/releases/download/nightly/horizon-windows-x64.zip','horizon-windows-x64.zip')"
if errorlevel 1 goto launcher_fallback
tar -xf horizon-windows-x64.zip
if errorlevel 1 goto launcher_fallback
del horizon-windows-x64.zip

:have_game
if exist "%ROOT%minecraft\versions\26.3\26.3.jar" goto have_minecraft
echo [3/3] Minecraft 26.3 from Mojang, about 650 MB
python fetch-minecraft.py minecraft --version 26.3
if errorlevel 1 goto launcher_fallback

:have_minecraft
if exist "%ROOT%horizon-windows-x64\.local\horizon-client\26.3\horizon-resources.json" goto done
echo     Preparing the game's resources, a few minutes
pushd horizon-windows-x64
.\horizon-prepare.exe --prepare --server-jar ..\minecraft\server.jar --minecraft-dir ..\minecraft --root .
if errorlevel 1 (popd & goto launcher_fallback)
.\horizon-prepare.exe sounds --minecraft-dir ..\minecraft --root .
popd

:done
echo.
echo Ready.
echo   Play-Horizon.cmd      the game, straight away
echo   Horizon-Launcher.cmd  the launcher window
exit /b 0

:launcher_only
echo.
echo No Python 3 or Java 25 here, so the folder stays as it is and the launcher builds it:
echo   double-click Horizon-Launcher.cmd, then Play.
echo It downloads Mojang's Java and Minecraft 26.3 itself, about 700 MB, ten minutes.
echo (For the direct route instead, install Python 3 and Java 25, then run this again.)
exit /b 0

:launcher_fallback
echo.
echo That step failed. Double-click Horizon-Launcher.cmd and press Play instead: it downloads
echo Java and Minecraft itself.
exit /b 0
