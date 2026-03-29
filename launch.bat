@echo off
title yt-dlp UI
cd /d "%~dp0"
call venv\Scripts\activate.bat
streamlit run app.py
if errorlevel 1 pause
