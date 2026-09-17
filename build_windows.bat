@echo off
REM ============================================================
REM  ApexVault — build both Windows .exe files locally
REM  Run this from the repo root (where this file lives):
REM      build_windows.bat
REM
REM  Requirements (install once):
REM      - Python 3.11  (add to PATH during install)
REM      - Rust toolchain:  https://rustup.rs
REM      - Visual Studio Build Tools (C++ workload) for dlib
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo   ApexVault builder
echo ============================================================

where python >nul 2>nul || (echo [ERROR] python not found in PATH & pause & exit /b 1)
where cargo  >nul 2>nul || (echo [ERROR] cargo (Rust) not found. Install from https://rustup.rs & pause & exit /b 1)

echo.
echo [1/4] Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install pyinstaller PyQt6 pywebview cryptography pywin32 opencv-python numpy
python -m pip install dlib face-recognition face-recognition-models
if errorlevel 1 echo [WARN] A dependency failed to install — check the log above.

REM ---------- ApexVault-Python ----------
echo.
echo [2/4] Building ApexVault-Python (PyQt6 desktop)...
pushd ApexVault-Python
    echo   - compiling Rust crypto core...
    pushd apex_crypto
        cargo build --release || (echo [ERROR] cargo build failed & popd & popd & pause & exit /b 1)
    popd
    for /f "delims=" %%f in ('dir /b /s "apex_crypto\target\release\apex_crypto.dll"') do copy /y "%%f" "apex_crypto.pyd" >nul
    echo   - running PyInstaller...
    pyinstaller build.spec --noconfirm --clean || (echo [ERROR] PyInstaller failed & popd & pause & exit /b 1)
    echo   - done: ApexVault-Python\dist\ApexVault-Python.exe
popd

REM ---------- ApexVault-Web ----------
echo.
echo [3/4] Building ApexVault-Web (HTML/CSS + pywebview)...
pushd ApexVault-Web
    echo   - compiling Rust crypto core...
    pushd apex_crypto
        cargo build --release || (echo [ERROR] cargo build failed & popd & popd & pause & exit /b 1)
    popd
    for /f "delims=" %%f in ('dir /b /s "apex_crypto\target\release\apex_crypto.dll"') do copy /y "%%f" "apex_crypto.pyd" >nul
    echo   - running PyInstaller...
    pyinstaller build.spec --noconfirm --clean || (echo [ERROR] PyInstaller failed & popd & pause & exit /b 1)
    echo   - done: ApexVault-Web\dist\ApexVault-Web.exe
popd

echo.
echo [4/4] All done!
echo   ApexVault-Python\dist\ApexVault-Python.exe
echo   ApexVault-Web\dist\ApexVault-Web.exe
echo.
echo Upload these two files to your GitHub Release.
pause