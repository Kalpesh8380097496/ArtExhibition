# 🎨 ArtExhibit — AI-Powered Art Exhibition Platform

A stunning, full-stack art exhibition platform built with **Django + SQLite + HTML/CSS/JS** and powered by **Claude AI (ARIA)**.

---

## 🌟 Features

### Frontend (HTML + CSS + JS)
- Luxury editorial design with Cormorant Garamond & Bebas Neue fonts
- Masonry gallery layout with hover animations
- Responsive design for all screen sizes
- Smooth transitions and micro-interactions
- ARIA floating chat widget (bottom-right)

### Backend (Django + Python)
- Full CRUD for Artworks, Artists, Exhibitions
- User authentication (login, register, logout)
- Search & filter (by medium, category, keyword)
- Like & comment system
- View count tracking
- Contact form

### Database (SQLite)
Tables:
- `gallery_artwork` — Artworks with metadata
- `gallery_artist` — Artist profiles
- `gallery_category` — Art categories
- `gallery_exhibition` — Exhibitions
- `gallery_like` — User likes
- `gallery_comment` — Comments
- `gallery_contactmessage` — Contact form submissions

### AI Features (Claude API)
- **ARIA Chat Widget** — AI art guide available on every page
- **AI Artwork Analysis** — Claude generates critic-style analysis of any artwork
- **Personalized Recommendations** — AI recommends artworks based on your taste

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Add Your API Key (for AI features)
Edit `artexhibit/settings.py`:
```python
ANTHROPIC_API_KEY = 'sk-ant-your-real-key-here'
```

### 3. Setup Database
```bash
python manage.py makemigrations gallery
python manage.py migrate
python manage.py seed_data   # Load sample artists & artworks
```

### 4. Run the Server
```bash
python manage.py runserver
```

### 5. Open in Browser
- **Website:** http://127.0.0.1:8000
- **Admin:** http://127.0.0.1:8000/admin
- **Login:** admin / admin123

---

## 📁 Project Structure

```
artexhibit/
├── artexhibit/
│   ├── settings.py          # Configuration & API keys
│   ├── urls.py              # Main URL routing
│   └── wsgi.py
├── gallery/
│   ├── models.py            # Database models
│   ├── views.py             # Page logic + AI integration
│   ├── urls.py              # App URL patterns
│   ├── admin.py             # Django admin setup
│   ├── management/
│   │   └── commands/
│   │       └── seed_data.py # Sample data loader
│   └── templates/gallery/
│       ├── home.html        # Homepage with hero, featured works
│       ├── gallery.html     # Art grid with filters
│       ├── artwork_detail.html  # Single artwork + AI analysis
│       ├── artists.html     # Artist listing
│       ├── artist_detail.html   # Artist profile + portfolio
│       ├── exhibitions.html # Exhibition listing
│       ├── exhibition_detail.html
│       ├── contact.html     # Contact form
│       ├── login.html       # Sign in page
│       └── register.html    # Registration page
├── templates/
│   └── base.html            # Shared layout, nav, footer, ARIA widget
├── media/                   # Uploaded artwork images
├── requirements.txt
├── setup_and_run.sh
└── manage.py
```

---

## 🎨 Adding Artworks via Admin

1. Go to http://127.0.0.1:8000/admin
2. Login with **admin / admin123**
3. Add Artists → Add Categories → Add Artworks
4. Upload real artwork images for the best visual experience
5. Check "Is featured" to show on homepage

---

## 🤖 AI Integration

The AI (Claude API) powers 3 features:

### 1. ARIA Chat (every page)
- Floating widget bottom-right
- Conversational art guide
- Answers questions about art history, exhibitions, artists

### 2. Artwork Analysis (artwork detail page)
- Click "Generate ✦" button
- ARIA writes a 2-paragraph art critic analysis
- Covers technique, emotion, themes, significance

### 3. Art Recommender (homepage)
- Describe your art preferences
- ARIA matches artworks from the database
- Returns personalized suggestions with reasons

---

## 🔧 Customization

### Change Colors (base.html :root)
```css
--gold: #C9A84C;      /* Accent color */
--charcoal: #1A1A1A;  /* Dark backgrounds */
--cream: #F5F0E8;     /* Main background */
```

### Add Real Images
Place images in `media/artworks/` and set the path in admin.

### Deploy to Production
1. Set `DEBUG = False` in settings.py
2. Set a strong `SECRET_KEY`
3. Use PostgreSQL instead of SQLite
4. Configure `ALLOWED_HOSTS`
5. Run `python manage.py collectstatic`

---

## 📸 Pages Overview

| Page | URL | Description |
|------|-----|-------------|
| Home | / | Hero, featured works, AI recommender, exhibitions |
| Gallery | /gallery/ | All artworks with search & filters |
| Artwork | /artwork/1/ | Detail view with AI analysis & comments |
| Artists | /artists/ | Artist profiles grid |
| Artist | /artist/1/ | Portfolio page |
| Exhibitions | /exhibitions/ | All exhibitions |
| Contact | /contact/ | Contact form |
| Login | /login/ | Sign in |
| Register | /register/ | Create account |
| Admin | /admin/ | Django admin panel |

---

Built with ❤️ using Django, SQLite, HTML/CSS/JS, and Claude AI
