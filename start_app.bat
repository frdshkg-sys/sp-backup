@echo off
chcp 65001 >nul
title CHUN KING 業務智慧表單伺服器
echo 正在啟動 CHUN KING 業務智慧表單伺服器...
start "" "http://localhost:8080"
python "%~dp0server.py"
pause
