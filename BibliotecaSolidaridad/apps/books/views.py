import logging

from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from ..users.mixin import LibrarianRequiredMixin, AdminRequiredMixin, MemberRequiredMixin
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Avg
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Book, Category, Review, Author, ISBN
from .forms import BookForm
from .services import OpenLibraryService
from apps.users.models import UserProfile

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Listados y búsqueda
# ---------------------------------------------------------------------------

class BookListView(ListView):
    """Listado general de libros con filtros simples."""
    model = Book
    template_name = 'books/book_list.html'
    context_object_name = 'books'
    paginate_by = 20

    def get_queryset(self):
        qs = Book.objects.all().prefetch_related('authors', 'categories')
        category_id = self.request.GET.get('category')
        author_id = self.request.GET.get('author')
        available = self.request.GET.get('available')

        if category_id:
            qs = qs.filter(categories__id=category_id)
        if author_id:
            qs = qs.filter(authors__id=author_id)
        if available == '1':
            qs = qs.filter(available=True, stock__gt=0)

        return qs.distinct().order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.all()
        ctx['authors'] = Author.objects.all()
        ctx['selected_category'] = self.request.GET.get('category', '')
        ctx['selected_author'] = self.request.GET.get('author', '')
        ctx['selected_available'] = self.request.GET.get('available', '')
        return ctx


class BookSearchView(ListView):
    """Búsqueda local + resultados de OpenLibrary."""
    model = Book
    template_name = 'books/book_search.html'
    context_object_name = 'local_results'
    paginate_by = 20

    def get_queryset(self):
        self.query = self.request.GET.get('q', '').strip()
        if not self.query:
            return Book.objects.none()
        return (
            Book.objects.search(self.query)
            .prefetch_related('authors', 'categories')
            .order_by('-created_at')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = getattr(self, 'query', '')
        if query:
            try:
                ctx['openlibrary_results'] = OpenLibraryService.search_books(query)
            except Exception as e:
                logger.error(f"Error consultando OpenLibrary: {e}", exc_info=True)
                ctx['openlibrary_results'] = []
            ctx['existing_ids'] = set(
                Book.objects.exclude(openlibrary_id__isnull=True)
                .values_list('openlibrary_id', flat=True)
            )
        else:
            ctx['openlibrary_results'] = []
            ctx['existing_ids'] = set()

        ctx['query'] = query
        ctx['searched'] = bool(query)
        return ctx


class RecommendedBooksView(ListView):
    model = Book
    template_name = 'books/recommended.html'
    context_object_name = 'books'

    def get_queryset(self):
        return Book.objects.recommended(limit=12).prefetch_related('authors')


# ---------------------------------------------------------------------------
# Detalle
# ---------------------------------------------------------------------------

class BookDetailView(DetailView):
    model = Book
    template_name = 'books/book_detail.html'
    context_object_name = 'book'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        book = self.object

        reviews = Review.objects.filter(book=book).select_related('user')
        ctx['recent_reviews'] = reviews[:3]
        ctx['review_count'] = reviews.count()
        ctx['average_rating'] = round(
            reviews.aggregate(avg=Avg('rating'))['avg'] or 0, 1
        )
        ctx['total_loans'] = (
            book.loan_set.count() if hasattr(book, 'loan_set') else 0
        )

        user = self.request.user
        ctx['user_review'] = (
            reviews.filter(user=user).first() if user.is_authenticated else None
        )
        ctx['user_has_reviewed'] = bool(ctx['user_review'])
        ctx['is_favorite'] = (
            user.is_authenticated
            and hasattr(user, 'profile')
            and hasattr(user.profile, 'favorite_books')
            and book in user.profile.favorite_books.all()
        )
        return ctx


# ---------------------------------------------------------------------------
# CRUD de libros
# ---------------------------------------------------------------------------

class AddBookView(LibrarianRequiredMixin, CreateView):
    model = Book
    form_class = BookForm
    template_name = 'books/add_book.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.all()
        return ctx

    def form_valid(self, form):
        openlibrary_id = self.request.POST.get('openlibrary_id')
        if openlibrary_id:
            form.instance.openlibrary_id = openlibrary_id
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Libro "{self.object.title}" agregado correctamente.'
        )
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor corregí los errores del formulario.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('book_detail', kwargs={'pk': self.object.pk})


