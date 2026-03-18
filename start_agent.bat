@echo off
setlocal
cd /d %~dp0..
powershell -ExecutionPolicy Bypass -File .\scripts\start_easy.ps1
