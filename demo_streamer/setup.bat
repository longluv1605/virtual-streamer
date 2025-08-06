@echo off
echo Starting Virtual Streamer System Setup...

REM Install requirements
echo Installing Python dependencies...
pip install -r requirements.txt

REM Create necessary directories
echo Creating output directories...
if not exist "outputs\audio" mkdir outputs\audio
if not exist "outputs\videos" mkdir outputs\videos
if not exist "static" mkdir static

REM Create environment file template
echo Creating environment file template...
(
echo # API Keys (replace with your actual keys^)
echo OPENAI_API_KEY=your_openai_api_key_here
echo GEMINI_API_KEY=your_gemini_api_key_here
echo.
echo # Database URL (SQLite default^)
echo DATABASE_URL=sqlite:///./virtual_streamer.db
echo.
echo # Server settings
echo HOST=0.0.0.0
echo PORT=8000
) > .env

echo Setup completed!
echo.
echo Next steps:
echo 1. Edit .env file and add your API keys
echo 2. Ensure MuseTalk is set up in ..\MuseTalk\
echo 3. Run: python main.py
echo 4. Open: http://localhost:8000
echo.
echo For detailed instructions, see README.md

pause
