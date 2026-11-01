@echo off
rem Play Horizon offline: no Microsoft account, no sign-in, nothing to log into.
rem The prepared 26.3 resources live beside the game in .local\horizon-client\26.3.
setlocal
set "GAME=%~dp0horizon-windows-x64"
if not exist "%GAME%\horizon-client.exe" (
  echo Cannot find "%GAME%\horizon-client.exe".
  pause
  exit /b 1
)
set "HORIZON_HOME=%GAME%"
rem Saves, options.txt, packs and mods stay in the game folder.
cd /d "%GAME%"
rem Exclusive fullscreen crashes the game at startup on laptops where Windows refuses the mode
rem switch (winit panics on it, window.rs:744), and being saved it crashes every start after,
rem before the menu where it could be turned off. Borderless fullscreen looks the same.
findstr /b /c:"exclusiveFullscreen:true" options.txt >nul 2>nul && powershell -NoProfile -Command "$f='%GAME%\options.txt'; [IO.File]::WriteAllText($f, ([IO.File]::ReadAllText($f) -replace '(?m)^exclusiveFullscreen:true','exclusiveFullscreen:false'))"
rem --name picks the offline name; without it the game keeps one it generates once.
"%GAME%\horizon-client.exe" --resources ".local/horizon-client/26.3" %*
