@echo off
echo Building Cache Eraser single exe...
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :error
python -m PyInstaller CacheEraser.spec
if errorlevel 1 goto :error
echo Done. Executable created: dist\CacheEraser.exe
pause
exit /b 0

:error
echo Build failed.
pause
exit /b 1
