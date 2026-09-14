from django.contrib import admin
from .models import Book, Category, BookStock, Review
admin.site.register(Book)
admin.site.register(Category)
admin.site.register(BookStock)
admin.site.register(Review)
