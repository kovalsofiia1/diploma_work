@echo off
echo Loading Visual Studio Build Tools environment...
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
echo.
echo Activating Python virtual environment...
call "C:\Users\skova6\Documents\angular projects\diploma_work\.venv311\Scripts\activate.bat"
echo.
echo Installing Python packages...
pip install -r requirements.txt
echo.
echo Installation complete!
pause
