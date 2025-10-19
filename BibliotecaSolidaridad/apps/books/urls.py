from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.book_search, name='book_search'),
    path('add/', views.add_book, name='add_book'),
    path('<int:book_id>/', views.book_detail, name='book_detail'),
    path('api/search-openlibrary/', views.search_openlibrary, name='search_openlibrary_api'),
    path('<int:book_id>/review/', views.add_review, name='add_review'),
    path('<int:book_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
]
