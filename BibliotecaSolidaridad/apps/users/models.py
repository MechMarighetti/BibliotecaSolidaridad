from django.db import models
from django.contrib.auth.models import AbstractUser

from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    ROLES = (
        ('reader', 'Lector'),
        ('librarian', 'Bibliotecario'),
        ('admin', 'Administrador')
    )
    role = models.CharField(max_length=10, choices=ROLES, default='reader')
    dni = models.CharField(max_length=20, unique=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    score = models.FloatField(default=5.0)
    is_active_member = models.BooleanField(default=True)
    suspension_end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    virtual_card_id = models.CharField(max_length=50, unique=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    
    favorite_categories = models.ManyToManyField('books.Category')
    favorite_books = models.ManyToManyField('books.Book', blank=True)
    newsletter_subscribed = models.BooleanField(default=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
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
        # Si querés suscribirlo a todas las categorías por defecto
        profile.favorite_categories.set(Category.objects.all()[:3])
