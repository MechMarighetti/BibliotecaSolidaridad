from django.db import models
from django.contrib.auth import get_user_model

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

class Book(models.Model):
    openlibrary_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=500)
    authors = models.JSONField()  # Lista de autores
    publish_date = models.CharField(max_length=100, blank=True)  # Año de publicación
    isbn = models.JSONField(blank=True, null=True)  # Lista de ISBNs
    number_of_pages = models.IntegerField(blank=True, null=True)
    cover_url = models.URLField(blank=True)
    categories = models.ManyToManyField(Category, related_name='libros')
    stock = models.IntegerField(default=0)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'books'
        verbose_name = 'Libro'
        verbose_name_plural = 'Libros'

    def __str__(self):
        return self.title
    
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


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    rating = models.IntegerField()  # Por ejemplo, de 1 a 5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

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