from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Count, Q

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.name


class BookQuerySet(models.QuerySet):
    def recommended(self):
        return self.filter(stock__gt=0).order_by('-created_at')[:8]

    def total_available(self):
        return self.filter(stock__gt=0).count()

    def featured_authors(self):
        return (
            self.values('authors')
            .annotate(books_count=Count('id'))
            .filter(authors__isnull=False)
            .order_by('-books_count')[:6]
        )

    def search(self, query: str):
        if not query:
            return self.none()
        return (
            self.filter(
                Q(title__icontains=query)
                | Q(authors__icontains=query)
                | Q(categories__name__icontains=query)
            )
            .distinct()
        )


class Author(models.Model):
    name = models.CharField(max_length=255, unique=True, db_index=True)
    openlibrary_id = models.CharField(
        max_length=100, 
        unique=True, 
        blank=True, 
        null=True
    )
    biography = models.TextField(blank=True)
    
    class Meta:
        db_table = 'authors'
        verbose_name = 'Autor'
        verbose_name_plural = 'Autores'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['openlibrary_id']),
        ]
    
    def __str__(self):
        return self.name


class ISBN(models.Model):
    """Modelo para ISBNs (un libro puede tener múltiples ISBNs)"""
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name='isbns')
    isbn = models.CharField(max_length=20, unique=True, db_index=True)
    format = models.CharField(
        max_length=10, 
        choices=[('10', 'ISBN-10'), ('13', 'ISBN-13')],
        default='13'
    )
    
    class Meta:
        db_table = 'isbns'
        verbose_name = 'ISBN'
        verbose_name_plural = 'ISBNs'
    
    def __str__(self):
        return self.isbn


class Book(models.Model):
    openlibrary_id = models.CharField(
        max_length=50, 
        unique=True, 
        blank=True, 
        null=True,
        db_index=True
    )
    title = models.CharField(max_length=500, db_index=True)
    authors = models.ManyToManyField(Author, related_name='books')  # CAMBIO: ManyToMany en lugar de JSONField
    publish_date = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)  # NUEVO: agregamos descripción
    number_of_pages = models.IntegerField(blank=True, null=True)
    cover_url = models.URLField(blank=True)
    categories = models.ManyToManyField(Category, related_name='libros')
    stock = models.IntegerField(default=0)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # NUEVO: rastrear cambios
    
    objects = BookQuerySet.as_manager()
    
    class Meta:
        db_table = 'books'
        verbose_name = 'Libro'
        verbose_name_plural = 'Libros'
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['available', 'stock']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_authors_display(self):
        """Retorna los autores como string para templates"""
        return ', '.join(self.authors.values_list('name', flat=True))


class BookStock(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    physical_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=(
        ('available', 'Disponible'),
        ('borrowed', 'Prestado'),
        ('maintenance', 'En Mantenimiento'),
        ('lost', 'Perdido')
    ))
    condition = models.CharField(max_length=20, default='good')
    added_date = models.DateField(auto_now_add=True)
    class Meta:
        db_table = 'book_stocks'
        verbose_name = 'Stock de Libro'
        verbose_name_plural = 'Stocks de Libros'
    def __str__(self):
        return f"{self.book.title} - {self.physical_id}"


class ReviewQuerySet(models.QuerySet):
    def for_book(self, book):
        return self.filter(book=book).select_related('user')


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    rating = models.IntegerField()  # Por ejemplo, de 1 a 5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ReviewQuerySet.as_manager()

    class Meta:
        db_table = 'reviews'
        verbose_name = 'Reseña'
        unique_together = ('user', 'book')


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'favorites'
        verbose_name = 'Favoritos'
        unique_together = ('user', 'book')
