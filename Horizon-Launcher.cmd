@echo off
rem Open the Horizon launcher window: the same launcher, rebuilt with the Microsoft owner gate off.
rem Its data (installed versions, prepared resources, settings) is the launcher-home folder here,
rem which is already installed and prepared; HORIZON_LAUNCHER_HOME is what points it there.
rem HORIZON_HOME keeps the game's own data (saves, options, telemetry) beside it too, where the
rem data-collection question is already answered as "send nothing".
setlocal
if not exist "%~dp0launcher\horizon-launcher.exe" (
  echo Cannot find "%~dp0launcher\horizon-launcher.exe".
  pause
  exit /b 1
)
set "HORIZON_LAUNCHER_HOME=%~dp0launcher-home"
set "HORIZON_HOME=%~dp0launcher-home\game"
rem The exclusive fullscreen crash fix (see Play-Horizon.cmd) for every game version the launcher
rem installed. A version it installs while open is patched the next time this starts.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix-fullscreen-crash.ps1" "%~dp0launcher-home\versions\*\horizon-client.exe"
rem Never let it replace itself with the official launcher: that one has the Microsoft gate back.
set "HORIZON_LAUNCHER_NO_SELF_UPDATE=1"
start "" "%~dp0launcher\horizon-launcher.exe" %*
