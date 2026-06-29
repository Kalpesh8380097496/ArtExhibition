#!/bin/bash
echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║    ArtExhibit — Mac/Linux Setup          ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

echo "[1/5] Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[2/5] Installing dependencies..."
pip install -r requirements.txt

echo "[3/5] Running database migrations..."
python manage.py migrate

echo "[4/5] Creating media folders..."
mkdir -p media/artworks media/artists media/exhibitions

echo "[5/5] Seeding sample data..."
python manage.py seed_data

echo ""
echo "  ✅ Setup complete!"
echo ""
echo "  ┌─────────────────────────────────────────────┐"
echo "  │  🎨 ArtExhibit is ready!                    │"
echo "  │                                             │"
echo "  │  URL:   http://127.0.0.1:8000               │"
echo "  │  Admin: http://127.0.0.1:8000/admin         │"
echo "  │  Login: admin / admin123                    │"
echo "  │                                             │"
echo "  │  Press CTRL+C to stop                       │"
echo "  └─────────────────────────────────────────────┘"
echo ""

python manage.py runserver 127.0.0.1:8000
