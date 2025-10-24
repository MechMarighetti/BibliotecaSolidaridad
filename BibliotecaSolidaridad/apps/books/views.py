from datetime import date
from django.urls import reverse_lazy
import requests
from django.views import View
from django.views.generic import ListView, DetailView, CreateView
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, render
from django.db.models import Avg
from django.contrib import messages
from .models import Category
from .forms import BookForm

from .models import Book, Review
from apps.users.models import UserProfile


class BookSearchView(ListView):
    model = Book
    template_name = 'books/book_search.html'
    context_object_name = 'local_results'

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        self.query = query
        self.openlibrary_results = []

        if not query:
            return Book.objects.none()

        local_books = Book.objects.search(query)
        self.openlibrary_results = self._search_openlibrary(query)
        return local_books

    def _search_openlibrary(self, query):
        try:
            response = requests.get(
                f"https://openlibrary.org/search.json?q={query}&limit=10", timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return [
                {
                    'title': doc.get('title', ''),
                    'authors': ", ".join(doc.get('author_name', [])),
                    'publish_year': doc.get('first_publish_year', ''),
                    'isbn': ", ".join(doc.get('isbn', [])[:1]) if doc.get('isbn') else '',
                    'openlibrary_id': (doc.get('edition_key', [None])[0] or doc.get('key')),
                    'cover_url': (
                        f"https://covers.openlibrary.org/b/id/{doc.get('cover_i')}-M.jpg"
                        if doc.get('cover_i') else None
                    ),
                }
                for doc in data.get('docs', [])
            ]
        except Exception:
            return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.query
        context['openlibrary_results'] = self.openlibrary_results
        context['searched'] = bool(self.query)
        context['existing_ids'] = set(Book.objects.values_list('openlibrary_id', flat=True))
        return context


class SearchOpenLibraryView(View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'error': 'Query parameter required'}, status=400)
        try:
            response = requests.get(
                f"https://openlibrary.org/search.json?q={query}&limit=10", timeout=10
            )
            response.raise_for_status()
            data = response.json()
            books = [
                {
                    'title': doc.get('title', ''),
                    'author_name': doc.get('author_name', []),
                    'publish_year': doc.get('first_publish_year', ''),
                    'number_of_pages': doc.get('number_of_pages', ''),
                    'isbn': doc.get('isbn', []),
                    'description': doc.get('description', ''),
                    'cover_url': (
                        f"https://covers.openlibrary.org/b/id/{doc.get('cover_i')}-M.jpg"
                        if doc.get('cover_i') else None
                    ),
                }
                for doc in data.get('docs', [])
            ]
            return JsonResponse({'books': books})
        except requests.RequestException:
            return JsonResponse({'error': 'Error connecting to OpenLibrary'}, status=502)
        except Exception:
            return JsonResponse({'error': 'Internal server error'}, status=500)


