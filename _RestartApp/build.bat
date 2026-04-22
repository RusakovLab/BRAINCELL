@echo off

dotnet msbuild RestartApp.sln -t:Restore /t:Rebuild /p:Configuration=Release;Platform="Any CPU"

echo.
pause
