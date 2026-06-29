from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('', views.home, name='home'),
    path('gallery/', views.gallery_view, name='gallery'),
    path('artwork/<int:pk>/', views.artwork_detail, name='artwork_detail'),
    path('artists/', views.artist_list, name='artists'),
    path('artist/<int:pk>/', views.artist_detail, name='artist_detail'),
    path('exhibitions/', views.exhibitions_view, name='exhibitions'),
    path('exhibition/<int:pk>/', views.exhibition_detail, name='exhibition_detail'),
    path('contact/', views.contact_view, name='contact'),

    # Auth
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Admin Dashboard
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/artwork/delete/<int:pk>/', views.admin_delete_artwork, name='admin_delete_artwork'),
    path('admin-panel/artwork/feature/<int:pk>/', views.admin_toggle_featured, name='admin_toggle_featured'),
    path('admin-panel/message/read/<int:pk>/', views.admin_mark_message_read, name='admin_mark_message_read'),
    path('admin-panel/exhibition/add/', views.admin_add_exhibition, name='admin_add_exhibition'),
    path('admin-panel/user/delete/<int:pk>/', views.admin_delete_user, name='admin_delete_user'),

    # Artist Dashboard
    path('artist/dashboard/', views.artist_dashboard, name='artist_dashboard'),
    path('artist/artwork/add/', views.artist_add_artwork, name='artist_add_artwork'),
    path('artist/artwork/delete/<int:pk>/', views.artist_delete_artwork, name='artist_delete_artwork'),
    path('artist/profile/update/', views.artist_update_profile, name='artist_update_profile'),

    # User Dashboard
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/profile/update/', views.user_update_profile, name='user_update_profile'),
    path('orders/', views.my_orders, name='my_orders'),

    # Purchase / Cart / Orders
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('order/success/<int:pk>/', views.order_success, name='order_success'),
    path('buy-now/<int:pk>/', views.buy_now, name='buy_now'),

    # AI API
    path('api/ai-describe/', views.ai_describe_artwork, name='ai_describe'),
    path('api/ai-chat/', views.ai_chat_api, name='ai_chat'),
    path('api/ai-recommend/', views.ai_recommend, name='ai_recommend'),
    path('api/like/<int:pk>/', views.toggle_like, name='toggle_like'),
    path('api/comment/<int:pk>/', views.add_comment, name='add_comment'),
]
