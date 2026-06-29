from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count
from django.contrib import messages
from django.conf import settings
from .models import Artwork, Artist, Category, Exhibition, Like, Comment, ContactMessage
import json
import urllib.request


def ai_chat(prompt, system="You are an expert art curator and critic."):
    try:
        api_key = settings.ANTHROPIC_API_KEY
        if api_key == 'your-anthropic-api-key-here':
            return "AI features require a valid Anthropic API key."
        data = json.dumps({"model": "claude-sonnet-4-20250514", "max_tokens": 1024,
            "system": system, "messages": [{"role": "user", "content": prompt}]}).encode('utf-8')
        req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=data,
            headers={'Content-Type': 'application/json', 'x-api-key': api_key, 'anthropic-version': '2023-06-01'})
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read())['content'][0]['text']
    except Exception as e:
        return f"AI unavailable: {str(e)}"


def home(request):
    context = {
        'featured_artworks': Artwork.objects.filter(is_featured=True)[:6],
        'recent_artworks': Artwork.objects.all()[:12],
        'artists': Artist.objects.annotate(work_count=Count('artwork')).order_by('-work_count')[:6],
        'exhibitions': Exhibition.objects.filter(status='active')[:3],
        'categories': Category.objects.all(),
        'total_artworks': Artwork.objects.count(),
        'total_artists': Artist.objects.count(),
        'total_exhibitions': Exhibition.objects.count(),
    }
    return render(request, 'gallery/home.html', context)


def gallery_view(request):
    artworks = Artwork.objects.all()
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    medium = request.GET.get('medium', '')
    sort = request.GET.get('sort', '-created_at')
    if search:
        artworks = artworks.filter(Q(title__icontains=search)|Q(artist__name__icontains=search)|Q(description__icontains=search))
    if category:
        artworks = artworks.filter(category__slug=category)
    if medium:
        artworks = artworks.filter(medium=medium)
    if sort in ['-created_at','created_at','-view_count','title','-year_created']:
        artworks = artworks.order_by(sort)
    return render(request, 'gallery/gallery.html', {
        'artworks': artworks, 'categories': Category.objects.all(),
        'search': search, 'selected_category': category,
        'selected_medium': medium, 'selected_sort': sort,
        'medium_choices': Artwork.MEDIUM_CHOICES,
    })


def artwork_detail(request, pk):
    artwork = get_object_or_404(Artwork, pk=pk)
    artwork.view_count += 1
    artwork.save()
    user_liked = False
    if request.user.is_authenticated:
        user_liked = Like.objects.filter(user=request.user, artwork=artwork).exists()
    return render(request, 'gallery/artwork_detail.html', {
        'artwork': artwork,
        'related': Artwork.objects.filter(Q(category=artwork.category)|Q(artist=artwork.artist)).exclude(pk=pk)[:4],
        'comments': artwork.comment_set.all(),
        'user_liked': user_liked, 'like_count': artwork.like_count(),
    })


def artist_list(request):
    artists = Artist.objects.annotate(work_count=Count('artwork')).order_by('-work_count')
    return render(request, 'gallery/artists.html', {'artists': artists})


def artist_detail(request, pk):
    artist = get_object_or_404(Artist, pk=pk)
    return render(request, 'gallery/artist_detail.html', {
        'artist': artist, 'artworks': Artwork.objects.filter(artist=artist)
    })


def exhibitions_view(request):
    return render(request, 'gallery/exhibitions.html', {'exhibitions': Exhibition.objects.all().order_by('-start_date')})


def exhibition_detail(request, pk):
    exhibition = get_object_or_404(Exhibition, pk=pk)
    return render(request, 'gallery/exhibition_detail.html', {
        'exhibition': exhibition, 'artworks': Artwork.objects.filter(exhibition=exhibition)
    })


def contact_view(request):
    if request.method == 'POST':
        ContactMessage.objects.create(
            name=request.POST.get('name'), email=request.POST.get('email'),
            subject=request.POST.get('subject'), message=request.POST.get('message'),
        )
        messages.success(request, 'Message sent successfully!')
        return redirect('contact')
    return render(request, 'gallery/contact.html')


def send_sms_alert(message_body):
    """SMS alert bhejo Twilio se — login hone par"""
    try:
        if not settings.SMS_ALERTS_ENABLED:
            return False
        if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN,
                    settings.TWILIO_PHONE_NUMBER, settings.ADMIN_PHONE_NUMBER]):
            return False
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message_body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=settings.ADMIN_PHONE_NUMBER
        )
        return True
    except Exception as e:
        print(f"SMS Error: {e}")
        return False


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)

            # ── SMS ALERT BHEJO ──
            from django.utils import timezone
            import datetime
            now = timezone.localtime(timezone.now())
            time_str = now.strftime("%d %b %Y, %I:%M %p")

            if user.is_superuser:
                role = "ADMIN"
            else:
                try:
                    Artist.objects.get(user=user)
                    role = "ARTIST"
                except Artist.DoesNotExist:
                    role = "USER"

            sms_msg = (
                f"🔔 ArtExhibit Login Alert!\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 User: {user.username}\n"
                f"📧 Email: {user.email or 'N/A'}\n"
                f"🎭 Role: {role}\n"
                f"🕐 Time: {time_str}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"ArtExhibit Security"
            )
            send_sms_alert(sms_msg)

            # Redirect based on role
            if user.is_superuser:
                return redirect('admin_dashboard')
            try:
                Artist.objects.get(user=user)
                return redirect('artist_dashboard')
            except Artist.DoesNotExist:
                return redirect('user_dashboard')

        messages.error(request, 'Invalid username or password.')
    return render(request, 'gallery/login.html')


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        role = request.POST.get('role', 'user')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'gallery/register.html')
        user = User.objects.create_user(username=username, email=email, password=password,
            first_name=first_name, last_name=last_name)
        if role == 'artist':
            Artist.objects.create(user=user, name=f"{first_name} {last_name}".strip() or username)
            # SMS Alert - New Artist Registration
            send_sms_alert(
                f"🎨 New Artist Registered!\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 Name: {first_name} {last_name}\n"
                f"📧 Email: {email}\n"
                f"🎭 Role: ARTIST\n"
                f"━━━━━━━━━━━━━━━\n"
                f"ArtExhibit"
            )
            login(request, user)
            return redirect('artist_dashboard')

        # SMS Alert - New User Registration
        send_sms_alert(
            f"👤 New User Registered!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 Name: {first_name} {last_name}\n"
            f"📧 Email: {email}\n"
            f"🎭 Role: USER\n"
            f"━━━━━━━━━━━━━━━\n"
            f"ArtExhibit"
        )
        login(request, user)
        return redirect('user_dashboard')
    return render(request, 'gallery/register.html')


def logout_view(request):
    logout(request)
    return redirect('home')


# ── ADMIN DASHBOARD ──
@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        messages.error(request, 'Access denied.')
        return redirect('home')
    return render(request, 'gallery/admin_dashboard.html', {
        'total_artworks': Artwork.objects.count(),
        'total_artists': Artist.objects.count(),
        'total_users': User.objects.count(),
        'total_exhibitions': Exhibition.objects.count(),
        'unread_messages': ContactMessage.objects.filter(is_read=False).count(),
        'recent_artworks': Artwork.objects.order_by('-created_at')[:8],
        'recent_users': User.objects.order_by('-date_joined')[:6],
        'recent_messages': ContactMessage.objects.order_by('-created_at')[:6],
        'all_artworks': Artwork.objects.all().order_by('-created_at'),
        'exhibitions': Exhibition.objects.all().order_by('-start_date'),
        'artists': Artist.objects.annotate(work_count=Count('artwork')).order_by('-work_count'),
        'categories': Category.objects.all(),
        'all_users': User.objects.all().order_by('-date_joined'),
    })


@login_required
def admin_delete_artwork(request, pk):
    if not request.user.is_superuser:
        return redirect('home')
    get_object_or_404(Artwork, pk=pk).delete()
    messages.success(request, 'Artwork deleted.')
    return redirect('admin_dashboard')


