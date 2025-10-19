import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.db.models import Count, Q
from .models import Book, Category, Review
from apps.loans.models import Loan
from apps.users.models import User

def home(request):
    # Libros recomendados (últimos 8 libros agregados)
    recommended_books = Book.objects.filter(stock__gt=0).order_by('-created_at')[:8]
    
    # Estadísticas para la home
    stats = {
        'total_books': Book.objects.filter(stock__gt=0).count(),
        'active_members': User.objects.filter(is_active_member=True).count(),
        'active_loans': Loan.objects.filter(status='active').count(),
        'categories': Category.objects.count(),
    }
    
    # Autores destacados (autores con más libros)
    featured_authors = Book.objects.values('authors').annotate(
        books_count=Count('id')
    ).order_by('-books_count')[:6]
    
    # Formatear autores para el template
    authors_list = []
    for author in featured_authors:
        if author['authors']:  # Asegurarse de que el autor no sea None
            authors_list.append({
                'name': author['authors'],
                'books_count': author['books_count']
            })
    
    context = {
        'recommended_books': recommended_books,
        'stats': stats,
        'featured_authors': authors_list,
    }
    return render(request, 'home.html', context)

def book_search(request):
    query = request.GET.get('q', '')
    results = []
    if query:
        results = Book.objects.filter(
            Q(title__icontains=query) |
            Q(authors__icontains=query) |
            Q(categories__name__icontains=query)
        ).distinct()
    
    context = {
        'query': query,
        'results': results,
    }
    
    return render(request, 'books/book_search.html', context)


@require_http_methods(["GET"])
@csrf_exempt
def search_openlibrary(request):
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'error': 'Query parameter required'}, status=400)
    
    try:
        # Buscar en OpenLibrary API
        url = f"https://openlibrary.org/search.json?q={query}&limit=10"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        books = []
        for doc in data.get('docs', []):
            book_info = {
                'title': doc.get('title', ''),
                'author_name': doc.get('author_name', []),
                'publish_year': doc.get('first_publish_year', ''),
                'isbn': doc.get('isbn', []),
                'description': doc.get('description', ''),
                'cover_url': f"https://covers.openlibrary.org/b/id/{doc.get('cover_i')}-M.jpg" if doc.get('cover_i') else None,
            }
            books.append(book_info)
        
        return JsonResponse({'books': books})
    
    except requests.RequestException as e:
        return JsonResponse({'error': 'Error connecting to OpenLibrary'}, status=500)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)

import requests

def add_book(request):
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            title = request.POST.get('title')
            authors = request.POST.get('authors')
            isbn = request.POST.get('isbn')
            publish_date = request.POST.get('publish_date')
            stock = request.POST.get('stock', 1)
            cover_url = request.POST.get('cover_url')
            available = request.POST.get('available') == 'true'
            openlibrary_id = request.POST.get('openlibrary_id')
            
            # Validar campos requeridos
            if not title:
                return JsonResponse({'error': 'El título es requerido'}, status=400)
            
            # Verificar si el libro ya existe por ISBN o OpenLibrary ID
            if isbn and Book.objects.filter(isbn=isbn).exists():
                return JsonResponse({'error': 'Ya existe un libro con este ISBN'}, status=400)
            
            if openlibrary_id and Book.objects.filter(openlibrary_id=openlibrary_id).exists():
                return JsonResponse({'error': 'Este libro de OpenLibrary ya existe'}, status=400)
            
            # Crear el libro
            book = Book.objects.create(
                title=title,
                authors=authors,
                isbn=isbn,
                publish_date=publish_date,
                stock=stock,
                cover_url=cover_url,
                available=available,
                openlibrary_id=openlibrary_id
            )
            
            return JsonResponse({
                'success': True, 
                'book_id': book.id,
                'message': f'Libro "{title}" agregado correctamente!'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error al agregar el libro: {str(e)}'}, status=500)
    
    # Si es GET, mostrar el formulario
    return render(request, 'books/add_book.html')

def book_detail(request, book_id):
    book = Book.objects.get(id=book_id)
    reviews = Review.objects.filter(book=book).select_related('user')
    context = {
        'book': book,
        'reviews': reviews,
    }
    return render(request, 'book_detail.html', context)
def add_review(request, book_id):
    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment', '')
        book = Book.objects.get(id=book_id)
        Review.objects.create(
            user=request.user,
            book=book,
            rating=rating,
            comment=comment
        )
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid request method'}, status=400)
def toggle_favorite(request, book_id):
    book = Book.objects.get(id=book_id)
    profile = request.user.profile
    if book in profile.favorite_books.all():
        profile.favorite_books.remove(book)
        favorited = False
    else:
        profile.favorite_books.add(book)
        favorited = True
    return JsonResponse({'favorited': favorited})

