@echo off
call "%~1" >nul
if errorlevel 1 exit /b %errorlevel%
cl.exe /nologo /O2 /W4 /LD "%~2" /Fo:"%~3\fused_slot_executor.obj" /link /OUT:"%~3\cm_fused_slots.dll" /IMPLIB:"%~3\cm_fused_slots.lib" /PDB:"%~3\cm_fused_slots.pdb"
exit /b %errorlevel%
