@echo off
title DNH Care - Scroll Cinematic Demo
cd /d "%~dp0"
echo Serving DNH Care at http://localhost:8347
start "" http://localhost:8347
python -m http.server 8347
