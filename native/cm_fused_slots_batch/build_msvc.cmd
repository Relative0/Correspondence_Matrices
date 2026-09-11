@echo off
call "%~1" >nul
if errorlevel 1 exit /b %errorlevel%
cl.exe /nologo /O2 /W4 /LD "%~2" /Fo:"%~3\fused_slot_executor_batch.obj" /link /OUT:"%~3\cm_fused_slots_batch.dll" /IMPLIB:"%~3\cm_fused_slots_batch.lib" /PDB:"%~3\cm_fused_slots_batch.pdb"
exit /b %errorlevel%
