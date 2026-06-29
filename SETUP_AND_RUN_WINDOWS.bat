@echo off
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║      ArtExhibit — Windows Setup          ║
echo  ╚══════════════════════════════════════════╝
echo.

echo [1/4] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Make sure Python is installed.
    pause
    exit /b 1
)

echo.
echo [2/4] Running database migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo ERROR: Migration failed.
    pause
    exit /b 1
)

echo.
echo [3/4] Creating media folders...
if not exist "media\artworks" mkdir media\artworks
if not exist "media\artists" mkdir media\artists
if not exist "media\exhibitions" mkdir media\exhibitions

echo.
echo [4/4] Seeding sample data...
python manage.py seed_data

echo.
echo  ✅ Setup complete!
echo.
echo  ┌─────────────────────────────────────────────┐
echo  │  🎨 ArtExhibit is ready to run!             │
echo  │                                             │
echo  │  Starting server at http://127.0.0.1:8000   │
echo  │  Admin Panel: http://127.0.0.1:8000/admin   │
echo  │  Username: admin  Password: admin123        │
echo  │                                             │
echo  │  Press CTRL+C to stop the server            │
echo  └─────────────────────────────────────────────┘
echo.

python manage.py runserver 127.0.0.1:8000
pause
