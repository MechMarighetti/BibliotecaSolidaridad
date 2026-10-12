from django.db import models
from django.contrib.auth.models import AbstractUser
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models.signals import post_save
from django.contrib import messages
from django.views.generic import DetailView
from django.dispatch import receiver
from .constants import LOAN_LIMITS
from .validators import validate_dni



class User(AbstractUser):
    ROLES = (
        ('reader', 'Lector'),
        ('librarian', 'Bibliotecario'),
        ('admin', 'Administrador')
    )
    role = models.CharField(max_length=10, choices=ROLES, default='reader')

    dni = models.CharField(
            max_length=20, 
            unique=True,
            validators=[validate_dni],
            help_text="Formato: 12345678 o 12.345.678"
        )
    address = models.TextField()
    phone = models.CharField(max_length=20)
    score = models.FloatField(default=5.0)
    is_active_member = models.BooleanField(default=True)
    suspension_end_date = models.DateField(null=True, blank=True)
    
    def get_loan_limit(self):
        """Calcula el límite de préstamos basado en el puntaje"""
        for score_range, limit in LOAN_LIMITS.items():
            if score_range == 'excellent' and self.score >= 4.5:
                return limit
            elif score_range == 'good' and 3.0 <= self.score < 4.5:
                return limit
            elif score_range == 'fair' and 1.0 <= self.score < 3.0:
                return limit
        return 0

    class Meta:
        db_table = 'users'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

AVATAR_CHOICES = [
    ('images/Armibiblio-.png', 'Tato el tatú carreta'),
    ('images/Bentevíbiblio-.png', 'Benteví el benteveo'),
    ('images/Carpibiblio-.png', 'Carpi el carpincho'),
    ('images/Doctorbiblio-.png', 'Doc el tordo'),
    ('images/DonBargresbiblio-.png', 'Don Borges el bagre'),
    ('images/Francabiblio-.png', 'Franca la Ballena Austral'),
    ('images/Guanabiblio-.png', 'Tato el guanaco'),
    ('images/Guaribiblio-.png', 'Wari el aguará guazú'),
    ('images/Hormibiblio-.png', 'Hormi el oso hormiguero'),
    ('images/Hornebiblio-.png', 'Jero el hornero'),
    ('images/Jaguabiblio-.png', 'Yasí el yaguareté'),
    ('images/Llamibiblio-.png', 'Tuy la llama'),
    ('images/Parribiblio-.png', 'Rolo el loro'),
    ('images/Pingubiblio-.png', 'Pingu la pingüina'),
    ('images/Susibiblio-.png', 'Zazo el zorro'),
    ('images/Tortubiblio-.png', 'Tuga la tortuga')
]


def random_avatar():
    import random
    return random.choice(AVATAR_CHOICES)[0]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    virtual_card_id = models.CharField(max_length=50, unique=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    profile_picture = models.CharField(max_length=255, choices=AVATAR_CHOICES, default=random_avatar)
    favorite_categories = models.ManyToManyField('books.Category')
    favorite_books = models.ManyToManyField('books.Book', blank=True)
    newsletter_subscribed = models.BooleanField(default=True)
    profile_picture = models.ImageField(null=True, blank=True, choices=AVATAR_CHOICES, default=random_avatar)
    fecha_nacimiento = models.DateField(null=True, blank=True)


    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'
    def __str__(self):
        return f"Perfil de {self.user.username}"
    def get_shelf(self, status=None):
        from apps.books.models import UserBookStatus, ReadingStatus   # ← acá
        qs = (
            UserBookStatus.objects
            .filter(user=self.user)
            .select_related('book')
            .prefetch_related('book__authors', 'book__categories')
            .order_by('-updated_at')
        )
        if status in dict(ReadingStatus.choices):
            qs = qs.filter(status=status)
        return qs

    def get_shelf_counts(self):
        from apps.books.models import UserBookStatus
        from django.db.models import Count
        raw = (
            UserBookStatus.objects
            .filter(user=self.user)
            .values('status')
            .annotate(total=Count('id'))
        )
        return {c['status']: c['total'] for c in raw}

    def get_shelf_tabs(self):
        from apps.books.models import ReadingStatus
        counts = self.get_shelf_counts()
        return [
            {
                'value': value,
                'label': label,
                'count': counts.get(value, 0),
                'url': f'?status={value}',
            }
            for value, label in ReadingStatus.choices
        ]

    def get_shelf_total(self):
        from apps.books.models import UserBookStatus
        return UserBookStatus.objects.filter(user=self.user).count()

    def get_reading_status_for(self, book):
        from apps.books.models import UserBookStatus
        return UserBookStatus.objects.filter(user=self.user, book=book).first()

    def set_reading_status(self, book, status, progress=0, notes=''):
        from apps.books.models import UserBookStatus
        obj, _ = UserBookStatus.objects.update_or_create(
            user=self.user,
            book=book,
            defaults={
                'status': status,
                'progress': progress,
                'notes': notes,
            },
        )
        return obj

    def remove_from_shelf(self, book):
        from apps.books.models import UserBookStatus
        UserBookStatus.objects.filter(user=self.user, book=book).delete()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        from apps.books.models import Category
        profile = UserProfile.objects.create(
            user=instance,
            virtual_card_id=f"VCARD-{instance.id:05d}"
        )
        profile.favorite_categories.set(Category.objects.all()[:3])
