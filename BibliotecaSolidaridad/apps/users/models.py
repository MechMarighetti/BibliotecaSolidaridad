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
    ('images/Doctorbiblio-.png', 'Doctor el tordo'),
    ('images/DonBargresbiblio-.png', 'Don Bargres el bagre'),
    ('images/Francabiblio-.png', 'Franca la Ballena Austral'),
    ('images/Guanabiblio-.png', 'Guana el guanaco'),
    ('images/Guaribiblio-.png', 'Guari el aguará guazú'),
    ('images/Hormibiblio-.png', 'Hormi el oso hormiguero'),
    ('images/Hornebiblio-.png', 'Horne el hornero'),
    ('images/Jaguabiblio-.png', 'Yasí el yaguareté'),
    ('images/Llamibiblio-.png', 'Llami la llama'),
    ('images/Parribiblio-.png', 'Parri el loro'),
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


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        from apps.books.models import Category
        profile = UserProfile.objects.create(
            user=instance,
            virtual_card_id=f"VCARD-{instance.id:05d}"
        )
        profile.favorite_categories.set(Category.objects.all()[:3])