class AddBookView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Vista para agregar libros usando el BookForm"""
    model = Book
    form_class = BookForm
    template_name = 'books/add_book.html'
    success_url = reverse_lazy('book_list')
    
    def test_func(self):
        """Solo bibliotecarios y administradores pueden agregar libros"""
        return self.request.user.role in ['librarian', 'admin']
    
    def get(self, request):
        """Muestra el formulario vacío para agregar libro"""
        form = BookForm()
        context = {
            'form': form,
            'categories': Category.objects.all(),
        }
        return render(request, 'books/add_book.html', context)

    def get_context_data(self, **kwargs):
        """Agrega categorías al contexto para el template"""
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

    def post(self, request):
        form = BookForm(request.POST)
        
        if form.is_valid():
            try:
                book = form.save(commit=False)
                openlibrary_id = request.POST.get('openlibrary_id')
                if openlibrary_id:
                    book.openlibrary_id = openlibrary_id
                
                book.save()
                form.save_m2m()
                
                messages.success(request, f'Libro "{book.title}" agregado correctamente.')
                # ✅ CAMBIO: Usar 'pk' en lugar de 'book_id'
                return redirect('book_detail', pk=book.id)
                
            except Exception as e:
                # ✅ CAMBIO: Mensaje genérico sin detalles técnicos
                messages.error(request, 'Error al guardar el libro. Por favor intenta nuevamente.')
                print(f"Error guardando libro: {str(e)}")  # Log interno

    def form_valid(self, form):
        """Procesa el formulario cuando es válido"""
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'Libro "{self.object.title}" agregado correctamente.'
        )
        return response
    
    def form_invalid(self, form):
        """Procesa el formulario cuando es inválido"""
        messages.error(
            self.request, 
            'Por favor corrige los errores en el formulario.'
        )
        return super().form_invalid(self, form)
        
        

class RemoveBookView(View):
    """Elimina un libro existente de la biblioteca."""

    def post(self, request, book_id):
        referer = request.META.get("HTTP_REFERER", "/")

        try:
            book = Book.objects.filter(id=book_id).first()
            if not book:
                messages.warning(request, "El libro no existe o ya fue eliminado.")
                return redirect(referer)

            title = book.title
            book.delete()
            messages.info(request, f'El libro "{title}" fue eliminado de la biblioteca.')
            return redirect(referer)

        except Exception as e:
            messages.error(request, f"Error al eliminar el libro: {e}")
            return redirect(referer)

class EditReviewView(LoginRequiredMixin, View):
    """Permite editar la reseña existente del usuario."""
    def post(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        user = request.user

        review = Review.objects.filter(book=book, user=user).first()
        if not review:
            messages.error(request, "No tienes una reseña para este libro.")
            return redirect('book_detail', pk=book_id)

        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()

        if not rating or not comment:
            messages.error(request, "Debes completar todos los campos.")
            return redirect('book_detail', pk=book_id)

        review.rating = int(rating)
        review.comment = comment
        review.save()

        messages.success(request, "Tu reseña fue actualizada correctamente.")
        return redirect('book_detail', pk=book_id)



class BookDetailView(DetailView):
    model = Book
    template_name = 'books/book_detail.html'
    context_object_name = 'book'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = self.object
        reviews = Review.objects.filter(book=book).order_by('-created_at')

        context['recent_reviews'] = reviews[:3]
        context['review_count'] = reviews.count()
        context['average_rating'] = round(reviews.aggregate(avg=Avg('rating'))['avg'] or 0, 1)
        context['total_loans'] = book.loan_set.count() if hasattr(book, 'loan_set') else 0

        user = self.request.user
        # 🔹 Agregamos esto
        context['user_review'] = (
            Review.objects.filter(book=book, user=user).first()
            if user.is_authenticated else None
        )
        context['user_has_reviewed'] = bool(context['user_review'])

        context['is_favorite'] = (
            user.is_authenticated
            and hasattr(user, 'profile')
            and hasattr(user.profile, 'favorite_books')
            and book in user.profile.favorite_books.all()
        )
        return context


class AddReviewView(LoginRequiredMixin, CreateView):
    model = Review
    fields = ['rating', 'comment']

    def post(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        user = request.user

        # Verificar si ya tiene una reseña
        if Review.objects.filter(book=book, user=user).exists():
            messages.warning(request, "Ya has dejado una reseña para este libro.")
            return redirect('book_detail', pk=book_id)

        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()

        if not rating or not comment:
            messages.error(request, "Debes completar todos los campos.")
            return redirect('book_detail', pk=book_id)

        Review.objects.create(
            user=user,
            book=book,
            rating=int(rating),
            comment=comment
        )

        messages.success(request, "Tu reseña fue publicada correctamente.")
        return redirect('book_detail', pk=book_id)
    

class DeleteReviewView(LoginRequiredMixin, View):
    """Permite eliminar la reseña existente del usuario."""
    def post(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        review = Review.objects.filter(book=book, user=request.user).first()

        if not review:
            messages.error(request, "No tenés una reseña para eliminar.")
            return redirect('book_detail', pk=book_id)

        review.delete()
        messages.success(request, "Tu reseña fue eliminada correctamente.")
        return redirect('book_detail', pk=book_id)


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

        referer = request.META.get('HTTP_REFERER', '/')
        return redirect(referer)


class ProfileView(LoginRequiredMixin, DetailView):
    model = UserProfile
    template_name = 'users/profile.html'
    context_object_name = 'profile'

    def get_object(self):
        return get_object_or_404(UserProfile, user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.get_object()

        # Favoritos (ManyToMany con Book)
        context['user_favorites'] = profile.favorite_books.all()

        # Préstamos activos e historial
        context['active_loans'] = self.request.user.loan_set.filter(status='active').select_related('book')
        context['loan_history'] = self.request.user.loan_set.exclude(status='active').select_related('book')

        return context

class RemoveFavoriteView(LoginRequiredMixin, View):
    """Elimina un libro de los favoritos del usuario."""
    def post(self, request, book_id):
        profile = get_object_or_404(UserProfile, user=request.user)
        book = get_object_or_404(Book, id=book_id)

        if book in profile.favorite_books.all():
            profile.favorite_books.remove(book)
            messages.success(request, f'El libro "{book.title}" fue eliminado de tus favoritos.')
        else:
            messages.warning(request, "Este libro no estaba en tus favoritos.")

        return redirect('profile')