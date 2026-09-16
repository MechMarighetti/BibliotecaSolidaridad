from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Count, Q

User = get_user_model()
class CulturalEvent(models.Model):

    EVENT_TYPES = [
        ('taller', 'Taller'),
        ('charla', 'Charla'),
        ('lectura', 'Club de lectura'),
        ('presentacion', 'Presentación de libro'),
        ('exposicion', 'Exposición'),
        ('otro', 'Otro'),
    ]

    STATUS_CHOICES = [
        ('programado', 'Programado'),
        ('realizado', 'Realizado'),
        ('cancelado', 'Cancelado'),
    ]

    title = models.CharField(max_length=200, verbose_name='Título')
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPES,
        default='otro',
        verbose_name='Tipo de evento'
    )
    date = models.DateField(verbose_name='Fecha')
    start_time = models.TimeField(verbose_name='Hora de inicio')
    end_time = models.TimeField(
        blank=True,
        null=True,
        verbose_name='Hora de finalización'
    )
    location = models.CharField(
        max_length=200,
        verbose_name='Lugar'
    )
    capacity = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Cupo máximo'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='programado',
        verbose_name='Estado'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cultural_events'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cultural_events'
        verbose_name = 'Evento cultural'
        verbose_name_plural = 'Eventos culturales'
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.title} - {self.date}"

# Create your models here.
