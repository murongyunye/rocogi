@echo off
set "ROOT=%~dp0"
set "PY=%ROOT%..\..\.toolchain\python\cpython-3.12.16-windows-x86_64-none\python.exe"
"%PY%" "%ROOT%kernel\cli.py" %*