class EditBookView(LibrarianRequiredMixin, UpdateView):
    model = Book
    form_class = BookForm
    template_name = 'books/edit_book.html'
    context_object_name = 'book'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.all()
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f'Libro "{self.object.title}" actualizado correctamente.'
        )
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor corregí los errores del formulario.')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('book_detail', kwargs={'pk': self.object.pk})


class RemoveBookView(LibrarianRequiredMixin, View):
    """Elimina un libro existente. Solo bibliotecarios/admin."""

    def post(self, request, book_id):
        referer = request.META.get('HTTP_REFERER', '/')
        book = Book.objects.filter(id=book_id).first()
        if not book:
            messages.warning(request, 'El libro no existe o ya fue eliminado.')
            return redirect(referer)

        title = book.title
        book.delete()
        messages.info(request, f'El libro "{title}" fue eliminado de la biblioteca.')
        return redirect(referer)


# ---------------------------------------------------------------------------
# Importar desde OpenLibrary
# ---------------------------------------------------------------------------

class ImportFromOpenLibraryView(LibrarianRequiredMixin, View):
    """Importa un libro desde OpenLibrary a la biblioteca local."""

    def post(self, request):
        openlibrary_id = request.POST.get('openlibrary_id', '').strip()
        referer = request.META.get('HTTP_REFERER', '/')

        if not openlibrary_id:
            messages.error(request, 'ID de OpenLibrary requerido.')
            return redirect(referer)

        existing = Book.objects.filter(openlibrary_id=openlibrary_id).first()
        if existing:
            messages.warning(request, f'El libro "{existing.title}" ya está en la biblioteca.')
            return redirect('book_detail', pk=existing.pk)

        try:
            data = OpenLibraryService.get_book_details(openlibrary_id)
            if not data:
                messages.error(request, 'No se pudo obtener el libro desde OpenLibrary.')
                return redirect(referer)

            with transaction.atomic():
                book = Book.objects.create(
                    openlibrary_id=openlibrary_id,
                    title=data.get('title', 'Sin título'),
                    publish_date=data.get('publish_date', ''),
                    description=data.get('description', ''),
                    number_of_pages=data.get('number_of_pages'),
                    cover_url=data.get('cover_url', ''),
                    stock=1,
                    available=True,
                )
                for author_name in data.get('authors', []):
                    author, _ = Author.objects.get_or_create(name=author_name)
                    book.authors.add(author)
                for isbn_str in data.get('isbn', []):
                    ISBN.objects.get_or_create(
                        isbn=isbn_str,
                        defaults={'book': book}
                    )

            messages.success(request, f'Libro "{book.title}" importado correctamente.')
            return redirect('book_detail', pk=book.pk)

        except Exception as e:
            logger.error(f'Error importando libro: {e}', exc_info=True)
            messages.error(request, 'Error al importar el libro.')
            return redirect(referer)


class SearchOpenLibraryAPIView(LibrarianRequiredMixin, View):
    """API JSON para búsquedas puntuales en OpenLibrary."""

    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'error': 'Query parameter required'}, status=400)

        try:
            books = OpenLibraryService.search_books(query)
            return JsonResponse({'books': books})
        except Exception as e:
            logger.error(f'Error en SearchOpenLibraryAPIView: {e}', exc_info=True)
            return JsonResponse({'error': 'Internal server error'}, status=500)


# ---------------------------------------------------------------------------
# Autores y categorías
# ---------------------------------------------------------------------------

class AuthorListView(ListView):
    model = Author
    template_name = 'books/author_list.html'
    context_object_name = 'authors'
    paginate_by = 30

    def get_queryset(self):
        return Author.objects.annotate(
            books_count=Book.objects.Count('books')
        ).order_by('name')


class AuthorDetailView(DetailView):
    model = Author
    template_name = 'books/author_detail.html'
    context_object_name = 'author'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['books'] = self.object.books.prefetch_related('categories').order_by('-created_at')
        return ctx