@login_required
def admin_toggle_featured(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Denied'}, status=403)
    artwork = get_object_or_404(Artwork, pk=pk)
    artwork.is_featured = not artwork.is_featured
    artwork.save()
    return JsonResponse({'featured': artwork.is_featured})


@login_required
def admin_mark_message_read(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Denied'}, status=403)
    msg = get_object_or_404(ContactMessage, pk=pk)
    msg.is_read = True
    msg.save()
    return JsonResponse({'success': True})


@login_required
def admin_add_exhibition(request):
    if not request.user.is_superuser:
        return redirect('home')
    if request.method == 'POST':
        Exhibition.objects.create(
            title=request.POST.get('title'), description=request.POST.get('description'),
            start_date=request.POST.get('start_date'), end_date=request.POST.get('end_date'),
            status=request.POST.get('status', 'upcoming'),
            is_virtual=request.POST.get('is_virtual') == 'on',
        )
        messages.success(request, 'Exhibition created!')
    return redirect('admin_dashboard')


@login_required
def admin_delete_user(request, pk):
    if not request.user.is_superuser:
        return redirect('home')
    user = get_object_or_404(User, pk=pk)
    if user != request.user:
        user.delete()
        messages.success(request, 'User deleted.')
    return redirect('admin_dashboard')


@login_required
def sms_setup(request):
    if not request.user.is_superuser:
        return redirect('home')
    return render(request, 'gallery/sms_setup.html')


# ── ARTIST DASHBOARD ──
@login_required
def artist_dashboard(request):
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        messages.error(request, 'Artist profile not found.')
        return redirect('home')
    artworks = Artwork.objects.filter(artist=artist).order_by('-created_at')
    return render(request, 'gallery/artist_dashboard.html', {
        'artist': artist, 'artworks': artworks,
        'total_views': sum(a.view_count for a in artworks),
        'total_likes': sum(a.like_count() for a in artworks),
        'total_comments': sum(a.comment_count() for a in artworks),
        'total_artworks': artworks.count(),
        'exhibitions': Exhibition.objects.all(),
        'categories': Category.objects.all(),
        'medium_choices': Artwork.MEDIUM_CHOICES,
        'recent_comments': Comment.objects.filter(artwork__artist=artist).order_by('-created_at')[:5],
    })


@login_required
def artist_add_artwork(request):
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        return redirect('home')
    if request.method == 'POST':
        artwork = Artwork(
            title=request.POST.get('title'), artist=artist,
            description=request.POST.get('description', ''),
            medium=request.POST.get('medium', 'other'),
            year_created=request.POST.get('year_created', 2024),
            dimensions=request.POST.get('dimensions', ''),
            tags=request.POST.get('tags', ''),
            is_for_sale=request.POST.get('is_for_sale') == 'on',
        )
        price = request.POST.get('price', '')
        if price:
            artwork.price = price
        cat_id = request.POST.get('category')
        if cat_id:
            artwork.category_id = cat_id
        ex_id = request.POST.get('exhibition')
        if ex_id:
            artwork.exhibition_id = ex_id
        artwork.image = request.FILES.get('image', 'artworks/placeholder.jpg')
        artwork.save()
        messages.success(request, f'"{artwork.title}" uploaded!')
    return redirect('artist_dashboard')


@login_required
def artist_delete_artwork(request, pk):
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        return redirect('home')
    get_object_or_404(Artwork, pk=pk, artist=artist).delete()
    messages.success(request, 'Artwork deleted.')
    return redirect('artist_dashboard')


@login_required
def artist_update_profile(request):
    try:
        artist = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        return redirect('home')
    if request.method == 'POST':
        artist.name = request.POST.get('name', artist.name)
        artist.bio = request.POST.get('bio', artist.bio)
        artist.country = request.POST.get('country', artist.country)
        artist.website = request.POST.get('website', artist.website)
        artist.instagram = request.POST.get('instagram', artist.instagram)
        if 'profile_image' in request.FILES:
            artist.profile_image = request.FILES['profile_image']
        artist.save()
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()
        messages.success(request, 'Profile updated!')
    return redirect('artist_dashboard')


# ── USER DASHBOARD ──
@login_required
def user_dashboard(request):
    liked = Artwork.objects.filter(like__user=request.user).order_by('-like__created_at')
    my_comments = Comment.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'gallery/user_dashboard.html', {
        'liked_artworks': liked,
        'my_comments': my_comments,
        'total_likes': liked.count(),
        'total_comments': my_comments.count(),
        'recent_artworks': Artwork.objects.order_by('-created_at')[:6],
        'active_exhibitions': Exhibition.objects.filter(status='active'),
    })


@login_required
def user_update_profile(request):
    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()
        messages.success(request, 'Profile updated!')
    return redirect('user_dashboard')


# ── AI ENDPOINTS ──
@csrf_exempt
def get_demo_chat_response(message):
    """200+ Art Topics ka Smart ARIA Response System"""
    m = message.lower().strip()

    # ── GREETINGS ──
    if any(w in m for w in ['hi', 'hello', 'hey', 'hii', 'helo', 'namaste', 'namaskar', 'good morning', 'good evening', 'good afternoon', 'sup', 'howdy', 'greetings', 'salut', 'bonjour']):
        return "Namaste! 🎨 I'm ARIA — your personal AI Art Guide at ArtExhibit! I know 200+ art topics — from Renaissance to Digital Art, from Picasso to Indian Classical Art. Ask me anything about artworks, artists, styles, techniques, history, or our gallery. What would you like to explore? ✨"

    # ── ABOUT ARIA / AI ──
    elif any(w in m for w in ['who are you', 'what are you', 'aria', 'ai assistant', 'bot', 'chatbot', 'robot', 'artificial intelligence', 'your name']):
        return "I'm ARIA — Art Research & Inspiration Assistant! 🤖✨ I'm an AI-powered art guide built into ArtExhibit. I can help you discover artworks, learn about art history, understand different styles and techniques, get personalized recommendations, and navigate our gallery. I know about 200+ art topics — just ask!"

    # ══════════════════════════════════════
    # ART MOVEMENTS & STYLES
    # ══════════════════════════════════════

    # Renaissance
    elif any(w in m for w in ['renaissance', 'rebirth', 'da vinci', 'leonardo', 'michelangelo', 'raphael', 'botticelli', 'donatello', 'sistine', 'mona lisa', 'the last supper', 'birth of venus']):
        return "🏛️ The Renaissance (14th-17th century) was art's greatest rebirth! It emerged in Florence, Italy, emphasizing humanism, perspective, and naturalism. Masters like Leonardo da Vinci (Mona Lisa, The Last Supper), Michelangelo (Sistine Chapel ceiling), and Raphael defined this era. Key features: realistic human figures, linear perspective, chiaroscuro (light-shadow), and religious + mythological themes. ArtExhibit's classical collection draws deep inspiration from Renaissance ideals!"

    # Baroque
    elif any(w in m for w in ['baroque', 'caravaggio', 'rembrandt', 'rubens', 'vermeer', 'velazquez', 'dramatic light', 'chiaroscuro', 'tenebrism']):
        return "🎭 Baroque art (17th century) is famous for drama, movement, and intense contrasts of light and dark! Caravaggio pioneered tenebrism — extreme light-dark contrast. Rembrandt mastered emotional portraiture. Vermeer captured intimate domestic scenes. Key features: dynamic compositions, emotional intensity, rich colors, and theatrical lighting. It was the art of kings, churches, and drama!"

    # Impressionism
    elif any(w in m for w in ['impressionism', 'impressionist', 'monet', 'claude monet', 'renoir', 'degas', 'pissarro', 'manet', 'water lilies', 'loose brushwork', 'en plein air', 'plein air']):
        return "🌸 Impressionism revolutionized art in 1860s France! Artists like Monet, Renoir, and Degas painted outdoors (en plein air), capturing fleeting light and movement with loose, visible brushstrokes. Monet's Water Lilies series is iconic. They were rejected by the official Paris Salon and laughed at — yet they changed art forever! Key features: natural light, everyday subjects, visible brushwork, and pure colors. Several ArtExhibit watercolor artists are inspired by Impressionism!"

    # Post-Impressionism
    elif any(w in m for w in ['post impressionism', 'post-impressionism', 'van gogh', 'vincent van gogh', 'cezanne', 'paul cezanne', 'gauguin', 'seurat', 'starry night', 'sunflowers', 'pointillism', 'divisionism']):
        return "⭐ Post-Impressionism (1880s-1900s) pushed beyond Impressionism's boundaries! Van Gogh used swirling, expressive brushstrokes and vivid colors (Starry Night, Sunflowers). Cézanne built forms with geometric shapes, influencing Cubism. Seurat invented Pointillism — thousands of color dots creating images. Gauguin fled to Tahiti for bold, flat colors. These artists were the bridge between traditional art and modern movements!"

    # Expressionism
    elif any(w in m for w in ['expressionism', 'expressionist', 'edvard munch', 'the scream', 'kandinsky', 'wassily kandinsky', 'kirchner', 'emotional art', 'distortion', 'inner feeling']):
        return "😱 Expressionism (early 20th century) prioritized inner emotion over outer reality! Edvard Munch's 'The Scream' is the ultimate expressionist icon — anguish made visible. Wassily Kandinsky was a pioneer of abstract expressionism, believing art should evoke music. Key features: distorted forms, intense colors, emotional rawness, and psychological depth. It was art as therapy, art as scream!"

    # Cubism
    elif any(w in m for w in ['cubism', 'cubist', 'picasso', 'pablo picasso', 'georges braque', 'guernica', 'multiple perspectives', 'fragmented', 'geometric faces', 'les demoiselles']):
        return "📐 Cubism (1907-1920s) shattered traditional perspective! Picasso and Braque showed objects from multiple viewpoints simultaneously — a face might have a front view and side view at once. Picasso's 'Les Demoiselles d'Avignon' and 'Guernica' are masterpieces. Guernica depicts the horrors of war in fragmented, agonized forms. Key features: geometric shapes, multiple perspectives, monochrome palette, and deconstruction of form!"

    # Surrealism
    elif any(w in m for w in ['surrealism', 'surrealist', 'surreal', 'salvador dali', 'dali', 'magritte', 'rene magritte', 'frida kahlo', 'frida', 'dream', 'subconscious', 'unconscious', 'melting clocks', 'persistence of memory']):
        return "🌙 Surrealism (1920s-1930s) dived into dreams and the unconscious mind! Salvador Dalí's 'Persistence of Memory' (melting clocks) is iconic. René Magritte painted impossibilities like men in bowler hats with apple faces. Frida Kahlo created deeply personal, symbolic self-portraits exploring pain and identity. Key features: dreamlike imagery, impossible juxtapositions, psychological symbolism, and automatic drawing. Surrealism believed art should bypass rational thought!"

    # Abstract Art
    elif any(w in m for w in ['abstract', 'abstract art', 'non-representational', 'non representational', 'mondrian', 'rothko', 'mark rothko', 'pollock', 'jackson pollock', 'action painting', 'color field', 'shapes and colors']):
        return "🔷 Abstract art removes recognizable subjects entirely — it's pure form, color, and emotion! Mondrian used only primary colors and right angles. Rothko painted large color fields that seem to glow and pulse with emotion. Jackson Pollock dripped and flung paint on canvas (action painting). Key features: no recognizable subjects, emphasis on color/line/texture, emotional or intellectual focus. Our Digital Art collection features stunning abstract works — explore them in the Gallery!"

    # Pop Art
    elif any(w in m for w in ['pop art', 'warhol', 'andy warhol', 'lichtenstein', 'roy lichtenstein', 'campbell soup', 'marilyn monroe', 'comic art', 'popular culture', 'consumer culture', 'mass media']):
        return "🎸 Pop Art (1950s-60s) brought everyday consumer culture into the gallery! Andy Warhol silk-screened Campbell's Soup cans and Marilyn Monroe portraits. Roy Lichtenstein painted comic book panels in giant scale. Pop Art celebrated (and criticized) mass media, advertising, and celebrity culture. Key features: bold colors, commercial imagery, repetition, and irony. It asked: what IS art if a soup can can be art?"

    # Minimalism
    elif any(w in m for w in ['minimalism', 'minimalist', 'minimal', 'less is more', 'simple art', 'clean lines', 'monochrome', 'geometric minimalism', 'donald judd', 'carl andre']):
        return "⬜ Minimalism (1960s) believed 'less is more' — strip art down to its absolute essence! Simple geometric forms, industrial materials, neutral colors, and extreme reduction. Donald Judd created precise metal boxes. Carl Andre arranged bricks on gallery floors. Key features: geometric simplicity, industrial materials, no emotion or narrative, focus on form and space. Our platform's clean design aesthetic is inspired by minimalist principles!"

    # Contemporary Art
    elif any(w in m for w in ['contemporary', 'contemporary art', 'modern art', 'today art', 'current art', 'new art', '21st century art', '2000s art', 'recent art']):
        return "🌍 Contemporary art (post-1970s to today) is incredibly diverse — there are no rules! It spans painting, sculpture, video, performance, digital art, installation, street art, and more. Themes include identity, technology, climate change, politics, and globalization. ArtExhibit is a contemporary art platform — all our artists create current, relevant work. Explore our Gallery to see what today's artists are creating!"

    # Art Nouveau
    elif any(w in m for w in ['art nouveau', 'klimt', 'gustav klimt', 'mucha', 'alphonse mucha', 'jugendstil', 'organic forms', 'decorative', 'the kiss', 'floral patterns']):
        return "🌿 Art Nouveau (1890-1910) drew from nature — curving lines, floral patterns, and organic forms! Gustav Klimt's 'The Kiss' with its golden, decorative patterns is iconic. Alphonse Mucha created beautiful decorative posters. Art Nouveau influenced architecture (Gaudí's Barcelona!), furniture, jewelry, and graphic design. Key features: sinuous curves, natural motifs, ornamental style, and integration of art into everyday objects!"

    # Bauhaus
    elif any(w in m for w in ['bauhaus', 'walter gropius', 'paul klee', 'moholy', 'craft and art', 'design school', 'form follows function', 'german design']):
        return "🏗️ The Bauhaus (1919-1933, Germany) united fine art with functional design and craft! It believed art should serve society — beautiful AND functional. Paul Klee and Wassily Kandinsky taught there. Typography, furniture, architecture, painting — all treated equally. The Nazis closed it in 1933, but Bauhaus teachers fled worldwide and revolutionized modern design. Its influence is seen in everything from Apple products to modern architecture!"

    # Street Art & Graffiti
    elif any(w in m for w in ['street art', 'graffiti', 'banksy', 'urban art', 'mural', 'spray paint', 'stencil art', 'public art', 'basquiat', 'jean michel basquiat', 'keith haring']):
        return "🏙️ Street art transformed public spaces into galleries! Banksy's anonymous stencil works appear worldwide, blending dark humor with political commentary. Jean-Michel Basquiat rose from NYC graffiti to gallery superstar. Keith Haring's bold, joyful figures appeared on NYC subway walls. Street art is democratic art — for everyone, free to see. It challenges: who decides what art is 'acceptable'? Several ArtExhibit artists work in urban-inspired styles!"

    # ══════════════════════════════════════
    # FAMOUS ARTISTS
    # ══════════════════════════════════════

    elif any(w in m for w in ['frida kahlo', 'frida', 'kahlo', 'self portrait', 'mexican artist', 'feminist art', 'pain in art']):
        return "🌺 Frida Kahlo (1907-1954) is one of history's most powerful artists! She created 55 self-portraits exploring pain, identity, gender, and Mexican culture after a devastating bus accident at 18. Her work is surrealist, personal, and fiercely feminist. Famous works: 'The Two Fridas', 'Self-Portrait with Thorn Necklace'. She said: 'I paint myself because I am so often alone and I am the subject I know best.' A true icon!"

    elif any(w in m for w in ['vincent van gogh', 'van gogh', 'gogh', 'starry night', 'sunflowers', 'ear', 'yellow house', 'post-impressionist painter']):
        return "⭐ Vincent van Gogh (1853-1890) created over 2,000 artworks in just 10 years — but sold only ONE painting in his lifetime! His swirling, passionate brushstrokes in Starry Night and Sunflowers are instantly recognizable. He struggled with mental illness and famously cut off part of his ear. After his death, the world finally recognized his genius. Now his works sell for hundreds of millions. A tragic but transcendent story!"

    elif any(w in m for w in ['pablo picasso', 'picasso', 'guernica', 'cubism painter', 'les demoiselles', 'blue period', 'rose period']):
        return "🎨 Pablo Picasso (1881-1973) is perhaps the most influential artist of the 20th century! He co-invented Cubism, revolutionizing how we represent reality. His Blue Period (melancholy blues) and Rose Period (warm circus scenes) show his range. Guernica (1937) is a powerful anti-war masterpiece. He created 20,000+ works across painting, sculpture, ceramics, and printmaking. He lived to 91, creating until the end!"

    elif any(w in m for w in ['rembrandt', 'dutch master', 'dutch golden age', 'portrait lighting', 'self portrait painter', 'night watch']):
        return "🕯️ Rembrandt van Rijn (1606-1669) is the master of light and shadow! His portraits seem to glow from within — a technique called Rembrandt lighting. 'The Night Watch' is his most famous work. He painted over 90 self-portraits throughout his life — the first great artistic autobiography. His psychological depth and technical mastery remain unmatched in portraiture!"

    elif any(w in m for w in ['claude monet', 'monet', 'water lilies', 'giverny', 'haystacks', 'rouen cathedral', 'japanese bridge']):
        return "🌸 Claude Monet (1840-1926) is the father of Impressionism! He painted the same subjects repeatedly to capture changing light — haystacks at different times of day, Rouen Cathedral in morning vs evening light. His Water Lilies series (250+ paintings!) at Giverny is a meditation on nature and reflection. He lost most of his eyesight but kept painting. His garden at Giverny, France is now a museum!"

    elif any(w in m for w in ['leonardo da vinci', 'da vinci', 'mona lisa', 'vitruvian man', 'the last supper', 'renaissance man', 'inventor artist']):
        return "🔬 Leonardo da Vinci (1452-1519) was the ultimate Renaissance Man — painter, sculptor, architect, musician, scientist, mathematician, engineer, inventor! The Mona Lisa's mysterious smile has fascinated for 500 years. The Last Supper captures the dramatic moment Jesus announces his betrayal. Vitruvian Man shows his perfect union of art and science. He filled 7,000+ pages of notebooks with inventions centuries ahead of his time!"

    elif any(w in m for w in ['michelangelo', 'sistine chapel', 'david sculpture', 'pieta', 'ceiling painting', 'buonarroti']):
        return "⛪ Michelangelo (1475-1564) created art of almost supernatural power! The Sistine Chapel ceiling took 4 years to paint (1508-1512) — he worked on scaffolding, paint dripping on his face. David (marble statue) captures perfect human form. The Pietà shows Mary holding the crucified Christ with heartbreaking tenderness. He was also a brilliant architect. He said: 'Every block of stone has a statue inside it — it is the sculptor's task to discover it.'"

    elif any(w in m for w in ['raja ravi varma', 'ravi varma', 'indian classical painter', 'oleograph', 'shakuntala', 'indian mythology painting']):
        return "🇮🇳 Raja Ravi Varma (1848-1906) is India's most celebrated classical painter! He brilliantly merged European oil painting techniques with Indian mythological and literary subjects. His paintings of goddesses — Lakshmi, Saraswati, Shakuntala — defined how Indians visualize their gods. He invented the oleograph printing press to make art affordable for common people. Born in Kerala's royal family, he changed Indian art forever!"

    elif any(w in m for w in ['amrita sher-gil', 'amrita shergil', 'sher gil', 'indian modern art', 'self portrait india', 'hungarian indian artist']):
        return "🌟 Amrita Sher-Gil (1913-1941) is the 'Frida Kahlo of India'! Half Hungarian, half Indian, she studied in Paris and returned to India to paint rural village life with extraordinary empathy. Her self-portraits are powerful and unflinching. Tragically she died at just 28, but left a legacy that defines Indian modernism. Her works are among the most expensive Indian paintings ever sold!"

    elif any(w in m for w in ['mf husain', 'm f husain', 'husain', 'indian modern painter', 'barefoot painter', 'horse paintings india']):
        return "🐎 M.F. Husain (1915-2011) was India's most celebrated modern painter — often called the 'Picasso of India'! Famous for his bold, colorful depictions of horses, Indian culture, and goddesses. He controversially worked barefoot his entire life. His works sold for crores. He spent his final years in exile due to controversy over his goddess paintings. A complex, brilliant, and iconic figure in Indian art!"

    elif any(w in m for w in ['banksy', 'anonymous artist', 'girl with balloon', 'devolved parliament', 'street artist anonymous']):
        return "🐀 Banksy is the world's most famous anonymous artist! Their identity remains unknown despite worldwide fame. Famous works: 'Girl with Balloon' (self-destructed at auction!), 'Devolved Parliament' (MPs replaced by chimps). They appear on walls overnight in cities worldwide — sharp political and social commentary through stencils and dark humor. Their work sells for millions despite being free to see on streets. The ultimate art world paradox!"

    # ══════════════════════════════════════
    # ART TECHNIQUES & MEDIUMS
    # ══════════════════════════════════════

    elif any(w in m for w in ['oil painting', 'oil paint', 'oil on canvas', 'oil medium', 'linseed oil']):
        return "🖌️ Oil painting has been the king of art mediums since the 15th century! Oil pigments mixed with linseed oil dry slowly, allowing artists to blend, rework, and build up layers (glazing). This creates extraordinary depth and luminosity. Van Eyck is credited with perfecting the technique. Famous for: rich colors, subtle gradients, smooth transitions, and lasting centuries. ArtExhibit features stunning oil paintings — filter by 'Oil Painting' in our Gallery!"

    elif any(w in m for w in ['watercolor', 'water colour', 'watercolour', 'transparent paint', 'wet on wet', 'water media']):
        return "💧 Watercolor is the most luminous of mediums — light passes through transparent pigment and reflects back from the white paper! Techniques include wet-on-wet (soft, blooming effects), wet-on-dry (sharp edges), and dry brush (texture). It's unforgiving — mistakes are hard to fix! Turner used it for atmospheric landscapes. Winslow Homer for seascapes. Our artists like James Chen create breathtaking watercolor landscapes — explore them in the Gallery!"

    elif any(w in m for w in ['acrylic', 'acrylic paint', 'acrylic medium', 'fast drying paint', 'polymer paint']):
        return "🎨 Acrylic paint was invented in the 1950s — the newest major painting medium! It's water-based but dries waterproof, fast-drying, and incredibly versatile. It can mimic oil paint (thick, impasto) or watercolor (thin washes). Artists like David Hockney love acrylics for their bold, fresh colors. ArtExhibit features vibrant acrylic works that pop with energy!"

    elif any(w in m for w in ['sculpture', 'sculpting', 'three dimensional', '3d art', 'clay', 'bronze', 'marble sculpture', 'stone carving', 'casting']):
        return "🗿 Sculpture is art in three dimensions — it exists in real space and can be walked around! Techniques include carving (removing material — marble, stone), modeling (adding material — clay, wax), casting (pouring metal into molds — bronze), and assemblage (combining found objects). Rodin's 'The Thinker' and Michelangelo's 'David' are iconic. ArtExhibit features sculptors like Marco Rosetti who work with bronze and stone!"

    elif any(w in m for w in ['digital art', 'digital painting', 'computer art', 'photoshop art', 'procreate', 'tablet art', 'cgi art', 'pixel art', 'vector art']):
        return "💻 Digital art uses computers and tablets as the canvas! Tools include Photoshop, Procreate, Illustrator, Blender, and more. It can mimic traditional mediums or create entirely new aesthetics impossible by hand. ArtExhibit's Yuki Tanaka blends traditional Japanese ukiyo-e aesthetics with digital techniques. Key advantage: infinitely editable, easily reproduced, global distribution. The future of art is digital!"

    elif any(w in m for w in ['photography', 'fine art photography', 'photo art', 'black and white photo', 'documentary photography', 'portrait photography', 'landscape photography']):
        return "📷 Photography as fine art goes far beyond documentation — it's about vision, composition, light, and meaning! Ansel Adams' black and white landscapes are as powerful as any painting. Cindy Sherman's self-portraits explore identity. Sebastião Salgado documents humanity with epic scope. ArtExhibit's Amara Osei captures powerful West African street life. Photography asks: what makes a moment worth preserving forever?"

    elif any(w in m for w in ['printmaking', 'etching', 'lithograph', 'woodcut', 'screen print', 'linocut', 'engraving', 'intaglio']):
        return "🖨️ Printmaking creates multiple originals through various transfer methods! Woodcut (carving wood, inking, pressing on paper) — Hokusai's Great Wave is a woodcut! Etching (acid on metal plate). Screen printing (Warhol's method). Lithography (drawing on stone with grease). Each technique has unique textural qualities. Prints made art democratic — multiple copies at lower prices than unique paintings!"

    elif any(w in m for w in ['mixed media', 'collage', 'assemblage', 'found objects', 'installation art', 'multi media art']):
        return "🎭 Mixed media art combines multiple materials and techniques in one work! Collage (gluing paper, photos, fabric) — Picasso and Braque invented it. Assemblage uses found 3D objects. Installation art transforms entire rooms or spaces. ArtExhibit's Elena Vasquez works in mixed media — found consumer objects commenting on modern life. Mixed media has no rules: anything can be art!"

    elif any(w in m for w in ['fresco', 'mural', 'wall painting', 'ceiling painting', 'plaster painting', 'buon fresco']):
        return "🏛️ Fresco is painting directly on wet plaster — pigment becomes part of the wall itself, lasting thousands of years! Michelangelo's Sistine Chapel ceiling is the greatest fresco. Diego Rivera's Mexican murals brought political art to public buildings. Cave paintings at Lascaux (35,000 years old!) are essentially prehistoric frescoes. The oldest human art we know is painted on walls!"

    elif any(w in m for w in ['pastel', 'chalk pastel', 'oil pastel', 'soft pastel', 'degas pastel', 'pastelist']):
        return "🌈 Pastels are pure pigment in stick form — intensely vibrant! Degas used soft pastels brilliantly for his ballet dancer series. They create luminous, velvety surfaces. Soft pastels blend beautifully but are delicate. Oil pastels are more robust. Pastel drawings are technically drawings but optically feel like paintings. They're one of the oldest mediums — used since the Renaissance!"

    elif any(w in m for w in ['charcoal drawing', 'charcoal art', 'pencil drawing', 'graphite', 'ink drawing', 'sketch', 'drawing technique']):
        return "✏️ Drawing is the foundation of all art! Charcoal creates dramatic darks and beautiful smudging. Graphite pencil allows precise, delicate lines. Ink (pen and wash) creates bold, permanent marks. Da Vinci's drawings are as revered as his paintings. Gesture drawing captures movement in seconds. Contour drawing follows edges. Drawing trains the eye and hand — it's where every artist begins!"

    elif any(w in m for w in ['mosaic', 'stained glass', 'tile art', 'glass art', 'ceramic art', 'pottery art']):
        return "🪟 Mosaic and glass art transform light itself into art! Byzantine mosaics in gold and colored glass have shimmered in churches for 1,500 years. Stained glass cathedral windows tell Biblical stories in colored light. Gaudi's mosaic work at Sagrada Família is modern mosaic art. Ceramic art — pottery elevated to fine art — has ancient roots in every culture. These are the art forms that outlast empires!"

    # ══════════════════════════════════════
    # INDIAN ART
    # ══════════════════════════════════════

    elif any(w in m for w in ['indian art', 'india art', 'indian painting', 'indian classical art', 'indian modern art', 'desi art', 'bharat kala', 'indian artist']):
        artworks = Artwork.objects.all()[:3]
        names = ", ".join([f'"{a.title}"' for a in artworks]) if artworks else "several stunning works"
        return f"🇮🇳 Indian art has one of the world's richest and longest traditions! From ancient Ajanta cave paintings (2nd century BC!), Mughal miniatures, Rajput paintings, and Bengal School to modern masters like Raja Ravi Varma, Amrita Sher-Gil, MF Husain, and contemporary digital artists. India's art reflects its incredible diversity — 28 states, hundreds of folk art traditions! ArtExhibit proudly features Indian artists. Check out {names} in our Gallery!"

    elif any(w in m for w in ['mughal painting', 'mughal art', 'miniature painting', 'persian miniature', 'rajput painting', 'pahari painting', 'kangra painting']):
        return "👑 Mughal miniature painting (16th-19th century) is one of India's greatest art traditions! Intricate, jewel-like paintings depicting court scenes, battles, portraits, and nature. Artists worked with squirrel-hair brushes and natural pigments — sometimes using a single hair for finest details! Rajput and Pahari paintings show romantic themes from Hindu epics in vivid colors. These tiny masterpieces required years to complete!"

    elif any(w in m for w in ['madhubani', 'mithila', 'warli', 'folk art', 'tribal art', 'pattachitra', 'kalamkari', 'phad', 'gond art', 'tanjore', 'kerala mural']):
        return "🌺 India's folk and tribal art traditions are living, breathing art forms! Madhubani/Mithila: Bihar's geometric patterns in natural colors — originally drawn on walls. Warli: Maharashtra's tribal art with stick figures in circles. Gond art: intricate patterns from Madhya Pradesh. Pattachitra: Odisha's scroll paintings. Kalamkari: hand-painted fabric from Andhra Pradesh. Tanjore: gold-embellished Tamil Nadu paintings. These are India's UNESCO-recognized living traditions!"

    elif any(w in m for w in ['ajanta', 'ellora', 'cave painting', 'ancient indian art', 'buddhist art', 'jain art']):
        return "🏔️ The Ajanta Caves (2nd century BC - 6th century AD) contain the world's finest ancient paintings! Buddhist monks painted these masterpieces on cave walls over 800 years — stories of Buddha's lives in extraordinary detail. Ellora caves feature both Buddhist, Hindu, and Jain art carved from living rock. India's ancient art tradition is 35,000+ years old (Bhimbetka rock paintings in Madhya Pradesh)!"

    # ══════════════════════════════════════
    # WORLD ART TRADITIONS
    # ══════════════════════════════════════

    elif any(w in m for w in ['japanese art', 'japan art', 'ukiyo-e', 'ukiyoe', 'hokusai', 'hiroshige', 'woodblock', 'great wave', 'manga art', 'anime art']):
        return "🌸 Japanese art has a breathtaking tradition! Ukiyo-e woodblock prints (17th-19th century) — Hokusai's Great Wave off Kanagawa is the world's most reproduced artwork! Hiroshige's landscape prints inspired Monet. Japanese aesthetics: wabi-sabi (beauty in imperfection), ma (negative space), and mono no aware (beauty of transience). Today, manga and anime are Japan's global art contribution. ArtExhibit's Yuki Tanaka blends these traditions with digital art!"

    elif any(w in m for w in ['chinese art', 'china art', 'chinese painting', 'ink wash', 'chinese calligraphy', 'chinese pottery', 'chinese landscape']):
        return "🐉 Chinese art has 5,000+ years of history! Ink wash painting (shuimohua) uses black ink in subtle gradations — mountains, bamboo, and birds captured in elegant brushstrokes. Chinese calligraphy is considered the highest art form. Porcelain and ceramics influenced the world (the word 'china' IS Chinese porcelain!). Chinese landscape painting (shan shui) depicts the cosmic relationship between man and nature — mountains in mist, rivers, pine trees."

    elif any(w in m for w in ['african art', 'africa art', 'african mask', 'tribal mask', 'benin bronze', 'west african art', 'contemporary african']):
        return "🌍 African art has profoundly shaped world art! Picasso acknowledged African masks as inspiration for Cubism. Benin Bronzes (15th-16th century Nigeria) are masterpieces of royal portraiture in metal. African masks are not merely decorative — they're ceremonial objects with spiritual power. Contemporary African artists like El Anatsui (Ghana) create giant tapestries from bottle caps. ArtExhibit's Amara Osei captures West African urban life through photography!"

    elif any(w in m for w in ['islamic art', 'arabic art', 'calligraphy art', 'arabesque', 'geometric pattern', 'persian art', 'ottoman art', 'mosque art']):
        return "☪️ Islamic art is famous for its breathtaking geometric complexity and calligraphy! Since depicting human figures was discouraged in religious contexts, artists developed infinite geometric patterns (arabesque) and elevated calligraphy to the highest art form. The Alhambra palace in Spain, Persian miniature paintings, and Turkish Iznik ceramics are glorious examples. Islamic art influenced mathematics — many geometric patterns encode complex mathematical principles!"

    elif any(w in m for w in ['greek art', 'roman art', 'ancient art', 'classical art', 'ancient sculpture', 'parthenon', 'venus de milo', 'discus thrower']):
        return "🏛️ Ancient Greek and Roman art set the foundations for Western art for 2,000 years! Greek sculpture idealized the perfect human form — Venus de Milo, Discus Thrower. The Parthenon frieze told stories in marble. Romans copied Greek sculpture and created portrait busts of startling realism. The Renaissance was literally a RE-birth of classical ideals. When we talk about 'academic' art tradition, we're tracing a line back to ancient Greece!"

    # ══════════════════════════════════════
    # ART THEORY & CONCEPTS
    # ══════════════════════════════════════

    elif any(w in m for w in ['composition', 'rule of thirds', 'golden ratio', 'fibonacci', 'balance in art', 'asymmetry', 'symmetry art', 'visual weight']):
        return "📐 Composition is how an artist arranges elements in a work! Rule of Thirds: divide the canvas in 9 equal parts — place subjects at intersection points for dynamic balance. Golden Ratio/Spiral: found in nature and used since ancient Greece — Da Vinci, Michelangelo, and modern photographers use it. Symmetry creates stability. Asymmetry creates tension and interest. Leading lines guide the viewer's eye. Negative space is as important as positive space!"

    elif any(w in m for w in ['color theory', 'color wheel', 'complementary colors', 'warm colors', 'cool colors', 'color mixing', 'hue saturation', 'tint shade tone']):
        return "🌈 Color theory is the science and art of color! The color wheel shows relationships: complementary colors (opposite — red/green, blue/orange) create maximum contrast. Analogous colors (neighboring — blue, blue-green, green) create harmony. Warm colors (red, orange, yellow) advance and energize. Cool colors (blue, green, purple) recede and calm. Tint = color + white. Shade = color + black. Tone = color + gray. Monet and the Impressionists revolutionized how artists think about color!"

    elif any(w in m for w in ['perspective', 'linear perspective', 'one point perspective', 'two point perspective', 'aerial perspective', 'vanishing point', 'depth in art']):
        return "📏 Perspective creates the illusion of 3D depth on a 2D surface! Linear perspective: parallel lines converge at a vanishing point on the horizon — invented/codified in the Renaissance by Brunelleschi. One-point perspective (looking down a road). Two-point perspective (corners of buildings). Aerial/atmospheric perspective: distant objects are lighter and bluer (less contrast) — Monet and Chinese ink painters both used this. Without perspective, art looks flat!"

    elif any(w in m for w in ['light in art', 'shadow', 'shading', 'highlight', 'chiaroscuro', 'tenebrism', 'sfumato', 'form and light']):
        return "☀️ Light is what makes art come alive! Chiaroscuro (Italian for 'light-dark') creates dramatic contrast — Caravaggio and Rembrandt mastered this. Tenebrism is extreme chiaroscuro with subjects emerging from near-total darkness. Sfumato (da Vinci's technique) creates soft, smoky transitions between light and dark — giving the Mona Lisa her mysterious quality. Highlights are the lightest areas. Shadows have color — they're never simply black! Impressionists painted colored shadows."

    elif any(w in m for w in ['texture in art', 'impasto', 'thick paint', 'palette knife', 'surface texture', 'rough texture art']):
        return "🎨 Texture in art is both visual and tactile! Impasto (Italian for 'paste') is thick, heavily textured paint application — Van Gogh's swirling brushstrokes are extreme impasto. Palette knife painting creates bold, flat areas of color. Smooth, blended texture (sfumato) suggests mystery. Rough texture suggests energy and rawness. In sculpture, texture is everything — polished marble vs rough granite tells completely different stories. Touch me! (metaphorically speaking)"

    elif any(w in m for w in ['symbolism in art', 'art symbols', 'iconography', 'allegory', 'vanitas', 'memento mori', 'hidden meaning art']):
        return "🔮 Art is full of hidden symbols and meanings — iconography! In Renaissance art: skull = death, hourglass = passing time, lily = purity, lamb = Christ. Vanitas paintings (Dutch Golden Age) feature skulls, wilting flowers, and bubbles — reminders of life's brevity. Red = passion/danger. Blue = divine/calm. Every color, object, and gesture in classical art had specific meaning that educated viewers understood. Modern art often deliberately breaks these codes!"

    elif any(w in m for w in ['negative space', 'white space', 'empty space art', 'ma japan', 'space in composition']):
        return "⬜ Negative space is the space AROUND and BETWEEN subjects — and it's just as important as the subject itself! Japanese aesthetic concept of 'ma' (間) celebrates meaningful emptiness. FedEx logo has a hidden arrow in the negative space. Georgia O'Keeffe's flower paintings fill the entire canvas — eliminating negative space for intense focus. Banksy uses negative space brilliantly. Great compositions deliberately shape negative space!"

    # ══════════════════════════════════════
    # PHOTOGRAPHY & MODERN MEDIA
    # ══════════════════════════════════════

    elif any(w in m for w in ['portrait', 'portrait art', 'portrait painting', 'face painting', 'likeness', 'sitter']):
        return "👤 Portrait art is one of the oldest art forms — capturing a person's likeness and inner essence! From Egyptian pharaoh busts to Rembrandt's psychological portraits to Freud's raw, unsettling paintings of flesh. A great portrait goes beyond physical resemblance — it reveals character, status, emotion, and moment in time. Selfies are the modern portrait! ArtExhibit features stunning portrait works in our collection. Find them in the Gallery!"

    elif any(w in m for w in ['landscape art', 'landscape painting', 'nature painting', 'scenery art', 'countryside painting', 'seascape', 'mountain painting']):
        return "🏔️ Landscape painting celebrates the natural world! In Chinese art, landscape (shan shui) IS the highest genre. European landscape evolved from background in portraits to main subject in the 17th century. Turner's atmospheric storms. Constable's English countryside. American Hudson River School's epic wilderness. Impressionists painted landscapes in changing light. ArtExhibit features beautiful landscape works — James Chen's watercolor landscapes are breathtaking!"

    elif any(w in m for w in ['still life', 'still-life', 'flowers painting', 'fruit painting', 'vanitas still life', 'dutch still life']):
        return "🌹 Still life painting explores the beauty of everyday objects! Dutch Golden Age still lifes were technically brilliant and symbolically rich — flowers that never existed (painted from multiple blooms across different seasons!), fruits with hidden decay, skulls hidden among plenty. Cézanne's still lifes of apples were so revolutionary they led to Cubism. Giorgio Morandi spent his whole career painting simple bottles and jars — finding infinity in the ordinary!"

    elif any(w in m for w in ['abstract expressionism', 'abstract expressionist', 'new york school', 'action painting', 'color field painting', 'de kooning', 'franz kline', 'lee krasner']):
        return "💥 Abstract Expressionism (1940s-50s, New York) was America's first major art movement! Jackson Pollock dripped and flung paint on canvas laid on the floor. Willem de Kooning attacked canvas aggressively. Mark Rothko painted large, glowing color fields that seem to breathe. Lee Krasner (Pollock's wife) was equally brilliant but less recognized. It was raw, emotional, LARGE, and thoroughly American — shifting the art world from Paris to New York!"

    # ══════════════════════════════════════
    # PLATFORM FEATURES
    # ══════════════════════════════════════

    elif any(w in m for w in ['artwork', 'artworks', 'painting', 'collection', 'gallery', 'browse', 'explore', 'view art', 'see art']):
        artworks = Artwork.objects.filter(is_featured=True)[:4]
        names = " | ".join([f'"{a.title}" by {a.artist.name}' for a in artworks]) if artworks else "Golden Meridian | Neon Ukiyo | Earth Memory | Market Day Accra"
        return f"🖼️ ArtExhibit has a stunning collection spanning Oil Painting, Watercolor, Digital Art, Photography, Sculpture, Mixed Media, Drawing, and Printmaking! Featured right now: {names}. Visit our Gallery page to browse all artworks with filters for medium, category, and sorting. Click any artwork for full details, AI analysis, and purchase options!"

    elif any(w in m for w in ['artist', 'artists', 'creator', 'painter', 'sculptor', 'photographer', 'who made', 'who created']):
        artists = Artist.objects.all()[:4]
        names = " | ".join([f"{a.name} ({a.country})" for a in artists]) if artists else "Priya Sharma (India) | Marco Rosetti (Italy) | Yuki Tanaka (Japan) | Amara Osei (Ghana)"
        return f"🎨 ArtExhibit features incredible artists from around the world! Currently: {names} and more. Each artist brings unique cultural perspective and technical expertise. Visit the Artists page to explore profiles, portfolios, bios, and links to each artist's complete body of work on our platform!"

    elif any(w in m for w in ['exhibition', 'exhibitions', 'show', 'exhibit', 'virtual exhibition', 'online show', 'current show']):
        exs = Exhibition.objects.filter(status='active')[:3]
        names = " | ".join([e.title for e in exs]) if exs else "Chromatic Dreams | Digital Horizons | Roots & Routes"
        return f"🏛️ ArtExhibit hosts virtual art exhibitions — accessible from anywhere in the world, 24/7! Currently active: {names}. Each exhibition brings together artworks around a compelling theme. Visit our Exhibitions page for full details, dates, and to explore all artworks in each show!"

    elif any(w in m for w in ['buy', 'purchase', 'price', 'cost', 'how much', 'collect', 'acquire', 'invest', 'art investment', 'buy artwork']):
        return "🛒 Buying art on ArtExhibit is simple and secure! Browse the Gallery → click any artwork marked 'Available for Purchase' → see the price → click 'Buy Now' or 'Add to Cart'. Checkout requires your delivery address and payment method (Cash on Delivery, UPI, Bank Transfer, or Card). Every purchase includes Certificate of Authenticity and free insured shipping. Art investment can appreciate significantly over time!"

    elif any(w in m for w in ['upload art', 'sell art', 'become artist', 'artist account', 'list artwork', 'showcase work', 'submit artwork']):
        return "🎨 Artists can join ArtExhibit FREE! Register as an 'Artist' → get your own Artist Dashboard → upload artworks with images, descriptions, medium, price → your work goes live in our Gallery instantly! Set your own prices, manage your portfolio, track views and likes, and connect with collectors worldwide. Join thousands of artists sharing their vision with the world!"

    elif any(w in m for w in ['account', 'register', 'sign up', 'join', 'membership', 'login', 'sign in', 'free account']):
        return "👤 Joining ArtExhibit is completely FREE! Click 'Join' in the navigation bar. Choose your role: Art Lover (browse, like, comment, purchase) or Artist (all of the above + upload and sell your work!). Your account gives you a personal dashboard, liked artworks collection, order history, and access to all AI features. No credit card needed to register!"

    elif any(w in m for w in ['contact', 'reach', 'support', 'help', 'enquire', 'enquiry', 'question']):
        return "📧 We're here to help! Visit our Contact page and send us a message — we respond within 24 hours. For artwork purchase enquiries, use the 'Enquire to Purchase' button on any artwork page. For technical support, account issues, or artist partnerships, use the Contact form. ARIA (that's me!) is also available 24/7 for art questions and platform guidance!"

    elif any(w in m for w in ['recommend', 'suggest', 'what should i', 'which artwork', 'best artwork', 'favorite', 'popular']):
        popular = Artwork.objects.order_by('-view_count')[:3]
        names = " | ".join([f'"{a.title}"' for a in popular]) if popular else '"Golden Meridian" | "Neon Ukiyo" | "Earth Memory"'
        return f"✨ Great question! Most viewed artworks right now: {names}. To get truly personalized recommendations, scroll down on our Homepage to the AI Recommender and describe what you love — 'moody dark abstracts', 'vibrant Indian colors', 'peaceful watercolor landscapes' — and I'll find your perfect match from our collection!"

    # ══════════════════════════════════════
    # ART BUSINESS & CAREER
    # ══════════════════════════════════════

    elif any(w in m for w in ['art career', 'become artist', 'art school', 'art college', 'art degree', 'study art', 'art education', 'art student']):
        return "🎓 Building an art career in 2024 has never had more options! Traditional: art school/college degree in Fine Arts, Illustration, or Graphic Design. Self-taught: online platforms like Skillshare, YouTube, Domestika. Key skills: consistent practice (draw EVERY day!), develop a unique style, build an online portfolio (Instagram, ArtStation, Behance), enter competitions, and reach collectors directly through platforms like ArtExhibit. Your audience is global — start sharing your work today!"

    elif any(w in m for w in ['art market', 'art auction', 'sothebys', 'christies', 'art price', 'expensive artwork', 'most expensive painting', 'art investment value']):
        return "💰 The global art market is worth $67+ billion! Most expensive artwork ever sold: Leonardo da Vinci's 'Salvator Mundi' — $450 million (2017, Christie's)! Top auction houses: Sotheby's and Christie's. But most art is bought and sold outside auctions — through galleries, online platforms, and directly from artists. Art can be a great investment — Banksy, Basquiat, and Kusama works have increased 1000%+ in value. ArtExhibit makes collecting original art accessible!"

    elif any(w in m for w in ['nft', 'nft art', 'crypto art', 'blockchain art', 'digital ownership', 'beeple', 'opensea']):
        return "🔷 NFT (Non-Fungible Token) art took the world by storm in 2021! Beeple's 'Everydays: The First 5000 Days' sold for $69 million at Christie's — a digital JPEG! NFTs use blockchain technology to prove digital ownership and authenticity. The NFT market has cooled since 2021's peak but continues evolving. ArtExhibit focuses on traditional and digital art with physical or digital delivery — the future may include NFT certificates of ownership!"

    elif any(w in m for w in ['art therapy', 'healing through art', 'therapeutic art', 'mindfulness art', 'art and mental health', 'creative therapy']):
        return "💚 Art therapy is a powerful mental health tool! Creating art — regardless of skill level — reduces cortisol (stress hormone), activates the brain's reward system, and provides nonverbal emotional expression. Coloring books for adults are a form of art therapy. Many hospitals use art programs for healing. Viewing art also has documented health benefits — reduced anxiety and improved mood. ArtExhibit believes art is not just beautiful — it's healing!"

    # ══════════════════════════════════════
    # COLORS & SPECIFIC SUBJECTS
    # ══════════════════════════════════════

    elif any(w in m for w in ['blue color art', 'blue painting', 'klein blue', 'yves klein', 'blue period picasso', 'cobalt blue', 'ultramarine']):
        return "💙 Blue has a fascinating art history! Ultramarine (from lapis lazuli) was once more expensive than gold — used only for the Virgin Mary's robes in medieval art. Yves Klein invented his own 'International Klein Blue' and painted entire canvases with it. Picasso's Blue Period (1901-1904) used cold blues to express depression after his friend's suicide. Blue represents sky, water, divinity, sadness, and infinity. It's the world's favorite color!"

    elif any(w in m for w in ['gold in art', 'gold leaf', 'golden', 'byzantine gold', 'klimt gold', 'gilding', 'icon painting']):
        return "✨ Gold in art represents the divine! Byzantine icons used gold backgrounds to show sacred subjects existing outside earthly time and space. Medieval illuminated manuscripts were gilded with gold leaf. Gustav Klimt's 'The Kiss' and 'Portrait of Adele' use real gold leaf extensively — inspired by Byzantine mosaics. Japanese art uses gold in lacquerware (maki-e) and folding screen paintings. Gold doesn't tarnish — it literally lasts forever, like the divine it represents!"

    elif any(w in m for w in ['red color art', 'red painting', 'vermillion', 'crimson', 'passion in art', 'red symbolism art']):
        return "❤️ Red is the most emotionally powerful color in art! It represents love, passion, danger, blood, and power. Chinese art uses red for luck and celebration. Medieval art used expensive vermillion (mercury sulfide) for red. Rothko's red paintings are almost overwhelming in their emotional intensity. Matisse's 'The Red Studio' bathes everything in vibrant red. Red advances visually — it jumps out of the canvas. No other color demands attention like red!"

    elif any(w in m for w in ['flower art', 'floral painting', 'flower painting', 'georgia o keeffe', 'botanical art', 'rose painting', 'sunflower art']):
        return "🌸 Flowers have inspired artists for thousands of years! Georgia O'Keeffe enlarged flowers to monumental scale — seeing sexual and spiritual dimensions in petals. Van Gogh's Sunflowers series captured joy and friendship. Dutch Golden Age flower paintings showed botanically impossible arrangements. Japanese cherry blossom (sakura) art captures mono no aware — beauty's transience. ArtExhibit features beautiful floral works — search 'flowers' in our Gallery!"

    # ══════════════════════════════════════
    # ARCHITECTURE AS ART
    # ══════════════════════════════════════

    elif any(w in m for w in ['architecture', 'gaudi', 'sagrada familia', 'zaha hadid', 'frank lloyd wright', 'gothic architecture', 'art and architecture']):
        return "🏗️ Architecture is the art we live inside! Antoni Gaudí's Sagrada Família in Barcelona (still under construction since 1882!) is organic architecture inspired by nature. Zaha Hadid's fluid, impossible-looking buildings redefined what structures could be. Frank Lloyd Wright's Fallingwater flows with the landscape. Gothic cathedrals are engineering and art united — stained glass, flying buttresses, soaring heights designed to make humans feel close to the divine!"

    # ══════════════════════════════════════
    # FINAL CATCHALL
    # ══════════════════════════════════════

    elif any(w in m for w in ['thank', 'thanks', 'thank you', 'dhanyawad', 'shukriya', 'great', 'awesome', 'amazing aria', 'good aria', 'helpful']):
        return "You're so welcome! 🎨✨ That's what I'm here for! I know 200+ art topics — from ancient cave paintings to NFT art, from Mughal miniatures to abstract expressionism. Keep exploring ArtExhibit's beautiful collection! Is there anything else about art, artists, or our platform you'd like to know? I'm always here!"

    elif any(w in m for w in ['bye', 'goodbye', 'see you', 'later', 'ciao', 'alvida', 'tata']):
        return "Goodbye! 🎨 Thank you for visiting ArtExhibit — where art meets technology! Come back anytime to explore our growing collection. Remember: art is everywhere, once you start looking. ARIA is always here when you need an art guide! Happy exploring! ✨"

    else:
        artworks = Artwork.objects.order_by('-view_count')[:2]
        popular = " and ".join([f'"{a.title}"' for a in artworks]) if artworks else '"Golden Meridian" and "Neon Ukiyo"'
        return f"Great question! 🎨 I'm ARIA and I know 200+ art topics! I can tell you about: Art Movements (Renaissance, Impressionism, Cubism, Surrealism, Abstract, Pop Art, Street Art), Famous Artists (Da Vinci, Van Gogh, Picasso, Frida Kahlo, Raja Ravi Varma, Banksy), Techniques (Oil, Watercolor, Digital, Sculpture, Photography), Indian Art (Mughal, Folk, Modern), Color Theory, Composition, Art History, and much more! Most popular on our platform right now: {popular}. What would you like to explore?"


def ai_describe_artwork(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        artwork = get_object_or_404(Artwork, pk=data.get('artwork_id'))
        
        # Try real API first
        api_key = settings.ANTHROPIC_API_KEY
        if api_key != 'your-anthropic-api-key-here':
            prompt = f"Analyze: '{artwork.title}' by {artwork.artist.name}, {artwork.get_medium_display()}, {artwork.year_created}. Description: {artwork.description}. Write 2-paragraph art critic analysis."
            result = ai_chat(prompt, "You are a world-renowned art critic.")
            if 'unavailable' not in result:
                return JsonResponse({'description': result})
        
        # Smart demo fallback
        medium_desc = {
            'oil': 'rich, luminous oil paint layers that create extraordinary depth',
            'watercolor': 'delicate watercolor washes that achieve remarkable luminosity',
            'digital': 'cutting-edge digital techniques that push the boundaries of contemporary art',
            'photography': 'masterful photographic composition that captures a decisive moment',
            'sculpture': 'three-dimensional form that commands space with powerful presence',
            'mixed': 'innovative mixed media approach that challenges traditional boundaries',
            'acrylic': 'bold acrylic strokes that convey energy and immediacy',
            'drawing': 'precise draftsmanship that reveals extraordinary skill and vision',
        }.get(artwork.medium, 'masterful technique and artistic vision')
        
        description = f'"{artwork.title}" by {artwork.artist.name} is a remarkable work that demonstrates {medium_desc}. Created in {artwork.year_created}, this {artwork.get_medium_display().lower()} piece invites the viewer into a deeply personal visual dialogue. {artwork.description if artwork.description else "The work speaks eloquently through its composition and emotional resonance."}\n\nAs a significant work in {artwork.artist.name}\'s portfolio, "{artwork.title}" reflects the artist\'s commitment to authentic expression and technical mastery. The piece rewards careful contemplation, revealing new layers of meaning with each viewing. It stands as a testament to the enduring power of visual art to communicate across cultural and linguistic boundaries, making it a worthy addition to any serious collection.'
        return JsonResponse({'description': description})
    return JsonResponse({'error': 'POST required'}, status=400)


@csrf_exempt
def ai_chat_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        message = data.get('message', '')
        history = data.get('history', [])
        
        # Try real API first
        api_key = settings.ANTHROPIC_API_KEY
        if api_key != 'your-anthropic-api-key-here':
            system = "You are ARIA, an expert AI art guide for ArtExhibit. Help visitors discover artworks, understand art history, and get recommendations. Be warm and concise."
            try:
                req_data = json.dumps({"model": "claude-sonnet-4-20250514", "max_tokens": 512,
                    "system": system, "messages": history + [{"role": "user", "content": message}]}).encode('utf-8')
                req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=req_data,
                    headers={'Content-Type': 'application/json', 'x-api-key': api_key, 'anthropic-version': '2023-06-01'})
                with urllib.request.urlopen(req, timeout=30) as response:
                    return JsonResponse({'response': json.loads(response.read())['content'][0]['text']})
            except:
                pass
        
        # Smart demo fallback - always works!
        return JsonResponse({'response': get_demo_chat_response(message)})
    return JsonResponse({'error': 'POST required'}, status=400)


@csrf_exempt
def ai_recommend(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        preferences = data.get('preferences', '').lower()
        
        # Try real API first
        api_key = settings.ANTHROPIC_API_KEY
        if api_key != 'your-anthropic-api-key-here':
            artworks = Artwork.objects.all()[:20]
            artwork_list = "\n".join([f"- ID:{a.pk} '{a.title}' by {a.artist.name} ({a.get_medium_display()})" for a in artworks])
            prompt = f'User likes: "{preferences}"\nArtworks:\n{artwork_list}\nRecommend 3. Return ONLY JSON: [{{"id":1,"reason":"..."}}]'
            response = ai_chat(prompt, "Art recommender. Return only valid JSON array.")
            try:
                clean = response.strip().split('```')
                clean = clean[1] if len(clean) > 1 else clean[0]
                if clean.startswith('json'): clean = clean[4:]
                recs = json.loads(clean)
                if recs:
                    return JsonResponse({'recommendations': recs})
            except:
                pass
        
        # Smart demo fallback based on preferences
        all_artworks = list(Artwork.objects.all())
        scored = []
        keywords = {
            'color': ['vibrant', 'colorful', 'bright', 'bold'],
            'calm': ['serene', 'peaceful', 'calm', 'quiet', 'muted'],
            'nature': ['landscape', 'nature', 'earth', 'water', 'monsoon'],
            'modern': ['digital', 'modern', 'contemporary', 'abstract', 'technology'],
            'dark': ['dark', 'moody', 'dramatic', 'shadow', 'night'],
            'portrait': ['portrait', 'figure', 'human', 'face', 'people'],
        }
        for artwork in all_artworks:
            score = 0
            text = f"{artwork.title} {artwork.description} {artwork.tags} {artwork.get_medium_display()}".lower()
            for pref_word in preferences.split():
                if pref_word in text:
                    score += 3
            for category, words in keywords.items():
                if any(w in preferences for w in words):
                    if any(w in text for w in words):
                        score += 2
            scored.append((score, artwork))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:3] if scored else []
        
        reasons = [
            "This piece perfectly matches your aesthetic preferences with its unique composition and emotional depth.",
            "The artist's masterful use of medium and color palette aligns beautifully with what you're looking for.",
            "This artwork's themes and visual language resonate strongly with your described preferences.",
        ]
        
        recs = [{"id": art.pk, "reason": f'"{art.title}" by {art.artist.name} — {reasons[i % 3]}'} 
                for i, (score, art) in enumerate(top)]
        
        if not recs:
            featured = Artwork.objects.filter(is_featured=True)[:3]
            recs = [{"id": a.pk, "reason": f'"{a.title}" by {a.artist.name} — A featured artwork highly appreciated by our visitors.'} 
                    for a in featured]
        
        return JsonResponse({'recommendations': recs})
    return JsonResponse({'error': 'POST required'}, status=400)


@login_required
def toggle_like(request, pk):
    artwork = get_object_or_404(Artwork, pk=pk)
    like, created = Like.objects.get_or_create(user=request.user, artwork=artwork)
    if not created:
        like.delete()
    return JsonResponse({'liked': created, 'count': artwork.like_count()})


@login_required
def add_comment(request, pk):
    if request.method == 'POST':
        artwork = get_object_or_404(Artwork, pk=pk)
        text = json.loads(request.body).get('text', '').strip()
        if text:
            comment = Comment.objects.create(user=request.user, artwork=artwork, text=text)
            return JsonResponse({'success': True, 'username': request.user.username,
                'text': comment.text, 'created_at': comment.created_at.strftime('%b %d, %Y')})
    return JsonResponse({'success': False})


# ─────────────────────────────────────────
#  PURCHASE / CART / ORDER VIEWS
# ─────────────────────────────────────────
from .models import Cart, CartItem, Order, OrderItem

@login_required
def add_to_cart(request, pk):
    artwork = get_object_or_404(Artwork, pk=pk)
    if not artwork.is_for_sale or not artwork.price:
        messages.error(request, 'This artwork is not available for sale.')
        return redirect('artwork_detail', pk=pk)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, artwork=artwork)
    if not created:
        messages.info(request, f'"{artwork.title}" is already in your cart!')
    else:
        messages.success(request, f'"{artwork.title}" added to cart! 🛒')
    return redirect('cart_view')


