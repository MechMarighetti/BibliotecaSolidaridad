from django.urls import path
from .views import (
    BookSearchView,
    AddBookView,
    BookDetailView,
    ProfileView,
    SearchOpenLibraryAPIView,
    AddReviewView,
    ToggleFavoriteView,
    EditReviewView,
    DeleteReviewView,
    RemoveFavoriteView,
    RemoveBookView,
)

urlpatterns = [
    path('search/', BookSearchView.as_view(), name='book_search'),
    path('add/', AddBookView.as_view(), name='add_book'),
    path('api/search-openlibrary/', SearchOpenLibraryAPIView.as_view(), name='search_openlibrary_api'),
    path('<int:pk>/', BookDetailView.as_view(), name='book_detail'),
    path('<int:book_id>/review/', AddReviewView.as_view(), name='add_review'),
    path('<int:book_id>/review/edit/', EditReviewView.as_view(), name='edit_review'),
    path('<int:book_id>/review/delete/', DeleteReviewView.as_view(), name='delete_review'),
    path('<int:book_id>/favorite/', ToggleFavoriteView.as_view(), name='toggle_favorite'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('favorites/remove/<int:book_id>/', RemoveFavoriteView.as_view(), name='remove_favorite'),
    path('remove/<int:book_id>/', RemoveBookView.as_view(), name='remove_book'),
]