class CategoryListView(ListView):
    model = Category
    template_name = 'books/category_list.html'
    context_object_name = 'categories'


class CategoryDetailView(DetailView):
    model = Category
    template_name = 'books/category_detail.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['books'] = self.object.libros.prefetch_related('authors').order_by('-created_at')
        return ctx


# ---------------------------------------------------------------------------
# Reseñas
# ---------------------------------------------------------------------------

def _validate_rating_comment(request):
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '').strip()
    if not rating or not comment:
        return None, None, "Debés completar todos los campos."
    try:
        rating_int = int(rating)
    except (TypeError, ValueError):
        return None, None, "La calificación debe ser un número."
    if not (1 <= rating_int <= 5):
        return None, None, "La calificación debe estar entre 1 y 5."
    return rating_int, comment, None


class AddReviewView(LoginRequiredMixin, View):
    def post(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)

        if Review.objects.filter(book=book, user=request.user).exists():
            messages.warning(request, 'Ya has dejado una reseña para este libro.')
            return redirect('book_detail', pk=book_id)

        rating, comment, error = _validate_rating_comment(request)
        if error:
            messages.error(request, error)
            return redirect('book_detail', pk=book_id)

        Review.objects.create(
            user=request.user, book=book, rating=rating, comment=comment
        )
        messages.success(request, 'Tu reseña fue publicada correctamente.')
        return redirect('book_detail', pk=book_id)


class EditReviewView(LoginRequiredMixin, View):
    def post(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        review = Review.objects.filter(book=book, user=request.user).first()
        if not review:
            messages.error(request, 'No tenés una reseña para este libro.')
            return redirect('book_detail', pk=book_id)

        rating, comment, error = _validate_rating_comment(request)
        if error:
            messages.error(request, error)
            return redirect('book_detail', pk=book_id)

        review.rating = rating
        review.comment = comment
        review.save()
        messages.success(request, 'Tu reseña fue actualizada correctamente.')
        return redirect('book_detail', pk=book_id)


class DeleteReviewView(LoginRequiredMixin, View):
    def post(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        review = Review.objects.filter(book=book, user=request.user).first()
        if not review:
            messages.error(request, 'No tenés una reseña para eliminar.')
            return redirect('book_detail', pk=book_id)

        review.delete()
        messages.success(request, 'Tu reseña fue eliminada correctamente.')
        return redirect('book_detail', pk=book_id)


# ---------------------------------------------------------------------------
# Favoritos y perfil
# ---------------------------------------------------------------------------

class ToggleFavoriteView(LoginRequiredMixin, View):
    def post(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        profile = get_object_or_404(UserProfile, user=request.user)

        if book in profile.favorite_books.all():
            profile.favorite_books.remove(book)
            messages.info(request, f'El libro "{book.title}" fue eliminado de tus favoritos.')
        else:
            profile.favorite_books.add(book)
            messages.success(request, f'El libro "{book.title}" fue agregado a tus favoritos.')

        return redirect(request.META.get('HTTP_REFERER', '/'))


class RemoveFavoriteView(LoginRequiredMixin, View):
    def post(self, request, book_id):
        profile = get_object_or_404(UserProfile, user=request.user)
        book = get_object_or_404(Book, id=book_id)

        if book in profile.favorite_books.all():
            profile.favorite_books.remove(book)
            messages.success(request, f'El libro "{book.title}" fue eliminado de tus favoritos.')
        else:
            messages.warning(request, 'Este libro no estaba en tus favoritos.')

        return redirect('profile')


class ProfileView(LoginRequiredMixin, DetailView):
    model = UserProfile
    template_name = 'users/profile.html'
    context_object_name = 'profile'

    def get_object(self):
        return get_object_or_404(UserProfile, user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = self.get_object()
        ctx['user_favorites'] = profile.favorite_books.all()
        ctx['active_loans'] = self.request.user.loans.filter(
            status='active'
        ).select_related('book')
        ctx['loan_history'] = self.request.user.loans.exclude(
            status='active'
        ).select_related('book')
        return ctx


