from django.contrib import admin
from .models import Artwork, Artist, Category, Exhibition, Like, Comment, ContactMessage


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'artwork_count', 'created_at']
    search_fields = ['name', 'bio']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Exhibition)
class ExhibitionAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'start_date', 'end_date', 'is_virtual']
    list_filter = ['status', 'is_virtual']


@admin.register(Artwork)
class ArtworkAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist', 'medium', 'year_created', 'is_featured', 'is_for_sale', 'view_count']
    list_filter = ['medium', 'is_featured', 'is_for_sale', 'category']
    search_fields = ['title', 'artist__name', 'description']
    list_editable = ['is_featured', 'is_for_sale']


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'artwork', 'created_at']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'artwork', 'created_at']


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'created_at', 'is_read']
    list_editable = ['is_read']

from .models import Cart, CartItem, Order, OrderItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'full_name', 'total_amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method']
    list_editable = ['status']
    search_fields = ['full_name', 'email', 'user__username']

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'artwork_title', 'artist_name', 'price', 'quantity']
