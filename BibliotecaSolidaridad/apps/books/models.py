from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Count, Q

User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_categories'
    )

    class Meta:
        db_table = 'categories'
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=255, unique=True, db_index=True)
    openlibrary_id = models.CharField(
        max_length=100, unique=True, blank=True, null=True
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

    @classmethod
    def featured(cls, limit=6):
        """Autores con más libros en la biblioteca."""
        return cls.objects.annotate(
            books_count=Count('books')
        ).order_by('-books_count')[:limit]


class ISBN(models.Model):
    """ISBNs asociados a un libro (un libro puede tener varios)."""
    book = models.ForeignKey(
        'Book', on_delete=models.CASCADE, related_name='isbns'
    )
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


class BookQuerySet(models.QuerySet):
    def recommended(self, limit=8):
        return self.filter(stock__gt=0).order_by('-created_at')[:limit]

    def total_available(self):
        return self.filter(stock__gt=0).count()

    def featured_authors(self, limit=6):
        return Author.featured(limit=limit)

    def search(self, query: str):
        if not query:
            return self.none()
        return self.filter(
            Q(title__icontains=query)
            | Q(authors__name__icontains=query)
            | Q(categories__name__icontains=query)
            | Q(isbns__isbn__icontains=query)
        ).distinct()


class Book(models.Model):
    openlibrary_id = models.CharField(
        max_length=50, unique=True, blank=True, null=True, db_index=True
    )
    title = models.CharField(max_length=500, db_index=True)
    authors = models.ManyToManyField(Author, related_name='books', blank=True)
    publish_date = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    number_of_pages = models.IntegerField(blank=True, null=True)
    isbn = models.ManyToManyField(ISBN, related_name='books', blank=True)
    cover_url = models.URLField(blank=True)
    categories = models.ManyToManyField(Category, related_name='books')
    stock = models.IntegerField(default=0)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

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
        """Autores como string, útil en templates."""
        return ', '.join(self.authors.values_list('name', flat=True))

    def get_isbn_display(self):
        return ', '.join(self.isbns.values_list('isbn', flat=True))


class BookStock(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='copies')
    physical_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(
        max_length=20,
        choices=(
            ('available', 'Disponible'),
            ('borrowed', 'Prestado'),
            ('maintenance', 'En Mantenimiento'),
            ('lost', 'Perdido'),
        ),
        default='available',
    )
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ReviewQuerySet.as_manager()

    class Meta:
        db_table = 'reviews'
        verbose_name = 'Reseña'
        verbose_name_plural = 'Reseñas'
        unique_together = ('user', 'book')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.book} ({self.rating}/5)"

class ReadingStatus(models.TextChoices):
    
    TO_READ = 'to_read', 'Por leer'
    READING = 'reading', 'Leyendo'
    READ = 'read', 'Leído'

    @classmethod
    def active_statuses(cls):
        """Estados que representan actividad actual del usuario."""
        return [cls.READING]

    @classmethod
    def completed_statuses(cls):
        """Estados que representan un ciclo cerrado."""
        return [cls.READ]

    @classmethod
    def default(cls):
        """Estado por defecto al agregar un libro a la estantería."""
        return cls.TO_READ