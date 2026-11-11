@echo off
rem Shortcut so you can type "scripts\dev-db start" instead of the long PowerShell command.
rem "-ExecutionPolicy Bypass" applies to this one run only; no Windows setting is changed.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev-db.ps1" %*
