from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from gallery.models import Artist, Category, Exhibition, Artwork
from django.utils import timezone
from datetime import date


class Command(BaseCommand):
    help = 'Seed database with sample art exhibition data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')

        # Create superuser
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@artexhibit.com', 'admin123')
            self.stdout.write('Created admin user: admin / admin123')

        # Create Categories
        categories_data = [
            ('Painting', 'painting', '🖼️'),
            ('Photography', 'photography', '📷'),
            ('Digital Art', 'digital-art', '💻'),
            ('Sculpture', 'sculpture', '🗿'),
            ('Mixed Media', 'mixed-media', '🎭'),
            ('Drawing', 'drawing', '✏️'),
        ]
        categories = {}
        for name, slug, icon in categories_data:
            cat, _ = Category.objects.get_or_create(
                slug=slug, defaults={'name': name, 'icon': icon}
            )
            categories[slug] = cat
        self.stdout.write('Created categories')

        # Create Artists
        artists_data = [
            ('Priya Sharma', 'Mumbai-based contemporary artist exploring identity and culture through vibrant oil paintings.', 'India'),
            ('Marco Rosetti', 'Italian sculptor working with bronze and reclaimed materials to explore human form.', 'Italy'),
            ('Yuki Tanaka', 'Tokyo digital artist blending traditional ukiyo-e aesthetics with modern technology.', 'Japan'),
            ('Amara Osei', 'Ghanaian photographer documenting urban life and social dynamics in West Africa.', 'Ghana'),
            ('Elena Vasquez', 'Barcelona mixed media artist using found objects to comment on consumerism.', 'Spain'),
            ('James Chen', 'San Francisco watercolor artist capturing landscapes and fleeting moments.', 'USA'),
        ]
        artists = []
        for name, bio, country in artists_data:
            artist, _ = Artist.objects.get_or_create(
                name=name, defaults={'bio': bio, 'country': country}
            )
            artists.append(artist)
        self.stdout.write('Created artists')

        # Create Exhibitions
        exhibitions_data = [
            ('Chromatic Dreams', 'A vibrant exploration of color theory in contemporary art.', date(2024, 1, 15), date(2025, 12, 31), 'active'),
            ('Digital Horizons', 'Where technology meets artistic expression.', date(2025, 3, 1), date(2026, 6, 30), 'active'),
            ('Roots & Routes', 'Artworks exploring cultural identity and migration.', date(2025, 6, 1), date(2026, 8, 31), 'active'),
        ]
        exhibitions = []
        for title, desc, start, end, status in exhibitions_data:
            ex, _ = Exhibition.objects.get_or_create(
                title=title, defaults={
                    'description': desc, 'start_date': start,
                    'end_date': end, 'status': status, 'is_virtual': True
                }
            )
            exhibitions.append(ex)
        self.stdout.write('Created exhibitions')

        # Create Artworks
        artworks_data = [
            ('Golden Meridian', artists[0], categories['painting'], 'oil', 2023, 'A sweeping landscape where golden light fractures across a horizon of possibility. The brushwork is deliberate and layered, building depth through transparent glazes.', True, 2500.00, exhibitions[0]),
            ('Silence Between Notes', artists[1], categories['sculpture'], 'sculpture', 2022, 'Bronze figures frozen in conversation, capturing the pause between spoken words.', True, 8500.00, None),
            ('Neon Ukiyo', artists[2], categories['digital-art'], 'digital', 2024, 'A modern reimagining of the floating world, where ancient wood-block motifs dance with neon light and digital pixels.', True, 450.00, exhibitions[1]),
            ('Market Day, Accra', artists[3], categories['photography'], 'photography', 2023, 'Street photography capturing the vibrant chaos and human connection of a busy West African market.', True, 750.00, exhibitions[2]),
            ('Consumption Loop', artists[4], categories['mixed-media'], 'mixed', 2024, 'Assemblage of branded packaging and consumer goods forming a circular composition questioning our relationship with objects.', True, 3200.00, exhibitions[1]),
            ('Morning Mist, Kyoto', artists[5], categories['painting'], 'watercolor', 2023, 'Delicate watercolor capturing morning fog rising from temple gardens in shades of grey and lavender.', False, 950.00, None),
            ('Identity Fragments', artists[0], categories['mixed-media'], 'mixed', 2024, 'Mixed media self-portrait exploring diaspora identity through layered fabrics, photographs and paint.', True, 4100.00, exhibitions[2]),
            ('Data Stream', artists[2], categories['digital-art'], 'digital', 2024, 'Generative artwork visualizing the flow of data through global networks as abstract flowing forms.', False, 280.00, exhibitions[1]),
            ('Urban Breath', artists[3], categories['photography'], 'photography', 2022, 'Long exposure photography capturing the movement of city life as light trails and ghostly human silhouettes.', False, 620.00, None),
            ('Earth Memory', artists[1], categories['sculpture'], 'sculpture', 2023, 'Carved limestone forms suggesting geological time and the layering of human history.', True, 12000.00, None),
            ('Monsoon Season', artists[5], categories['painting'], 'watercolor', 2024, 'Vivid watercolors depicting the drama and beauty of the Indian monsoon.', False, 1100.00, exhibitions[0]),
            ('Parallel Lives', artists[4], categories['photography'], 'photography', 2023, 'Diptych photographs juxtaposing similar moments from radically different lives across the world.', True, 890.00, exhibitions[2]),
        ]

        for title, artist, category, medium, year, desc, featured, price, exhibition in artworks_data:
            Artwork.objects.get_or_create(
                title=title, artist=artist,
                defaults={
                    'category': category,
                    'medium': medium,
                    'year_created': year,
                    'description': desc,
                    'is_featured': featured,
                    'price': price,
                    'is_for_sale': True,
                    'exhibition': exhibition,
                    'image': 'artworks/placeholder.jpg',
                    'tags': f'{category.name}, {artist.country}, {year}'
                }
            )
        self.stdout.write('Created artworks')
        self.stdout.write(self.style.SUCCESS('✅ Database seeded successfully!'))
        self.stdout.write('Admin: admin / admin123')
