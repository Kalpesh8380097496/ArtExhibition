#!/bin/bash
# ============================================================
#  ArtExhibit — Complete Setup & Run Script
#  Run this script to get the full website working!
# ============================================================

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║        ArtExhibit Setup Script        ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# Step 1: Install dependencies
echo "📦 Installing Python dependencies..."
pip install django pillow anthropic --break-system-packages -q
pip install django pillow anthropic  # if above fails without --break-system-packages

# Step 2: Run database migrations
echo ""
echo "🗄️  Setting up database..."
python manage.py makemigrations gallery
python manage.py migrate

# Step 3: Create media directory
mkdir -p media/artworks media/artists media/exhibitions

# Step 4: Seed sample data
echo ""
echo "🌱 Seeding sample data..."
python manage.py seed_data

# Step 5: Collect static files (optional for production)
# python manage.py collectstatic --noinput

echo ""
echo "  ✅ Setup complete!"
echo ""
echo "  ┌──────────────────────────────────────────┐"
echo "  │  🎨 ArtExhibit is ready!                 │"
echo "  │                                          │"
echo "  │  Run: python manage.py runserver         │"
echo "  │  Open: http://127.0.0.1:8000             │"
echo "  │                                          │"
echo "  │  Admin: http://127.0.0.1:8000/admin      │"
echo "  │  User:  admin  Password: admin123        │"
echo "  │                                          │"
echo "  │  ⚠️  Add Anthropic API key in            │"
echo "  │      artexhibit/settings.py for AI!     │"
echo "  └──────────────────────────────────────────┘"
echo ""

# Start server
echo "🚀 Starting development server..."
python manage.py runserver
