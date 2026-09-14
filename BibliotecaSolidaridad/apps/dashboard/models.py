from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class DashboardMetric(models.Model):
    name = models.CharField(max_length=100, unique=True)
    value = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dashboard_metrics'
        verbose_name = 'Métrica del Tablero'
        verbose_name_plural = 'Métricas del Tablero'
        ordering = ['name']

    def __str__(self):
        return f"{self.name}: {self.value}"


class Notification(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications'
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'read']),
        ]

    def __str__(self):
        estado = 'Leída' if self.read else 'No Leída'
        return f"Notificación para {self.user.username} - {estado}"