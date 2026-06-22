@echo off
chcp 65001 >nul
:: =============================================================================
:: Запуск Панели Администратора NoteBuns (Smart Synchronizer)
:: =============================================================================

echo [INFO] Проверка библиотек (customtkinter, paramiko, blake3)...
pip install customtkinter paramiko blake3 >nul 2>&1

echo [INFO] Запуск графического интерфейса...
start pythonw main.py
exit
