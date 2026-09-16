import logging

from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from ..users.mixin import LibrarianRequiredMixin
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Avg
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Book, Category, Review, Author, ISBN, ReadingStatus
from .forms import BookForm
from .services import OpenLibraryService
from apps.users.models import UserProfile
from django.db.models import Count, Sum, Avg, Max, Min, Q, F

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

class SearchOpenLibraryAPIView(LibrarianRequiredMixin, View):
    """
    Búsqueda en OpenLibrary con dos modos:
      - Si el query es un ISBN → devuelve UNA edición exacta.
      - Si no → devuelve obras; cada una puede expandirse para ver sus ediciones.
    """

    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'error': 'Query parameter required'}, status=400)

        try:
            # Modo 1: el usuario tipeó un ISBN
            isbn = OpenLibraryService.looks_like_isbn(query)
            if isbn:
                edition = OpenLibraryService.get_edition_by_isbn(isbn)
                if edition:
                    return JsonResponse({
                        'mode': 'isbn',
                        'edition': edition,
                    })
                return JsonResponse({
                    'mode': 'isbn',
                    'edition': None,
                    'message': f'No se encontró el ISBN {isbn} en OpenLibrary.',
                })

            # Modo 2: búsqueda normal
            books = OpenLibraryService.search_books(query)
            return JsonResponse({
                'mode': 'search',
                'books': books,
            })

        except Exception as e:
            logger.error(f'Error en SearchOpenLibraryAPIView: {e}', exc_info=True)
            return JsonResponse({'error': 'Internal server error'}, status=500)


class WorkEditionsAPIView(LibrarianRequiredMixin, View):
    """Devuelve las ediciones de una obra para que el bibliotecario elija."""

    def get(self, request):
        work_id = request.GET.get('work_id', '').strip()
        if not work_id:
            return JsonResponse({'error': 'work_id requerido'}, status=400)

        editions = OpenLibraryService.get_work_editions(work_id)
        return JsonResponse({
            'work_id': work_id,
            'editions': editions,
            'count': len(editions),
        })

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
class MyShelfView(LoginRequiredMixin, ListView):
    model = ReadingStatus
    template_name = 'books/my_shelf.html'
    context_object_name = 'items'
    paginate_by = 20

    def get_queryset(self):
        qs = (
            ReadingStatus.objects
            .filter(user=self.request.user)
            .select_related('book')
            .prefetch_related('book__authors', 'book__categories')
        )
        status = self.request.GET.get('status')
        if status in dict(ReadingStatus.Status.choices):
            qs = qs.filter(status=status)
        return qs.order_by('-updated_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Contadores por estantería en UNA sola query
        raw_counts = (
            ReadingStatus.objects
            .filter(user=self.request.user)
            .values('status')
            .annotate(total=Count('id'))
        )
        counts = {c['status']: c['total'] for c in raw_counts}

        # Lista de pestañas lista para iterar en el template
        ctx['shelf_tabs'] = [
            {
                'value': value,
                'label': label,
                'count': counts.get(value, 0),
                'url': f'?status={value}',
            }
            for value, label in ReadingStatus.Status.choices
        ]
        ctx['total_count'] = sum(counts.values())
        ctx['active_status'] = self.request.GET.get('status', '')
        return ctx

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
        ctx['user'] = self.request.user
        ctx['profile'] = profile
        ctx['user_favorites'] = profile.favorite_books.all()
        ctx['active_loans'] = self.request.user.loans.filter(
            status='active'
        ).select_related('book')
        ctx['loan_history'] = self.request.user.loans.exclude(
            status='active'
        ).select_related('book')
        return ctx


