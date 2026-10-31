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
rem --name picks the offline name; without it the game keeps one it generates once.
"%GAME%\horizon-client.exe" --resources ".local/horizon-client/26.3" %*