@login_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.cartitem_set.all()
    return render(request, 'gallery/cart.html', {
        'cart': cart, 'items': items, 'total': cart.total()
    })


@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('cart_view')


@login_required
def checkout_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.cartitem_set.all()
    if not items:
        messages.error(request, 'Your cart is empty!')
        return redirect('gallery')
    if request.method == 'POST':
        order = Order.objects.create(
            user=request.user,
            total_amount=cart.total(),
            full_name=request.POST.get('full_name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            address=request.POST.get('address'),
            city=request.POST.get('city'),
            state=request.POST.get('state'),
            pincode=request.POST.get('pincode'),
            payment_method=request.POST.get('payment_method', 'cod'),
            notes=request.POST.get('notes', ''),
            status='confirmed',
        )
        for item in items:
            OrderItem.objects.create(
                order=order,
                artwork=item.artwork,
                artwork_title=item.artwork.title,
                artist_name=item.artwork.artist.name,
                price=item.artwork.price,
                quantity=item.quantity,
            )
        cart.cartitem_set.all().delete()
        # SMS Alert - New Order
        send_sms_alert(
            f"🛒 New Order Placed!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📦 Order: #{order.pk}\n"
            f"👤 Customer: {order.full_name}\n"
            f"📞 Phone: {order.phone}\n"
            f"💰 Total: Rs.{order.total_amount}\n"
            f"💳 Payment: {order.payment_method.upper()}\n"
            f"📍 City: {order.city}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"ArtExhibit Orders"
        )
        messages.success(request, f'Order #{order.pk} placed successfully! 🎉')
        return redirect('order_success', pk=order.pk)
    return render(request, 'gallery/checkout.html', {
        'cart': cart, 'items': items, 'total': cart.total(),
        'user': request.user,
    })


@login_required
def order_success(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'gallery/order_success.html', {'order': order})


@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'gallery/my_orders.html', {'orders': orders})


@login_required
def buy_now(request, pk):
    """Direct buy — add to cart and go to checkout"""
    artwork = get_object_or_404(Artwork, pk=pk)
    if not artwork.is_for_sale or not artwork.price:
        messages.error(request, 'This artwork is not available for sale.')
        return redirect('artwork_detail', pk=pk)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    CartItem.objects.get_or_create(cart=cart, artwork=artwork)
    return redirect('checkout')
